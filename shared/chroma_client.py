"""Optional ChromaDB client for semantic search with graceful fallback"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ChromaClient:
    """Client for a local ChromaDB instance with graceful degradation.

    All public methods return None or empty results when ChromaDB is
    unreachable, allowing the platform to continue operating.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "observatory_recipes",
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    async def _connect(self) -> bool:
        if self._client is not None:
            return True
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = await chromadb.AsyncHttpClient(
                host=self.host,
                port=self.port,
                settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False),
            )
            return True
        except ImportError:
            logger.warning("chromadb package not installed; semantic search disabled")
            return False
        except Exception as exc:
            logger.warning("ChromaDB not reachable at %s:%s: %s", self.host, self.port, exc)
            return False

    async def _get_collection(self):
        if self._collection is not None:
            return self._collection
        if not await self._connect():
            return None
        try:
            self._collection = await self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except Exception as exc:
            logger.warning("ChromaDB collection error: %s", exc)
            return None

    async def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Index a document. Returns False on failure."""
        collection = await self._get_collection()
        if collection is None:
            return False
        try:
            await collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata or {}],
            )
            return True
        except Exception as exc:
            logger.warning("ChromaDB add_document error: %s", exc)
            return False

    async def search(
        self,
        query: str,
        n_results: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        """Semantic search over indexed documents. Returns None if unavailable."""
        collection = await self._get_collection()
        if collection is None:
            return None
        try:
            results = await collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            output = []
            for i in range(len(results.get("ids", [[]])[0])):
                output.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                })
            return output
        except Exception as exc:
            logger.warning("ChromaDB search error: %s", exc)
            return None

    async def delete_document(self, doc_id: str) -> bool:
        """Remove a document. Returns False on failure."""
        collection = await self._get_collection()
        if collection is None:
            return False
        try:
            await collection.delete(ids=[doc_id])
            return True
        except Exception as exc:
            logger.warning("ChromaDB delete error: %s", exc)
            return False

    async def count(self) -> Optional[int]:
        """Return document count, or None if unavailable."""
        collection = await self._get_collection()
        if collection is None:
            return None
        try:
            return await collection.count()
        except Exception as exc:
            logger.warning("ChromaDB count error: %s", exc)
            return None

    async def close(self) -> None:
        self._collection = None
        self._client = None
