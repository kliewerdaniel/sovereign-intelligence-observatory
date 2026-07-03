"""Autonomous Evaluation Loop - HTTP API"""

from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends

from .models import SignalCreate, EvaluateRequest, EvaluateResponse, SignalResponse, DriftRequest, DriftReport, EvaluationStats
from .database import EvaluationDatabase
from .models import EvaluationSignal, SignalType, SignalStatus

app = FastAPI(title="Autonomous Evaluation Loop", version="2.0.0")


async def get_db() -> EvaluationDatabase:
    db = EvaluationDatabase()
    yield db
    await db.close()


@app.post("/api/signals", status_code=201)
async def create_signal(
    body: SignalCreate,
    db: EvaluationDatabase = Depends(get_db),
) -> dict:
    signal = EvaluationSignal(
        signal_id=body.signal_id,
        name=body.name,
        signal_type=body.signal_type,
        threshold=body.threshold,
    )
    signal_id = await db.create_signal(signal)
    return {"signal_id": signal_id, "status": "created"}


@app.post("/api/evaluate/{recipe_id}", response_model=EvaluateResponse)
async def evaluate_recipe(
    recipe_id: str,
    body: EvaluateRequest,
    db: EvaluationDatabase = Depends(get_db),
) -> EvaluateResponse:
    signal_row = await db.get_signal(body.signal_id)
    if not signal_row:
        raise HTTPException(status_code=404, detail=f"Signal not found: {body.signal_id}")

    signal = EvaluationSignal(
        signal_id=signal_row["signal_id"],
        name=signal_row["name"],
        signal_type=SignalType(signal_row["signal_type"]),
        threshold=signal_row["threshold"],
    )
    result = await db.run_evaluation(recipe_id, signal, body.score)
    return EvaluateResponse(
        result_id=f"result-{recipe_id}-{result.timestamp.strftime('%Y%m%d%H%M%S')}",
        recipe_id=recipe_id,
        signal_id=body.signal_id,
        score=body.score,
        passed=result.passed,
    )


@app.get("/api/signals/drift/{signal_id}", response_model=DriftReport)
async def check_signal_drift(
    signal_id: str,
    lookback_days: int = 30,
    db: EvaluationDatabase = Depends(get_db),
) -> DriftReport:
    drift_report = await db.detect_drift(signal_id, lookback_days)
    if not drift_report:
        raise HTTPException(status_code=404, detail=f"Signal not found: {signal_id}")
    return DriftReport(
        signal_id=drift_report.signal_id,
        old_correlation=drift_report.old_correlation,
        new_correlation=drift_report.new_correlation,
        drift_detected=drift_report.drift_detected,
        recommended_action=drift_report.recommended_action,
    )


@app.get("/api/signals", response_model=List[SignalResponse])
async def list_signals(
    db: EvaluationDatabase = Depends(get_db),
) -> List[SignalResponse]:
    signals = await db.get_signals()
    return [SignalResponse(**s) for s in signals]


@app.get("/api/evaluations/stats", response_model=EvaluationStats)
async def get_evaluation_stats(
    db: EvaluationDatabase = Depends(get_db),
) -> EvaluationStats:
    stats = await db.get_evaluation_stats()
    return EvaluationStats(**stats)


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "autonomous-evaluation-loop"}
