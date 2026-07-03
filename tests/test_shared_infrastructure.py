"""Unit tests for the shared infrastructure layer"""

import json
import pytest
from shared.async_db import AsyncDatabase
from shared.config import Settings


@pytest.fixture
async def db():
    _db = AsyncDatabase(":memory:")
    yield _db
    await _db.close()


class TestAsyncDatabase:
    async def test_connect(self, db):
        conn = await db.connect()
        assert conn is not None

    async def test_execute_and_fetchone(self, db):
        await db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        await db.execute("INSERT INTO test VALUES (1, 'alice')")
        await db.commit()
        row = await db.fetchone("SELECT * FROM test WHERE id=1")
        assert row is not None
        assert row["name"] == "alice"

    async def test_fetchall(self, db):
        await db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, val TEXT)")
        for i in range(3):
            await db.execute("INSERT INTO items VALUES (?, ?)", (i, f"item-{i}"))
        await db.commit()
        rows = await db.fetchall("SELECT * FROM items ORDER BY id")
        assert len(rows) == 3
        assert rows[2]["val"] == "item-2"

    async def test_serialize_json(self, db):
        data = {"key": "value", "list": [1, 2, 3]}
        serialized = db.serialize_json(data)
        assert json.loads(serialized) == data

    async def test_deserialize_json(self, db):
        result = db.deserialize_json('{"a": 1}')
        assert result["a"] == 1

    async def test_deserialize_json_none(self, db):
        result = db.deserialize_json(None, default=[])
        assert result == []

    async def test_fts5_creation(self, db):
        await db.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                title TEXT,
                body TEXT
            )
        """)
        await db.ensure_fts5_trigger("documents", "documents_fts", ["title", "body"])

        await db.execute("INSERT INTO documents VALUES (1, 'hello world', 'this is a test document')")
        await db.commit()

        row = await db.fetchone(
            "SELECT * FROM documents_fts WHERE documents_fts MATCH ?",
            ("hello",),
        )
        assert row is not None

    async def test_close(self, db):
        await db.close()
        assert db._conn is None


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.ollama_base_url == "http://localhost:11434"
        assert s.ollama_model == "qwen2.5:3b"
        assert s.chroma_host == "localhost"
        assert s.chroma_port == 8000
        assert s.enable_ollama is True
        assert s.enable_chroma is True

    def test_from_env(self):
        s = Settings.from_env()
        assert isinstance(s, Settings)
