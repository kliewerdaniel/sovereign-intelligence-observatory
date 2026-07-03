"""Expert Signal Router - Data Models"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class SignalTier(Enum):
    NONE = "none"
    CHEAP = "cheap"
    EXPERT = "expert"


class EvaluationOutcome(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class SignalRoutingDecision:
    signal_type: SignalTier
    confidence: float
    routing_reason: str
    reviewed_by: Optional[str] = None


@dataclass
class ExpertEvaluation:
    recipe_id: str
    evaluation: Dict[str, Any]
    decision: SignalRoutingDecision
    feedback: str = ""
    reviewed_at: datetime = field(default_factory=datetime.now)
