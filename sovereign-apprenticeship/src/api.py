"""Sovereign Apprenticeship Engine - HTTP API"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query

from .models import (
    ActionRecord, PromoteRequest, AgentStateResponse,
    ActionResponse, PromoteResponse, BudgetResponse, AutonomyLevel,
)
from .database import ApprenticeshipDatabase, OUTBOX_CIRCUIT_BREAKER_LIMIT

app = FastAPI(title="Sovereign Apprenticeship Engine", version="2.1.0")

# Optional outbox reference wired in at startup by the hosting layer.
_outbox = None


def wire_outbox(outbox_instance) -> None:
    global _outbox
    _outbox = outbox_instance


async def get_db() -> ApprenticeshipDatabase:
    db = ApprenticeshipDatabase(outbox=_outbox)
    yield db
    await db.close()


@app.get("/api/agent/{agent_id}", response_model=AgentStateResponse)
async def get_agent_state(
    agent_id: str,
    db: ApprenticeshipDatabase = Depends(get_db),
) -> AgentStateResponse:
    state = await db.get_or_create_state(agent_id)
    return AgentStateResponse(
        agent_id=state.agent_id,
        level=state.level.value,
        supervision_ratio=state.supervision_ratio,
        autonomy_budget_remaining=state.autonomy_budget_remaining,
        total_actions=state.total_actions,
        monitored_actions=state.monitored_actions,
        autonomy_debt=state.autonomy_debt,
        last_updated=state.last_updated.isoformat(),
    )


@app.post("/api/action/{agent_id}", response_model=ActionResponse)
async def record_action(
    agent_id: str,
    body: ActionRecord,
    db: ApprenticeshipDatabase = Depends(get_db),
) -> ActionResponse:
    result = await db.record_action(agent_id, body.monitored, body.quality_score)
    state = await db.get_or_create_state(agent_id)
    return ActionResponse(
        action_recorded=result.get("action_recorded", True),
        circuit_breaked=result.get("circuit_breaked", False),
        outbox_pending=result.get("outbox_pending", 0),
        circuit_breaker_limit=OUTBOX_CIRCUIT_BREAKER_LIMIT,
        current_level=state.level.value,
        autonomy_budget_remaining=state.autonomy_budget_remaining,
        autonomy_debt=state.autonomy_debt,
        action_cost=result.get("action_cost", 0.0),
        budget_used_today=result.get("budget_used_today", 0),
        budget_daily_limit=result.get("budget_daily_limit", 100),
        budget_exceeded=result.get("budget_exceeded", False),
    )


@app.get("/api/circuit-breaker/{agent_id}")
async def get_circuit_breaker_status(
    agent_id: str,
    db: ApprenticeshipDatabase = Depends(get_db),
) -> Dict[str, Any]:
    state = await db.get_or_create_state(agent_id)
    outbox_pending = 0
    circuit_breaked = False
    if _outbox is not None:
        outbox_pending = _outbox.count_pending()
        circuit_breaked = outbox_pending >= OUTBOX_CIRCUIT_BREAKER_LIMIT
    return {
        "agent_id": agent_id,
        "circuit_breaked": circuit_breaked,
        "outbox_pending": outbox_pending,
        "circuit_breaker_limit": OUTBOX_CIRCUIT_BREAKER_LIMIT,
        "current_level": state.level.value,
    }


@app.post("/api/promote/{agent_id}", response_model=PromoteResponse)
async def promote_agent(
    agent_id: str,
    body: PromoteRequest,
    db: ApprenticeshipDatabase = Depends(get_db),
) -> PromoteResponse:
    try:
        level = AutonomyLevel(body.new_level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid autonomy level: {body.new_level}")

    state_before = await db.get_or_create_state(agent_id)
    from_level = state_before.level.value

    await db.promote_agent(agent_id, level, body.reason, body.quality_threshold)
    state_after = await db.get_or_create_state(agent_id)

    return PromoteResponse(
        from_level=from_level,
        to_level=state_after.level.value,
        new_budget=state_after.autonomy_budget_remaining,
    )


@app.get("/api/transitions/{agent_id}")
async def get_transitions(
    agent_id: str,
    db: ApprenticeshipDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.get_transition_history(agent_id)


@app.get("/api/budget/{agent_id}", response_model=BudgetResponse)
async def get_budget(
    agent_id: str,
    db: ApprenticeshipDatabase = Depends(get_db),
) -> BudgetResponse:
    state = await db.get_or_create_state(agent_id)
    budget_row = await db._ensure_budget_row(agent_id)
    return BudgetResponse(
        agent_id=agent_id,
        daily_budget=budget_row["daily_budget"],
        used_today=budget_row["used_today"],
        remaining=max(0, budget_row["daily_budget"] - budget_row["used_today"]),
        warnings=budget_row["warnings_issued"],
    )


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "sovereign-apprenticeship-engine"}
