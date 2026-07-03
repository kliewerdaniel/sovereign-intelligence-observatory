"""Tacit Judgment Extractor - Pydantic v2 Data Models"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    RECORDING = "recording"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class DecisionNode(BaseModel):
    node_id: str
    parent_id: Optional[str] = None
    condition: str = ""
    action: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""
    children: List[str] = Field(default_factory=list)


class ExpertSessionCreate(BaseModel):
    session_id: str = Field(..., min_length=1)
    expert_id: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    session_text: str = Field(..., min_length=1)


class SessionCorrection(BaseModel):
    correction_id: str
    session_id: str
    original_text: str
    corrected_text: str
    rationale: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str = SessionState.RECORDING.value
    corrections_count: int = 0
    decision_nodes_count: int = 0


class SessionResponse(BaseModel):
    session_id: str
    expert_id: str
    domain: str
    session_text: str
    status: str
    created_at: str
    corrections: List[Dict[str, Any]] = Field(default_factory=list)
    decision_tree: List[Dict[str, Any]] = Field(default_factory=list)


class DecisionTreeExport(BaseModel):
    tree_id: str
    session_id: str
    domain: str
    expert_id: str
    nodes: List[DecisionNode]
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    schema_version: str = "1.0.0"


class PatternAnalysis(BaseModel):
    pattern_id: str
    session_id: str
    pattern_type: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str
    extracted_rules: List[str] = Field(default_factory=list)
    suggested_decision_node: Optional[Dict[str, Any]] = None


class AnalyticResult(BaseModel):
    session_id: str
    patterns: List[PatternAnalysis] = Field(default_factory=list)
    decision_tree: Optional[DecisionTreeExport] = None
    analysis_duration_ms: int = 0
    status: str = SessionState.COMPLETE.value
