"""Sovereign Apprenticeship Engine - HTTP API"""
from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any

from .database import ApprenticeshipDatabase
from .models import AutonomyLevel

app = FastAPI(title="Sovereign Apprenticeship Engine", version="1.0.0")
db = ApprenticeshipDatabase()


@app.get("/api/agent/{agent_id}")
async def get_agent_state(agent_id: str) -> Dict[str, Any]:
    """Get current autonomy state for an agent"""
    state = db.get_or_create_state(agent_id)
    return {
        "agent_id": state.agent_id,
        "level": state.level.value,
        "supervision_ratio": state.supervision_ratio,
        "autonomy_budget_remaining": state.autonomy_budget_remaining,
        "total_actions": state.total_actions,
        "monitored_actions": state.monitored_actions,
        "autonomy_debt": state.autonomy_debt,
        "last_updated": state.last_updated.isoformat()
    }


@app.post("/api/action/{agent_id}")
async def record_action(
    agent_id: str,
    monitored: bool,
    quality_score: float
) -> Dict[str, Any]:
    """Record an action and update autonomy state"""
    db.record_action(agent_id, monitored, quality_score)
    state = db.get_or_create_state(agent_id)
    return {
        "action_recorded": True,
        "current_level": state.level.value,
        "autonomy_budget_remaining": state.autonomy_budget_remaining,
        "autonomy_debt": state.autonomy_debt
    }


@app.post("/api/promote/{agent_id}")
async def promote_agent(
    agent_id: str,
    new_level: str,
    reason: str,
    quality_threshold: float
) -> Dict[str, Any]:
    """Promote agent to higher autonomy level"""
    try:
        level = AutonomyLevel(new_level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid autonomy level: {new_level}")
    
    db.promote_agent(agent_id, level, reason, quality_threshold)
    state = db.get_or_create_state(agent_id)
    return {
        "promoted": True,
        "from_level": state.level.value,
        "to_level": state.level.value,
        "new_budget": state.autonomy_budget_remaining
    }


@app.get("/api/transitions/{agent_id}")
async def get_transitions(agent_id: str) -> List[Dict[str, Any]]:
    """Get transition history for an agent"""
    return db.get_transition_history(agent_id)


@app.get("/api/budget/{agent_id}")
async def get_budget(agent_id: str) -> Dict[str, Any]:
    """Get current autonomy budget status"""
    state = db.get_or_create_state(agent_id)
    return {
        "agent_id": agent_id,
        "daily_budget": 100,
        "used_today": state.total_actions - state.autonomy_budget_remaining,
        "remaining": state.autonomy_budget_remaining,
        "warnings": 0
    }


@app.get("/api/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "sovereign-apprenticeship-engine"}
