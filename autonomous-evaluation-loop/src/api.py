"""Autonomous Evaluation Loop - HTTP API"""
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any

from .database import EvaluationDatabase
from .models import EvaluationSignal, SignalType

app = FastAPI(title="Autonomous Evaluation Loop", version="1.0.0")
db = EvaluationDatabase()


@app.post("/api/signals")
async def create_signal(signal_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new evaluation signal"""
    signal = EvaluationSignal(
        signal_id=signal_data["signal_id"],
        name=signal_data["name"],
        signal_type=SignalType(signal_data["signal_type"]),
        threshold=signal_data["threshold"]
    )
    signal_id = db.create_signal(signal)
    return {"signal_id": signal_id, "status": "created"}


@app.post("/api/evaluate/{recipe_id}")
async def evaluate_recipe(recipe_id: str, signal_id: str, score: float) -> Dict[str, Any]:
    """Run evaluation on a recipe"""
    signals = db.get_signals()
    signal = next((s for s in signals if s["signal_id"] == signal_id), None)
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    result = db.run_evaluation(recipe_id, signal, score)
    return {"result_id": f"result-{recipe_id}-{result.timestamp.strftime('%Y%m%d%H%M%S')}", "passed": result.passed}


@app.get("/api/signals/drift/{signal_id}")
async def check_signal_drift(signal_id: str, lookback_days: int = 30) -> Dict[str, Any]:
    """Check for signal drift"""
    drift_report = db.detect_drift(signal_id, lookback_days)
    if not drift_report:
        raise HTTPException(status_code=404, detail="Signal not found")
    return drift_report.__dict__


@app.get("/api/signals")
async def list_signals() -> List[Dict[str, Any]]:
    """List all evaluation signals"""
    return db.get_signals()


@app.get("/api/evaluations/stats")
async def get_evaluation_stats() -> Dict[str, Any]:
    """Get evaluation statistics"""
    return db.get_evaluation_stats()


@app.get("/api/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "autonomous-evaluation-loop"}
