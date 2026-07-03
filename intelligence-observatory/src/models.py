"""
Intelligence Observatory - Data Models
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class IntelligenceNode:
    """Represents a point in the intelligence timeline"""
    date: str  # YYYY-MM-DD
    recipe_count: int = 0
    avg_score: float = 0.0
    memory_versions: List[str] = field(default_factory=list)
    prompt_versions: List[str] = field(default_factory=list)
    capability_index: float = 1.0  # Baseline normalized to 1.0


@dataclass
class ObsolescentPrompt:
    """Identifies a prompt that is no longer effective"""
    prompt_id: str
    usage_count: int = 0
    avg_relevance: float = 0.0
    suggested_action: str = ""
    trend: str = "declining"  # declining, stable, improving


@dataclass
class UnusedMemory:
    """Identifies a memory document that is never retrieved"""
    memory_id: str
    title: str = ""
    last_retrieved: Optional[datetime] = None
    usage_count: int = 0
    suggested_action: str = ""


@dataclass
class SignalCorrelation:
    """Represents correlation between cheap signals and expert quality"""
    signal_name: str
    correlation_coefficient: float = 0.0
    p_value: float = 1.0
    significance: str = "not_significant"  # significant, marginal, not_significant
    sample_size: int = 0


@dataclass
class CapabilityRegression:
    """Detects when recipe quality decreases"""
    task: str
    date_range: str
    score_change: float = 0.0
    contributing_factors: List[str] = field(default_factory=list)
    severity: str = "low"  # low, medium, high, critical


@dataclass
class CapabilityImprovement:
    """Detects when recipe quality increases"""
    task: str
    date_range: str
    score_change: float = 0.0
    drivers: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class IntelligenceReport:
    """Comprehensive intelligence report"""
    title: str
    date_from: str
    date_to: str
    generated_at: datetime = field(default_factory=datetime.now)
    summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    timeline: List[IntelligenceNode] = field(default_factory=list)
    regressions: List[CapabilityRegression] = field(default_factory=list)
    improvements: List[CapabilityImprovement] = field(default_factory=list)
    obsolescent_prompts: List[ObsolescentPrompt] = field(default_factory=list)
    unused_memories: List[UnusedMemory] = field(default_factory=list)
    signal_correlations: List[SignalCorrelation] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
