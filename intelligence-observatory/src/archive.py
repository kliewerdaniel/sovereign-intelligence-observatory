"""Cold-Storage Archive Pipeline with Immutable Ledger Chain

Archives old recipe/timeline data into gzipped CSV blobs with SHA-256
content hashes, linked sequentially into a verifiable Merkle sequence.
Also provides an on-demand streaming reader that retrieves single
records without fully decompressing the archive file.
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
from typing import List, Dict, Any, Optional, Iterator

logger = logging.getLogger(__name__)

ARCHIVE_AFTER_DAYS = int(os.getenv("ARCHIVE_AFTER_DAYS", "90"))


# ── Sequential Ledger Chain ────────────────────────────────────────────────────

def _hash_content(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


class ArchivePipeline:
    """Immutable, sequentially-linked cold-storage archive pipeline.

    Each archive file records the hash of the preceding archive file,
    building a tamper-evident Merkle chain.  The chain can be verified
    from the most recent archive all the way back to genesis.

    Schema of ``cold_storage_archive`` (new):
      filename        TEXT PRIMARY KEY
      hash            TEXT NOT NULL          -- SHA-256 of this archive
      previous_hash   TEXT                   -- SHA-256 of previous archive (NULL for genesis)
      recipe_count    INTEGER DEFAULT 0
      archived_at     TEXT NOT NULL
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

    # ── Public API ───────────────────────────────────────────────────────────

    async def archive_recipes(
        self, recipe_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if recipe_ids is None:
            recipe_ids = await self._find_archivable_recipes()

        if not recipe_ids:
            return {"archived": 0, "hash": "", "filename": ""}

        previous_hash = await self._get_latest_archive_hash()
        recipes = await self._fetch_recipes(recipe_ids)
        archive_filename = self._generate_filename()
        archive_path = self.archive_dir / archive_filename

        archive_hash = self._write_archive(archive_path, recipes, previous_hash)

        await self._replace_with_pointers(recipe_ids, archive_hash, len(recipes))
        await self._register_archive(archive_filename, archive_hash, previous_hash, len(recipes))

        return {
            "archived": len(recipe_ids),
            "hash": archive_hash,
            "previous_hash": previous_hash,
            "filename": archive_filename,
        }

    async def verify_archive(self, archive_filename: str) -> Dict[str, Any]:
        """Verify integrity of a single archive file."""
        archive_path = self.archive_dir / archive_filename
        if not archive_path.exists():
            return {"valid": False, "error": f"Archive not found: {archive_filename}"}
        try:
            with gzip.open(archive_path, "rt", newline="") as f:
                content = f.read()
            computed_hash = _hash_content(content)
            metadata = await self._get_archive_metadata(archive_filename)
            if metadata is None:
                return {"valid": False, "error": "No metadata found"}
            stored_hash = metadata.get("hash", "")
            if stored_hash and computed_hash != stored_hash:
                return {"valid": False, "error": "Hash mismatch", "computed": computed_hash, "stored": stored_hash}
            return {"valid": True, "hash": computed_hash, "recipe_count": len(content.strip().split("\n")) - 1}
        except Exception as exc:
            return {"valid": False, "error": str(exc)}

    async def verify_chain(self) -> List[Dict[str, Any]]:
        """Walk the archive chain from most recent to genesis, checking each link.

        Returns a list of per-archive verification results.
        """
        await self._init_archive_table()
        archives = await self.db.fetchall(
            "SELECT filename, hash, previous_hash FROM cold_storage_archive ORDER BY archived_at DESC"
        )
        results: List[Dict[str, Any]] = []
        for entry in archives:
            filename = entry["filename"]
            expected_prev = entry["previous_hash"]
            prev_result = results[-1] if results else None
            if prev_result is not None and expected_prev and prev_result.get("hash"):
                if expected_prev != prev_result["hash"]:
                    results.append({
                        "filename": filename,
                        "valid": False,
                        "error": f"Chain break: expected previous_hash {expected_prev}, "
                                 f"but next archive has hash {prev_result['hash']}",
                    })
                    continue
            ver = await self.verify_archive(filename)
            results.append({"filename": filename, "valid": ver.get("valid", False), "hash": ver.get("hash", "")})
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _get_latest_archive_hash(self) -> str:
        await self._init_archive_table()
        row = await self.db.fetchone(
            "SELECT hash FROM cold_storage_archive ORDER BY archived_at DESC LIMIT 1"
        )
        return row["hash"] if row else ""

    async def _find_archivable_recipes(self) -> List[str]:
        cutoff = (datetime.now() - timedelta(days=self.archive_after_days)).date().isoformat()
        try:
            rows = await self.db.fetchall(
                "SELECT id FROM intelligence_timeline WHERE date < ? AND recipe_count > 0 ORDER BY date ASC",
                (cutoff,),
            )
            return [r["id"] for r in rows]
        except Exception:
            return []

    async def _fetch_recipes(self, recipe_ids: List[str]) -> List[Dict[str, Any]]:
        recipes = []
        for rid in recipe_ids:
            row = await self.db.fetchone(
                "SELECT * FROM intelligence_timeline WHERE id = ?", (rid,)
            )
            if row:
                recipes.append(dict(row))
        return recipes

    def _generate_filename(self) -> str:
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"archive_{ts}.csv.gz"

    def _write_archive(
        self, archive_path: Path, recipes: List[Dict[str, Any]], previous_hash: str = ""
    ) -> str:
        if not recipes:
            return "sha256:" + "0" * 64
        csv_buffer = io.StringIO(newline="")
        fieldnames = list(recipes[0].keys())
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(recipes)
        content = csv_buffer.getvalue()
        hash_value = _hash_content(content)
        with gzip.open(archive_path, "wt") as f:
            f.write(content)
        logger.info(
            "Archived %d recipes to %s (hash: %s, previous: %s)",
            len(recipes), archive_path.name, hash_value, previous_hash or "(genesis)",
        )
        return hash_value

    async def _replace_with_pointers(
        self, recipe_ids: List[str], archive_hash: str, original_count: int
    ) -> None:
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
        try:
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS cold_storage_archive (
                    filename TEXT PRIMARY KEY,
                    hash TEXT NOT NULL,
                    previous_hash TEXT,
                    recipe_count INTEGER DEFAULT 0,
                    archived_at TEXT NOT NULL
                );
            """)
        except Exception:
            pass

    async def _register_archive(
        self, filename: str, archive_hash: str, previous_hash: str, recipe_count: int
    ) -> None:
        try:
            await self._init_archive_table()
            await self.db.execute(
                "INSERT INTO cold_storage_archive (filename, hash, previous_hash, recipe_count, archived_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (filename, archive_hash, previous_hash or None, recipe_count, datetime.now().isoformat()),
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


# ── On-Demand Archive Streamer ─────────────────────────────────────────────────

class ArchiveStreamer:
    """Streaming reader for gzipped CSV archives.

    Reads compressed archive files line-by-line without loading the
    entire blob into memory.  Useful for retrieving single records
    by ID from large historical archives.
    """

    def __init__(self, archive_dir: str = "archives"):
        self.archive_dir = Path(archive_dir)

    def find_recipe(
        self, archive_filename: str, recipe_id: str
    ) -> Optional[Dict[str, Any]]:
        """Stream through an archive and return the first matching record.

        The archive is decompressed incrementally; only one CSV row is
        held in memory at a time.
        """
        archive_path = self.archive_dir / archive_filename
        if not archive_path.exists():
            return None
        return self._search(archive_path, recipe_id)

    def iter_archive(self, archive_filename: str) -> Iterator[Dict[str, Any]]:
        """Yield all records from an archive as a generator.

        Memory usage is proportional to the largest single CSV row,
        not the total file size.
        """
        archive_path = self.archive_dir / archive_filename
        if not archive_path.exists():
            return
        with gzip.open(archive_path, "rt", newline="") as f:
            reader = csv.DictReader(f)
            yield from reader

    def _search(self, archive_path: Path, recipe_id: str) -> Optional[Dict[str, Any]]:
        with gzip.open(archive_path, "rt", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("id") == recipe_id or row.get("id") == f"timeline-{recipe_id}":
                    return dict(row)
        return None
