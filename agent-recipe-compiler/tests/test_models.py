"""Unit tests for Agent Recipe Compiler models"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from src.models import (
    RecipeInput, Recipe, EvaluationMetadata, RecipeResponse,
)


class TestRecipeInput:
    def test_valid_recipe_input(self):
        data = RecipeInput(
            objective="classify_paper",
            model="qwen3.5",
            prompt_version=5,
            memory_version=12,
        )
        assert data.objective == "classify_paper"
        assert data.model == "qwen3.5"
        assert data.prompt_version == 5
        assert data.memory_version == 12
        assert data.outcome == "pending"
        assert data.retrieved_docs == []
        assert data.reasoning_patterns == []

    def test_rejects_empty_objective(self):
        with pytest.raises(ValidationError):
            RecipeInput(objective="", model="m", prompt_version=1, memory_version=1)

    def test_rejects_negative_prompt_version(self):
        with pytest.raises(ValidationError):
            RecipeInput(objective="x", model="m", prompt_version=0, memory_version=1)

    def test_rejects_invalid_outcome(self):
        with pytest.raises(ValidationError):
            RecipeInput(
                objective="x", model="m", prompt_version=1, memory_version=1,
                outcome="invalid",
            )

    def test_rejects_empty_reasoning_items(self):
        with pytest.raises(ValidationError):
            RecipeInput(
                objective="x", model="m", prompt_version=1, memory_version=1,
                reasoning_patterns=[""],
            )

    def test_full_recipe_input(self):
        data = RecipeInput(
            objective="test",
            model="llama3",
            prompt_version=3,
            memory_version=8,
            retrieved_docs=["doc_1", "doc_2"],
            reasoning_patterns=["analyze", "retrieve"],
            evaluation=EvaluationMetadata(score=0.95, reviewed_by="expert"),
            outcome="accepted",
            metadata={"env": "prod"},
        )
        assert data.evaluation.score == 0.95
        assert data.evaluation.reviewed_by == "expert"
        assert len(data.retrieved_docs) == 2
        assert data.metadata["env"] == "prod"


class TestRecipeDomain:
    def test_recipe_creation(self):
        recipe = Recipe(
            objective="classify_paper",
            model="qwen3.5",
            prompt_version=5,
            memory_version=12,
        )
        assert recipe.recipe_id.startswith("recipe-")
        assert recipe.objective == "classify_paper"
        assert recipe.model == "qwen3.5"
        assert recipe.prompt_version == 5
        assert recipe.memory_version == 12
        assert recipe.evaluation == {"score": 0.0, "reviewed_by": "none"}
        assert recipe.outcome == "pending"
        assert recipe.retrieved_docs == []
        assert recipe.reasoning_patterns == []

    def test_recipe_to_dict(self):
        recipe = Recipe(
            objective="test_task",
            model="llama3",
            prompt_version=3,
            memory_version=8,
            retrieved_docs=["doc_1", "doc_2"],
            reasoning_patterns=["analyze", "retrieve"],
            evaluation={"score": 0.95, "reviewed_by": "expert"},
            outcome="accepted",
        )
        recipe_dict = recipe.to_dict()
        assert recipe_dict["recipe_id"] == recipe.recipe_id
        assert recipe_dict["objective"] == "test_task"
        assert recipe_dict["evaluation"]["score"] == 0.95

    def test_recipe_from_dict(self):
        data = {
            "recipe_id": "recipe-20240101-120000-abc123",
            "objective": "test_task",
            "model": "llama3",
            "prompt_version": 3,
            "memory_version": 8,
            "retrieved_docs": ["doc_1"],
            "reasoning_patterns": ["analyze"],
            "evaluation": {"score": 0.9},
            "outcome": "accepted",
            "created_at": "2024-01-01T12:00:00",
            "metadata": {"key": "value"},
        }
        recipe = Recipe.from_dict(data)
        assert recipe.recipe_id == "recipe-20240101-120000-abc123"
        assert recipe.objective == "test_task"

    def test_recipe_custom_id(self):
        recipe = Recipe(
            objective="task", model="model1",
            prompt_version=1, memory_version=1,
            recipe_id="recipe-custom-123",
        )
        assert recipe.recipe_id == "recipe-custom-123"

    def test_recipe_metadata(self):
        recipe = Recipe(
            objective="task", model="model1",
            prompt_version=1, memory_version=1,
            metadata={"custom_field": "value", "nested": {"key": "val"}},
        )
        assert recipe.metadata["custom_field"] == "value"
        assert recipe.metadata["nested"]["key"] == "val"


class TestEvaluationMetadata:
    def test_defaults(self):
        m = EvaluationMetadata()
        assert m.score == 0.0
        assert m.reviewed_by == "none"

    def test_score_range(self):
        EvaluationMetadata(score=0.5)
        with pytest.raises(ValidationError):
            EvaluationMetadata(score=-0.1)
        with pytest.raises(ValidationError):
            EvaluationMetadata(score=1.1)
