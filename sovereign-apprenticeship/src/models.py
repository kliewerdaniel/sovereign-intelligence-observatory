"""Sovereign Apprenticeship Engine - Pydantic v2 Data Models"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AutonomyLevel(str, Enum):
    FULLY_SUPERVISED = "fully_supervised"
    APPROVE_DANGEROUS = "approve_dangerous"
    APPROVE_NOVEL = "approve_novel"
    APPROVE_UNCERTAIN = "approve_uncertain"
    FULLY_AUTONOMOUS = "fully_autonomous"


class ActionRecord(BaseModel):
    monitored: bool
    quality_score: float = Field(..., ge=0.0, le=1.0)


class PromoteRequest(BaseModel):
    new_level: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    quality_threshold: float = Field(..., ge=0.0, le=1.0)


class AgentStateResponse(BaseModel):
    agent_id: str
    level: str
    supervision_ratio: float
    autonomy_budget_remaining: int
    total_actions: int
    monitored_actions: int
    autonomy_debt: float
    last_updated: str


class ActionResponse(BaseModel):
    action_recorded: bool = True
    circuit_breaked: bool = False
    outbox_pending: int = 0
    circuit_breaker_limit: int = 50
    current_level: str
    autonomy_budget_remaining: int
    autonomy_debt: float
    action_cost: float = 0.0
    budget_used_today: int = 0
    budget_daily_limit: int = 100
    budget_exceeded: bool = False


class PromoteResponse(BaseModel):
    promoted: bool = True
    from_level: str
    to_level: str
    new_budget: int


class BudgetResponse(BaseModel):
    agent_id: str
    daily_budget: int = 100
    used_today: int = 0
    remaining: int = 0
    warnings: int = 0


class AutonomyState:
    """Domain model for agent autonomy state."""

    def __init__(
        self,
        agent_id: str,
        level: AutonomyLevel,
        supervision_ratio: float,
        autonomy_budget_remaining: int,
        total_actions: int = 0,
        monitored_actions: int = 0,
        autonomy_debt: float = 0.0,
        last_updated: Optional[datetime] = None,
        phase_history: Optional[List[Dict[str, Any]]] = None,
    ):
        self.agent_id = agent_id
        self.level = level
        self.supervision_ratio = supervision_ratio
        self.autonomy_budget_remaining = autonomy_budget_remaining
        self.total_actions = total_actions
        self.monitored_actions = monitored_actions
        self.autonomy_debt = autonomy_debt
        self.last_updated = last_updated or datetime.now()
        self.phase_history = phase_history or []


class AutonomyTransition:
    """Domain model for autonomy level transitions."""

    def __init__(
        self,
        agent_id: str,
        from_level: AutonomyLevel,
        to_level: AutonomyLevel,
        reason: str,
        quality_threshold: float,
        transition_date: Optional[datetime] = None,
        contributing_factors: Optional[List[str]] = None,
    ):
        self.agent_id = agent_id
        self.from_level = from_level
        self.to_level = to_level
        self.reason = reason
        self.quality_threshold = quality_threshold
        self.transition_date = transition_date or datetime.now()
        self.contributing_factors = contributing_factors or []


class AutonomyBudget:
    """Domain model for autonomy budget tracking."""

    def __init__(
        self,
        agent_id: str,
        daily_budget: int = 100,
        used_today: int = 0,
        reset_date: Optional[datetime] = None,
        warnings_issued: int = 0,
    ):
        self.agent_id = agent_id
        self.daily_budget = daily_budget
        self.used_today = used_today
        self.reset_date = reset_date or datetime.now()
        self.warnings_issued = warnings_issued


class ScaffoldedTrainingData:
    """Domain model for training data extracted from transitions."""

    def __init__(
        self,
        training_id: str,
        agent_id: str,
        supervised_examples: List[Dict[str, Any]],
        autonomous_examples: List[Dict[str, Any]],
        quality_transition_point: str,
        training_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.training_id = training_id
        self.agent_id = agent_id
        self.supervised_examples = supervised_examples
        self.autonomous_examples = autonomous_examples
        self.quality_transition_point = quality_transition_point
        self.training_metadata = training_metadata or {}
