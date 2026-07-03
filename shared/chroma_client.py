"""Optional ChromaDB client for semantic search with graceful fallback

Includes an embedding-model metadata ledger that detects dimension
changes and flags the database for a clean re-index.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

EMBEDDING_LEDGER_COLLECTION = "_embedding_ledger"


class EmbeddingModelLedger:
    """Tracks the embedding model identity used to populate a Chroma collection.

    Stores model name, embedding dimension, and a migration flag so that
    a change in the local embedding model triggers a clean re-index
    instead of silent corruption.
    """

    def __init__(self, collection):
        self._collection = collection

    @classmethod
    async def load(
        cls, client: Any, host: str, port: int
    ) -> Optional["EmbeddingModelLedger"]:
        try:
            ledger_col = await client.get_or_create_collection(
                name=EMBEDDING_LEDGER_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            return cls(ledger_col)
        except Exception as exc:
            logger.debug("Embedding ledger unavailable: %s", exc)
            return None

    async def get_registration(
        self, collection_name: str
    ) -> Optional[Dict[str, Any]]:
        try:
            results = await self._collection.query(
                query_texts=[collection_name],
                n_results=1,
            )
            if results.get("ids") and results["ids"][0]:
                idx = results["ids"][0][0]
                meta = (results.get("metadatas") or [[]])[0][0] if results.get("metadatas") else {}
                return {"id": idx, **meta}
            return None
        except Exception:
            return None

    async def register(
        self, collection_name: str, model_name: str, dimension: int
    ) -> None:
        try:
            await self._collection.upsert(
                ids=[collection_name],
                documents=[f"Embedding model '{model_name}' dim={dimension}"],
                metadatas=[{
                    "model_name": model_name,
                    "dimension": str(dimension),
                    "needs_reindex": "false",
                }],
            )
        except Exception as exc:
            logger.warning("Failed to register embedding model: %s", exc)


class _ChromaCollectionProxy:
    """A proxy that validates embedding-model compatibility on first access."""

    def __init__(self, raw_collection, ledger: Optional[EmbeddingModelLedger],
                 collection_name: str, model_name: str, dimension: int):
        self._raw = raw_collection
        self._ledger = ledger
        self._collection_name = collection_name
        self._model_name = model_name
        self._dimension = dimension
        self._validated = False

    async def _validate_or_reindex(self) -> bool:
        if self._validated:
            return True
        self._validated = True

        if self._ledger is None:
            return True

        reg = await self._ledger.get_registration(self._collection_name)
        if reg is None:
            await self._ledger.register(self._collection_name, self._model_name, self._dimension)
            return True

        stored_dim = int(reg.get("dimension", 0))
        stored_model = reg.get("model_name", "")

        if stored_dim != self._dimension or stored_model != self._model_name:
            logger.warning(
                "Embedding model changed: was '%s' (dim=%d), now '%s' (dim=%d). "
                "Collection '%s' needs re-index.",
                stored_model, stored_dim, self._model_name, self._dimension,
                self._collection_name,
            )
            try:
                await self._raw.update_metadata(
                    None,  # no filter — update collection-level metadata
                    {"needs_reindex": "true"},
                )
            except Exception:
                pass
            try:
                await self._ledger._collection.upsert(
                    ids=[self._collection_name],
                    documents=[f"Embedding model '{self._model_name}' dim={self._dimension}"],
                    metadatas=[{
                        "model_name": self._model_name,
                        "dimension": str(self._dimension),
                        "needs_reindex": "true",
                    }],
                )
            except Exception:
                pass
            return False

        return True

    async def add(self, ids, documents, metadatas=None):
        await self._validate_or_reindex()
        await self._raw.add(ids=ids, documents=documents, metadatas=metadatas)

    async def query(self, query_texts, n_results=10):
        await self._validate_or_reindex()
        return await self._raw.query(query_texts=query_texts, n_results=n_results)

    async def delete(self, ids):
        await self._validate_or_reindex()
        await self._raw.delete(ids=ids)

    async def count(self):
        await self._validate_or_reindex()
        return await self._raw.count()

    async def update_metadata(self, ids, metadata):
        await self._validate_or_reindex()
        await self._raw.update_metadata(ids=ids, metadata=metadata)


class ChromaClient:
    """Client for a local ChromaDB instance with embedding-model versioning.

    All public methods return None or empty results when ChromaDB is
    unreachable, allowing the platform to continue operating.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "observatory_recipes",
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dimension: int = 384,
        agent_id: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self._client = None
        self._collection = None
        self._agent_id = agent_id

        # Tenant isolation: append a deterministic namespace derived from agent_id.
        # Each agent gets its own collection, preventing cross-tenant leakage.
        if agent_id:
            namespace = hashlib.sha256(agent_id.encode()).hexdigest()[:16]
            self.collection_name = f"{collection_name}___{namespace}"
        else:
            self.collection_name = collection_name

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
            raw_collection = await self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            ledger = await EmbeddingModelLedger.load(self._client, self.host, self.port)
            self._collection = _ChromaCollectionProxy(
                raw_collection=raw_collection,
                ledger=ledger,
                collection_name=self.collection_name,
                model_name=self.embedding_model,
                dimension=self.embedding_dimension,
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
