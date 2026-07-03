"""Sovereign Apprenticeship Engine - HTTP API"""

from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends

from .models import (
    ActionRecord, PromoteRequest, AgentStateResponse,
    ActionResponse, PromoteResponse, BudgetResponse, AutonomyLevel,
)
from .database import ApprenticeshipDatabase

app = FastAPI(title="Sovereign Apprenticeship Engine", version="2.0.0")


async def get_db() -> ApprenticeshipDatabase:
    db = ApprenticeshipDatabase()
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
    await db.record_action(agent_id, body.monitored, body.quality_score)
    state = await db.get_or_create_state(agent_id)
    return ActionResponse(
        current_level=state.level.value,
        autonomy_budget_remaining=state.autonomy_budget_remaining,
        autonomy_debt=state.autonomy_debt,
    )


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
    return BudgetResponse(
        agent_id=agent_id,
        remaining=state.autonomy_budget_remaining,
        used_today=state.total_actions - state.autonomy_budget_remaining,
    )


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "sovereign-apprenticeship-engine"}
