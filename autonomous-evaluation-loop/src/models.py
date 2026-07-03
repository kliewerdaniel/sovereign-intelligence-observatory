"""Autonomous Evaluation Loop - Data Models"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class SignalType(Enum):
    HEURISTIC = "heuristic"
    STRUCTURED = "structured"
    EXPERT = "expert"


class SignalStatus(Enum):
    ACTIVE = "active"
    DRIFTING = "drifting"
    OBSOLETE = "obsolete"


@dataclass
class EvaluationSignal:
    signal_id: str
    name: str
    signal_type: SignalType
    threshold: float
    status: SignalStatus = SignalStatus.ACTIVE
    correlation_coefficient: float = 0.0
    p_value: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    recipe_id: str
    signal_id: str
    score: float
    passed: bool
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SignalDriftReport:
    signal_id: str
    old_correlation: float
    new_correlation: float
    drift_detected: bool
    drift_threshold: float = 0.2
    recommended_action: str = ""
