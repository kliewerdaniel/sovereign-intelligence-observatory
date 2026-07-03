"""Tests for Recipe models"""
from src.models import Recipe
from datetime import datetime


def test_recipe_creation():
    """Test creating a recipe with all required fields"""
    recipe = Recipe(
        objective="classify_paper",
        model="qwen3.5",
        prompt_version=5,
        memory_version=12
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


def test_recipe_to_dict():
    """Test converting recipe to dictionary"""
    recipe = Recipe(
        objective="test_task",
        model="llama3",
        prompt_version=3,
        memory_version=8,
        retrieved_docs=["doc_1", "doc_2"],
        reasoning_patterns=["analyze", "retrieve"],
        evaluation={"score": 0.95, "reviewed_by": "expert"},
        outcome="accepted"
    )
    
    recipe_dict = recipe.to_dict()
    
    assert recipe_dict["recipe_id"] == recipe.recipe_id
    assert recipe_dict["objective"] == "test_task"
    assert recipe_dict["model"] == "llama3"
    assert recipe_dict["prompt_version"] == 3
    assert recipe_dict["memory_version"] == 8
    assert recipe_dict["retrieved_docs"] == ["doc_1", "doc_2"]
    assert recipe_dict["reasoning_patterns"] == ["analyze", "retrieve"]
    assert recipe_dict["evaluation"]["score"] == 0.95
    assert recipe_dict["outcome"] == "accepted"


def test_recipe_from_dict():
    """Test creating recipe from dictionary"""
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
        "metadata": {"key": "value"}
    }
    
    recipe = Recipe.from_dict(data)
    
    assert recipe.recipe_id == "recipe-20240101-120000-abc123"
    assert recipe.objective == "test_task"
    assert recipe.model == "llama3"
    assert recipe.prompt_version == 3
    assert recipe.memory_version == 8
    assert recipe.outcome == "accepted"


def test_recipe_custom_id():
    """Test creating recipe with custom ID"""
    recipe = Recipe(
        objective="task",
        model="model1",
        prompt_version=1,
        memory_version=1,
        recipe_id="recipe-custom-123"
    )
    
    assert recipe.recipe_id == "recipe-custom-123"


def test_recipe_metadata():
    """Test recipe with metadata"""
    recipe = Recipe(
        objective="task",
        model="model1",
        prompt_version=1,
        memory_version=1,
        metadata={"custom_field": "value", "nested": {"key": "val"}}
    )
    
    assert recipe.metadata["custom_field"] == "value"
    assert recipe.metadata["nested"]["key"] == "val"
