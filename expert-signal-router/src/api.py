"""Expert Signal Router - HTTP API"""

from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends

from .models import RouteRequest, RouteResponse, ReviewRequest
from .database import SignalDatabase

app = FastAPI(title="Expert Signal Router", version="2.0.0")


async def get_db() -> SignalDatabase:
    db = SignalDatabase()
    yield db
    await db.close()


@app.post("/api/route/{recipe_id}", response_model=RouteResponse)
async def route_recipe(
    recipe_id: str,
    body: RouteRequest,
    db: SignalDatabase = Depends(get_db),
) -> RouteResponse:
    result = await db.route_recipe(recipe_id, body.objective, body.confidence)
    return RouteResponse(**result)


@app.get("/api/pending-reviews")
async def get_pending_reviews(
    db: SignalDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.get_pending_reviews()


@app.post("/api/review/{evaluation_id}")
async def record_review(
    evaluation_id: str,
    body: ReviewRequest,
    db: SignalDatabase = Depends(get_db),
) -> dict:
    await db.record_expert_review(evaluation_id, body.decision, body.feedback, body.reviewed_by)
    return {"status": "review_recorded", "evaluation_id": evaluation_id}


@app.get("/api/signals/stats")
async def get_signal_stats(
    db: SignalDatabase = Depends(get_db),
) -> Dict[str, Any]:
    return await db.get_signal_statistics()


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "expert-signal-router"}
