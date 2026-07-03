"""Cold-Storage Archive Pipeline

Moves old recipe and timeline data into compressed archive files,
replacing database rows with hash-pointer metadata.

Uses gzipped CSV + SHA-256 for storage — stdlib only, no extra deps.
"""

import csv
import gzip
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

ARCHIVE_AFTER_DAYS = int(os.getenv("ARCHIVE_AFTER_DAYS", "90"))


class ArchivePipeline:
    """Compress and archive old data, replacing rows with hash pointers.

    The pipeline:
      1. Identifies recipes older than *archive_after_days*.
      2. Packages them into a gzipped CSV file with a SHA-256 hash.
      3. Replaces database rows with a metadata blob:
         ``{"archived": true, "hash": "sha256:...", "original_count": N, "archived_at": "..."}``
      4. The archive file can be verified later via ``verify_archive()``.
    """

    def __init__(
        self,
        db,
        archive_dir: str = "archives",
        archive_after_days: int = ARCHIVE_AFTER_DAYS,
    ):
        self.db = db
        self.archive_dir = Path(archive_dir)
        self.archive_after_days = archive_after_days
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    async def archive_recipes(
        self, recipe_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Archive old recipes.

        If *recipe_ids* is provided, archives those specific IDs.
        Otherwise, archives all recipes older than *archive_after_days*.
        """
        if recipe_ids is None:
            recipe_ids = await self._find_archivable_recipes()

        if not recipe_ids:
            return {"archived": 0, "hash": "", "filename": ""}

        recipes = await self._fetch_recipes(recipe_ids)
        archive_filename = self._generate_filename()
        archive_path = self.archive_dir / archive_filename

        archive_hash = self._write_archive(archive_path, recipes)

        await self._replace_with_pointers(recipe_ids, archive_hash, len(recipes))

        await self._register_archive(archive_filename, archive_hash, len(recipes))

        return {
            "archived": len(recipe_ids),
            "hash": archive_hash,
            "filename": archive_filename,
        }

    async def verify_archive(self, archive_filename: str) -> Dict[str, Any]:
        """Verify the integrity of a single archive file."""
        archive_path = self.archive_dir / archive_filename
        if not archive_path.exists():
            return {"valid": False, "error": f"Archive not found: {archive_filename}"}
        try:
            with gzip.open(archive_path, "rt", newline="") as f:
                content = f.read()
            computed_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
            metadata = await self._get_archive_metadata(archive_filename)
            stored_hash = metadata.get("hash", "") if metadata else ""
            if stored_hash and computed_hash != stored_hash:
                return {"valid": False, "error": "Hash mismatch", "computed": computed_hash, "stored": stored_hash}
            return {"valid": True, "hash": computed_hash, "recipe_count": len(content.strip().split("\n")) - 1}
        except Exception as exc:
            return {"valid": False, "error": str(exc)}

    async def _find_archivable_recipes(self) -> List[str]:
        """Find recipe IDs older than *archive_after_days*.

        This targets the timeline's archived recipe data. In a full
        deployment, this would join against the agent-recipe-compiler
        recipes table.
        """
        cutoff = (datetime.now() - timedelta(days=self.archive_after_days)).date().isoformat()
        try:
            rows = await self.db.fetchall(
                "SELECT id FROM intelligence_timeline WHERE date < ? ORDER BY date ASC",
                (cutoff,),
            )
            return [r["id"] for r in rows]
        except Exception:
            return []

    async def _fetch_recipes(self, recipe_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch full row data for the given recipe IDs."""
        recipes = []
        for rid in recipe_ids:
            row = await self.db.fetchone(
                "SELECT * FROM intelligence_timeline WHERE id = ?", (rid,)
            )
            if row:
                recipes.append(dict(row))
        return recipes

    def _generate_filename(self) -> str:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"archive_{ts}.csv.gz"

    def _write_archive(
        self, archive_path: Path, recipes: List[Dict[str, Any]]
    ) -> str:
        """Write recipes to gzipped CSV, return SHA-256 hash."""
        if not recipes:
            return "sha256:" + "0" * 64
        csv_buffer = io.StringIO(newline="")
        fieldnames = list(recipes[0].keys())
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(recipes)
        content = csv_buffer.getvalue()

        hash_value = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

        with gzip.open(archive_path, "wt") as f:
            f.write(content)

        logger.info(
            "Archived %d recipes to %s (hash: %s)",
            len(recipes),
            archive_path.name,
            hash_value,
        )
        return hash_value

    async def _replace_with_pointers(
        self, recipe_ids: List[str], archive_hash: str, original_count: int
    ) -> None:
        """Replace archived recipe rows with hash-pointer metadata.

        Since the schema does not support in-place replacement,
        we set a JSON metadata blob via the existing columns.
        For intelligence_timeline, we clear recipe-specific columns
        and store the archive pointer in prompt_versions.
        """
        pointer = json.dumps({
            "archived": True,
            "hash": archive_hash,
            "original_count": original_count,
            "archived_at": datetime.now().isoformat(),
        })
        for rid in recipe_ids:
            await self.db.execute(
                "UPDATE intelligence_timeline SET recipe_count=0, avg_score=0.0, "
                "memory_versions='[]', prompt_versions=? WHERE id=?",
                (pointer, rid),
            )
        await self.db.commit()

    async def _init_archive_table(self) -> None:
        """Ensure the cold_storage_archive table exists."""
        try:
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS cold_storage_archive (
                    filename TEXT PRIMARY KEY,
                    hash TEXT NOT NULL,
                    recipe_count INTEGER DEFAULT 0,
                    archived_at TEXT NOT NULL
                );
            """)
        except Exception:
            pass

    async def _register_archive(
        self, filename: str, archive_hash: str, recipe_count: int
    ) -> None:
        """Record archive metadata in the cold_storage_archive table."""
        try:
            await self._init_archive_table()
            await self.db.execute(
                "INSERT INTO cold_storage_archive (filename, hash, recipe_count, archived_at) "
                "VALUES (?, ?, ?, ?)",
                (filename, archive_hash, recipe_count, datetime.now().isoformat()),
            )
            await self.db.commit()
        except Exception:
            pass

    async def _get_archive_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        try:
            await self._init_archive_table()
            return await self.db.fetchone(
                "SELECT * FROM cold_storage_archive WHERE filename = ?", (filename,)
            )
        except Exception:
            return None
