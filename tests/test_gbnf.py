"""Tests for GBNF grammar generator"""

import pytest
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from shared.gbnf import gbnf_schema


class NestedModel(BaseModel):
    name: str
    value: float


class TestModel(BaseModel):
    name: str
    count: int
    score: float = 0.0
    active: bool = True
    tags: List[str] = Field(default_factory=list)
    nested: Optional[NestedModel] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TestGBNF:
    def test_gbnf_output_is_string(self):
        result = gbnf_schema(TestModel)
        assert isinstance(result, str)
        assert result.startswith("root ::= TestModel")

    def test_gbnf_contains_model_name(self):
        result = gbnf_schema(TestModel)
        assert "TestModel" in result

    def test_gbnf_contains_field_names(self):
        result = gbnf_schema(TestModel)
        assert "name" in result
        assert "count" in result
        assert "score" in result
        assert "active" in result

    def test_gbnf_contains_basic_types(self):
        result = gbnf_schema(TestModel)
        assert "string" in result
        assert "integer" in result
        assert "number" in result
        assert "boolean" in result

    def test_gbnf_contains_nested_model(self):
        result = gbnf_schema(TestModel)
        assert "NestedModel" in result

    def test_gbnf_root_rule(self):
        result = gbnf_schema(TestModel)
        lines = result.strip().split("\n")
        assert lines[0] == "root ::= TestModel"

    def test_gbnf_with_empty_model(self):
        class EmptyModel(BaseModel):
            pass

        result = gbnf_schema(EmptyModel)
        assert "EmptyModel" in result

    def test_gbnf_with_optional_field(self):
        class OptionalModel(BaseModel):
            name: str
            description: Optional[str] = None

        result = gbnf_schema(OptionalModel)
        assert "OptionalModel" in result

    def test_gbnf_with_list_field(self):
        class ListModel(BaseModel):
            items: List[str] = Field(default_factory=list)

        result = gbnf_schema(ListModel)
        assert "ListModel" in result
        assert "array" in result

    def test_gbnf_with_dict_field(self):
        class DictModel(BaseModel):
            config: Dict[str, Any] = Field(default_factory=dict)

        result = gbnf_schema(DictModel)
        assert "DictModel" in result
        assert "object" in result

    def test_gbnf_with_int_field(self):
        class IntModel(BaseModel):
            age: int

        result = gbnf_schema(IntModel)
        assert "integer" in result

    def test_gbnf_with_float_field(self):
        class FloatModel(BaseModel):
            price: float

        result = gbnf_schema(FloatModel)
        assert "number" in result

    def test_gbnf_with_bool_field(self):
        class BoolModel(BaseModel):
            enabled: bool

        result = gbnf_schema(BoolModel)
        assert "boolean" in result

    def test_gbnf_parseable(self):
        result = gbnf_schema(TestModel)
        assert "::=" in result
        assert "root" in result

    def test_gbnf_deeply_nested(self):
        class Inner(BaseModel):
            x: int

        class Outer(BaseModel):
            inner: Inner
            name: str

        result = gbnf_schema(Outer)
        assert "Outer" in result
        assert "Inner" in result
