"""Autonomous Evaluation Loop - Pydantic v2 Data Models"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    HEURISTIC = "heuristic"
    STRUCTURED = "structured"
    EXPERT = "expert"


class SignalStatus(str, Enum):
    ACTIVE = "active"
    DRIFTING = "drifting"
    OBSOLETE = "obsolete"


class SignalCreate(BaseModel):
    signal_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    signal_type: SignalType
    threshold: float = Field(..., ge=0.0, le=1.0)


class EvaluateRequest(BaseModel):
    signal_id: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)


class EvaluateResponse(BaseModel):
    result_id: str
    recipe_id: str
    signal_id: str
    score: float
    passed: bool


class SignalResponse(BaseModel):
    signal_id: str
    name: str
    signal_type: str
    threshold: float
    status: str
    correlation_coefficient: float = 0.0
    p_value: float = 1.0
    last_updated: str


class DriftRequest(BaseModel):
    lookback_days: int = Field(default=30, ge=1, le=365)


class DriftReport(BaseModel):
    signal_id: str
    old_correlation: float
    new_correlation: float
    drift_detected: bool
    recommended_action: str


class EvaluationStats(BaseModel):
    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0


class EvaluationSignal:
    """Domain model for evaluation signals."""

    def __init__(
        self,
        signal_id: str,
        name: str,
        signal_type: SignalType,
        threshold: float,
        status: SignalStatus = SignalStatus.ACTIVE,
        correlation_coefficient: float = 0.0,
        p_value: float = 1.0,
        last_updated: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.signal_id = signal_id
        self.name = name
        self.signal_type = signal_type
        self.threshold = threshold
        self.status = status
        self.correlation_coefficient = correlation_coefficient
        self.p_value = p_value
        self.last_updated = last_updated or datetime.now()
        self.metadata = metadata or {}


class EvaluationResult:
    """Domain model for evaluation results."""

    def __init__(
        self,
        recipe_id: str,
        signal_id: str,
        score: float,
        passed: bool,
        timestamp: Optional[datetime] = None,
    ):
        self.recipe_id = recipe_id
        self.signal_id = signal_id
        self.score = score
        self.passed = passed
        self.timestamp = timestamp or datetime.now()


class SignalDriftReport:
    """Domain model for drift detection reports."""

    def __init__(
        self,
        signal_id: str,
        old_correlation: float,
        new_correlation: float,
        drift_detected: bool,
        recommended_action: str = "",
    ):
        self.signal_id = signal_id
        self.old_correlation = old_correlation
        self.new_correlation = new_correlation
        self.drift_detected = drift_detected
        self.drift_threshold = 0.2
        self.recommended_action = recommended_action
