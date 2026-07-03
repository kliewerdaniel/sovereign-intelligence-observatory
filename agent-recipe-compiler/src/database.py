"""
Agent Recipe Compiler - Database Layer
"""
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


class RecipeDatabase:
    """SQLite database for storing recipes"""
    
    def __init__(self, db_path: str = "recipes.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    recipe_id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version INTEGER NOT NULL,
                    memory_version INTEGER NOT NULL,
                    retrieved_docs TEXT,
                    reasoning_patterns TEXT,
                    evaluation TEXT,
                    outcome TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
                    objective,
                    model,
                    outcome,
                    content='recipes',
                    content_rowid='rowid'
                )
            """)
            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS recipes_ai AFTER INSERT ON recipes BEGIN
                    INSERT INTO recipes_fts(rowid, objective, model, outcome)
                    VALUES (new.rowid, new.objective, new.model, new.outcome);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS recipes_ad AFTER DELETE ON recipes BEGIN
                    INSERT INTO recipes_fts(recipes_fts, rowid, objective, model, outcome)
                    VALUES ('delete', old.rowid, old.objective, old.model, old.outcome);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS recipes_au AFTER UPDATE ON recipes BEGIN
                    INSERT INTO recipes_fts(recipes_fts, rowid, objective, model, outcome)
                    VALUES ('delete', old.rowid, old.objective, old.model, old.outcome);
                    INSERT INTO recipes_fts(rowid, objective, model, outcome)
                    VALUES (new.rowid, new.objective, new.model, new.outcome);
                END
            """)
            conn.commit()
    
    def store_recipe(self, recipe_data: Dict[str, Any]) -> str:
        """Store a recipe and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO recipes (
                    recipe_id, objective, model, prompt_version, memory_version,
                    retrieved_docs, reasoning_patterns, evaluation, outcome,
                    created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipe_data["recipe_id"],
                recipe_data["objective"],
                recipe_data["model"],
                recipe_data["prompt_version"],
                recipe_data["memory_version"],
                str(recipe_data.get("retrieved_docs", [])),
                str(recipe_data.get("reasoning_patterns", [])),
                str(recipe_data.get("evaluation", {})),
                recipe_data.get("outcome", "pending"),
                recipe_data["created_at"],
                str(recipe_data.get("metadata", {}))
            ))
            conn.commit()
            return recipe_data["recipe_id"]
    
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a recipe by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM recipes WHERE recipe_id = ?",
                (recipe_id,)
            )
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def list_recipes(
        self,
        objective: Optional[str] = None,
        model: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List recipes with filters"""
        conditions = []
        params = []
        
        if objective:
            conditions.append("objective LIKE ?")
            params.append(f"%{objective}%")
        if model:
            conditions.append("model = ?")
            params.append(model)
        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)
        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT * FROM recipes WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def search_recipes(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search on recipes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT r.* FROM recipes_fts fts
                JOIN recipes r ON r.rowid = fts.rowid
                WHERE recipes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_recipe_count(self) -> int:
        """Get total recipe count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM recipes")
            return cursor.fetchone()[0]
    
    def get_recipe_stats(self) -> Dict[str, Any]:
        """Get recipe statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN outcome = 'accepted' THEN 1 END) as accepted,
                    COUNT(CASE WHEN outcome = 'rejected' THEN 1 END) as rejected,
                    COUNT(DISTINCT model) as unique_models,
                    COUNT(DISTINCT objective) as unique_objectives
                FROM recipes
            """)
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, cursor.fetchone()))
