"""
Agent Recipe Compiler - Data Models
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4


class Recipe:
    """Represents an agent run recipe artifact"""
    
    def __init__(
        self,
        objective: str,
        model: str,
        prompt_version: int,
        memory_version: int,
        recipe_id: Optional[str] = None,
        retrieved_docs: Optional[List[str]] = None,
        reasoning_patterns: Optional[List[str]] = None,
        evaluation: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.recipe_id = recipe_id or f"recipe-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        self.objective = objective
        self.model = model
        self.prompt_version = prompt_version
        self.memory_version = memory_version
        self.retrieved_docs = retrieved_docs or []
        self.reasoning_patterns = reasoning_patterns or []
        self.evaluation = evaluation or {"score": 0.0, "reviewed_by": "none"}
        self.outcome = outcome or "pending"
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recipe to dictionary for storage"""
        return {
            "recipe_id": self.recipe_id,
            "objective": self.objective,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "memory_version": self.memory_version,
            "retrieved_docs": self.retrieved_docs,
            "reasoning_patterns": self.reasoning_patterns,
            "evaluation": self.evaluation,
            "outcome": self.outcome,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        """Create recipe from dictionary"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            objective=data["objective"],
            model=data["model"],
            prompt_version=data["prompt_version"],
            memory_version=data["memory_version"],
            recipe_id=data.get("recipe_id"),
            retrieved_docs=data.get("retrieved_docs", []),
            reasoning_patterns=data.get("reasoning_patterns", []),
            evaluation=data.get("evaluation", {}),
            outcome=data.get("outcome", "pending"),
            created_at=created_at,
            metadata=data.get("metadata", {})
        )
