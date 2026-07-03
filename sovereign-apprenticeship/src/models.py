"""Sovereign Apprenticeship Engine - Data Models"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class AutonomyLevel(Enum):
    FULLY_SUPERVISED = "fully_supervised"      # 100% human oversight
    APPROVE_DANGEROUS = "approve_dangerous"     # Only dangerous actions reviewed
    APPROVE_NOVEL = "approve_novel"             # Only novel actions reviewed
    APPROVE_UNCERTAIN = "approve_uncertain"     # Only uncertain actions reviewed
    FULLY_AUTONOMOUS = "fully_autonomous"       # No human oversight


@dataclass
class AutonomyState:
    """Current autonomy state for an agent"""
    agent_id: str
    level: AutonomyLevel
    supervision_ratio: float  # 0.0 to 1.0 (0 = fully autonomous, 1 = fully supervised)
    autonomy_budget_remaining: int  # Number of unmonitored actions allowed
    total_actions: int = 0
    monitored_actions: int = 0
    autonomy_debt: float = 0.0  # Accumulated low-quality autonomous decisions
    last_updated: datetime = field(default_factory=datetime.now)
    phase_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AutonomyTransition:
    """Records a transition between autonomy levels"""
    agent_id: str
    from_level: AutonomyLevel
    to_level: AutonomyLevel
    reason: str
    quality_threshold: float
    transition_date: datetime = field(default_factory=datetime.now)
    contributing_factors: List[str] = field(default_factory=list)


@dataclass
class AutonomyBudget:
    """Budget for unmonitored autonomous actions"""
    agent_id: str
    daily_budget: int = 100
    used_today: int = 0
    reset_date: datetime = field(default_factory=datetime.now)
    warnings_issued: int = 0


@dataclass
class ScaffoldedTrainingData:
    """Training data extracted from supervised-to-autonomous transitions"""
    training_id: str
    agent_id: str
    supervised_examples: List[Dict[str, Any]]
    autonomous_examples: List[Dict[str, Any]]
    quality_transition_point: str  # When the transition happened
    training_metadata: Dict[str, Any] = field(default_factory=dict)
