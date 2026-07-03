"""Tacit Judgment Extractor - FastAPI HTTP API"""

import logging
import json
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Depends

from .models import (
    ExpertSessionCreate, SessionCreateResponse, SessionResponse,
    SessionCorrection, DecisionNode, DecisionTreeExport, TreeExportResponse,
    AnalyticResult, ReasoningPattern,
)
from .database import TacitJudgmentDatabase
from .pipeline import TacitJudgmentPipeline
from shared.ollama_client import OllamaClient
from shared.config import Settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Tacit Judgment Extractor", version="1.1.0")
settings = Settings.from_env()


async def get_db() -> TacitJudgmentDatabase:
    db = TacitJudgmentDatabase()
    yield db
    await db.close()


async def get_ollama() -> OllamaClient:
    client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )
    yield client
    await client.close()


async def get_pipeline(
    db: TacitJudgmentDatabase = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> TacitJudgmentPipeline:
    return TacitJudgmentPipeline(db=db, ollama=ollama, settings=settings)


@app.post("/api/sessions", status_code=201, response_model=SessionCreateResponse)
async def create_session(
    body: ExpertSessionCreate,
    db: TacitJudgmentDatabase = Depends(get_db),
) -> SessionCreateResponse:
    await db.create_session(
        session_id=body.session_id,
        expert_id=body.expert_id,
        domain=body.domain,
        session_text=body.session_text,
    )
    return SessionCreateResponse(session_id=body.session_id)


@app.post("/api/sessions/{session_id}/corrections")
async def add_correction(
    session_id: str,
    original_text: str = Query(..., min_length=1),
    corrected_text: str = Query(..., min_length=1),
    rationale: str = Query(""),
    db: TacitJudgmentDatabase = Depends(get_db),
) -> dict:
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    correction_id = await db.add_correction(session_id, original_text, corrected_text, rationale)
    return {"correction_id": correction_id, "session_id": session_id}


@app.post("/api/sessions/{session_id}/analyze", response_model=AnalyticResult)
async def analyze_session(
    session_id: str,
    pipeline: TacitJudgmentPipeline = Depends(get_pipeline),
) -> AnalyticResult:
    session = await pipeline.db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    try:
        return await pipeline.analyze_session(session_id)
    except Exception as exc:
        logger.error("Analysis failed for session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")


@app.get("/api/sessions/{session_id}/tree")
async def export_decision_tree(
    session_id: str,
    db: TacitJudgmentDatabase = Depends(get_db),
) -> DecisionTreeExport:
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    nodes = session.get("decision_tree", [])
    if not nodes:
        raise HTTPException(status_code=404, detail="No decision tree found for this session")

    parsed = []
    for n in nodes:
        n["children"] = json.loads(n["children"]) if isinstance(n.get("children"), str) else n.get("children", [])
        parsed.append(DecisionNode(**n))
    return DecisionTreeExport(
        tree_id=f"tree-export-{session_id}",
        session_id=session_id,
        domain=session["domain"],
        expert_id=session["expert_id"],
        nodes=parsed,
    )


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: TacitJudgmentDatabase = Depends(get_db),
) -> SessionResponse:
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return SessionResponse(
        session_id=session["session_id"],
        expert_id=session["expert_id"],
        domain=session["domain"],
        session_text=session["session_text"],
        status=session["status"],
        created_at=session["created_at"],
        corrections=session.get("corrections", []),
        decision_tree=session.get("decision_tree", []),
    )


@app.get("/api/sessions")
async def list_sessions(
    expert_id: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: TacitJudgmentDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.list_sessions(
        expert_id=expert_id, domain=domain, status=status,
        limit=limit, offset=offset,
    )


@app.post("/api/expert/session", status_code=201, response_model=SessionCreateResponse)
async def create_expert_session(
    body: ExpertSessionCreate,
    db: TacitJudgmentDatabase = Depends(get_db),
) -> SessionCreateResponse:
    existing = await db.get_session(body.session_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Session already exists: {body.session_id}")
    await db.create_session(
        session_id=body.session_id,
        expert_id=body.expert_id,
        domain=body.domain,
        session_text=body.session_text,
    )
    return SessionCreateResponse(session_id=body.session_id)


@app.get("/api/expert/trees/{tree_id}/export", response_model=TreeExportResponse)
async def export_decision_tree_by_id(
    tree_id: str,
    db: TacitJudgmentDatabase = Depends(get_db),
) -> TreeExportResponse:
    export_row = await db.get_tree_export(tree_id)
    if export_row is None:
        raise HTTPException(status_code=404, detail=f"Tree export not found: {tree_id}")

    export_data = export_row.get("export_data", {})
    if isinstance(export_data, str):
        export_data = json.loads(export_data)
    nodes = [DecisionNode(**n) for n in export_data]

    return TreeExportResponse(
        tree_id=export_row["tree_id"],
        session_id=export_row["session_id"],
        domain=export_row["domain"],
        expert_id=export_row["expert_id"],
        nodes=nodes,
        schema_version=export_row.get("schema_version", "1.0.0"),
    )


@app.get("/api/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "tacit-judgment-extractor",
        "integrations": {
            "ollama": settings.enable_ollama,
        },
    }
