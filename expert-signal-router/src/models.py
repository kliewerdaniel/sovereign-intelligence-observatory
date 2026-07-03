"""Expert Signal Router - Pydantic v2 Data Models"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SignalTier(str, Enum):
    NONE = "none"
    CHEAP = "cheap"
    EXPERT = "expert"


class EvaluationOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class RouteRequest(BaseModel):
    recipe_id: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class RouteResponse(BaseModel):
    evaluation_id: str
    signal_type: str
    decision: str
    confidence: float
    threshold_used: float


class ReviewRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(accepted|rejected|pending_review)$")
    feedback: str = Field(default="")
    reviewed_by: str = Field(..., min_length=1)


class RoutingSignal(BaseModel):
    signal_type: SignalTier
    confidence: float
    routing_reason: str


class ExpertEvaluation(BaseModel):
    recipe_id: str
    evaluation: Dict[str, Any]
    decision: RoutingSignal
    feedback: str = ""
    reviewed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
