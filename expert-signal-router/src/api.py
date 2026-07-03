"""Expert Signal Router - HTTP API"""
from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List, Dict, Any

from .database import SignalDatabase

app = FastAPI(title="Expert Signal Router", version="1.0.0")
db = SignalDatabase()


@app.post("/api/route/{recipe_id}")
async def route_recipe(recipe_id: str, objective: str, confidence: float) -> Dict[str, Any]:
    """Route recipe evaluation based on confidence"""
    return db.route_recipe(recipe_id, objective, confidence)


@app.get("/api/pending-reviews")
async def get_pending_reviews() -> List[Dict[str, Any]]:
    """Get all pending expert reviews"""
    return db.get_pending_reviews()


@app.post("/api/review/{evaluation_id}")
async def record_review(
    evaluation_id: str,
    decision: str,
    feedback: str,
    reviewed_by: str
) -> Dict[str, str]:
    """Record expert review decision"""
    db.record_expert_review(evaluation_id, decision, feedback, reviewed_by)
    return {"status": "review_recorded"}


@app.get("/api/signals/stats")
async def get_signal_stats() -> Dict[str, Any]:
    """Get signal routing statistics"""
    return db.get_signal_statistics()


@app.get("/api/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "router": "expert-signal-router"}
