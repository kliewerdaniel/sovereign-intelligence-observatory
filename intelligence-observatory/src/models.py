"""Intelligence Observatory - Pydantic v2 Data Models"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    date: str
    recipe_count: int = 0
    avg_score: float = 0.0
    capability_index: float = 1.0
    memory_versions: List[str] = Field(default_factory=list)
    prompt_versions: List[str] = Field(default_factory=list)


class TimelineUpdate(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    recipes: List[Dict[str, Any]]


class ObsolescentPromptUpdate(BaseModel):
    prompt_id: str = Field(..., min_length=1)
    prompt_name: str = Field(..., min_length=1)
    usage_count: int = Field(..., ge=0)
    avg_relevance: float = Field(..., ge=0.0, le=1.0)
    trend: str = Field(default="stable", pattern=r"^(declining|stable|improving)$")


class UnusedMemoryUpdate(BaseModel):
    memory_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    usage_count: int = Field(..., ge=0)
    last_retrieved: Optional[str] = None


class SignalCorrelationUpdate(BaseModel):
    signal_name: str = Field(..., min_length=1)
    correlation_coefficient: float = Field(..., ge=-1.0, le=1.0)
    p_value: float = Field(..., ge=0.0, le=1.0)
    sample_size: int = Field(..., ge=1)


class CapabilityChangeRecord(BaseModel):
    task: str = Field(..., min_length=1)
    date_from: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    score_change: float
    change_type: str = Field(..., pattern=r"^(regression|improvement)$")
    factors: List[str] = Field(default_factory=list)
    severity: str = Field(default="low", pattern=r"^(low|medium|high|critical)$")


class ObservatoryStats(BaseModel):
    timeline_entries: int = 0
    obsolescent_prompts: int = 0
    unused_memories: int = 0
    signal_correlations: int = 0
    capability_changes: int = 0
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class IntelligenceReport(BaseModel):
    report_title: str
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    date_from: str
    date_to: str
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    obsolescent_prompts: List[Dict[str, Any]] = Field(default_factory=list)
    unused_memories: List[Dict[str, Any]] = Field(default_factory=list)
    signal_correlations: List[Dict[str, Any]] = Field(default_factory=list)
    capability_changes: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class IntelligenceNode:
    """Domain model for timeline intelligence nodes."""

    def __init__(
        self,
        date: str,
        recipe_count: int = 0,
        avg_score: float = 0.0,
        memory_versions: Optional[List[str]] = None,
        prompt_versions: Optional[List[str]] = None,
        capability_index: float = 1.0,
    ):
        self.date = date
        self.recipe_count = recipe_count
        self.avg_score = avg_score
        self.memory_versions = memory_versions or []
        self.prompt_versions = prompt_versions or []
        self.capability_index = capability_index


class ObsolescentPrompt:
    """Domain model for obsolescent prompt detection."""

    def __init__(
        self,
        prompt_id: str,
        usage_count: int = 0,
        avg_relevance: float = 0.0,
        suggested_action: str = "",
        trend: str = "declining",
    ):
        self.prompt_id = prompt_id
        self.usage_count = usage_count
        self.avg_relevance = avg_relevance
        self.suggested_action = suggested_action
        self.trend = trend


class UnusedMemory:
    """Domain model for unused memory detection."""

    def __init__(
        self,
        memory_id: str,
        title: str = "",
        last_retrieved: Optional[datetime] = None,
        usage_count: int = 0,
        suggested_action: str = "",
    ):
        self.memory_id = memory_id
        self.title = title
        self.last_retrieved = last_retrieved
        self.usage_count = usage_count
        self.suggested_action = suggested_action


class SignalCorrelation:
    """Domain model for signal correlation analysis."""

    def __init__(
        self,
        signal_name: str,
        correlation_coefficient: float = 0.0,
        p_value: float = 1.0,
        significance: str = "not_significant",
        sample_size: int = 0,
    ):
        self.signal_name = signal_name
        self.correlation_coefficient = correlation_coefficient
        self.p_value = p_value
        self.significance = significance
        self.sample_size = sample_size


class CapabilityChange:
    """Domain model for capability regression/improvement detection."""

    def __init__(
        self,
        task: str,
        date_range: str,
        score_change: float = 0.0,
        contributing_factors: Optional[List[str]] = None,
        severity: str = "low",
        change_type: str = "regression",
    ):
        self.task = task
        self.date_range = date_range
        self.score_change = score_change
        self.contributing_factors = contributing_factors or []
        self.severity = severity
        self.change_type = change_type
