"""Intelligence Observatory - HTTP API & WebSocket Telemetry"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect

from .models import (
    TimelineUpdate, ObsolescentPromptUpdate, UnusedMemoryUpdate,
    SignalCorrelationUpdate, CapabilityChangeRecord, ObservatoryStats,
)
from .database import ObservatoryDatabase
from .dashboard import router as dashboard_router
from .telemetry import telemetry_manager, TelemetryManager

app = FastAPI(title="Sovereign Intelligence Observatory", version="2.2.0")
app.include_router(dashboard_router)


async def get_db() -> ObservatoryDatabase:
    db = ObservatoryDatabase()
    yield db
    await db.close()


@app.post("/api/timeline")
async def update_timeline(
    body: TimelineUpdate,
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    await db.update_timeline(body.date, body.recipes)
    return {"status": "updated", "date": body.date, "recipe_count": len(body.recipes)}


@app.get("/api/timeline/{start_date}/{end_date}")
async def get_timeline(
    start_date: str,
    end_date: str,
    db: ObservatoryDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.get_timeline(start_date, end_date)


@app.post("/api/prompts/obsolescent")
async def update_obsolescent_prompt(
    body: ObsolescentPromptUpdate,
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    await db.update_obsolescent_prompts(
        body.prompt_id, body.prompt_name, body.usage_count, body.avg_relevance, body.trend
    )
    return {"status": "updated", "prompt_id": body.prompt_id}


@app.get("/api/prompts/obsolescent")
async def get_obsolescent_prompts(
    lookback_days: int = Query(30, ge=1),
    db: ObservatoryDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.get_obsolescent_prompts(lookback_days)


@app.post("/api/memories/unused")
async def update_unused_memory(
    body: UnusedMemoryUpdate,
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    await db.update_unused_memories(body.memory_id, body.title, body.usage_count, body.last_retrieved)
    return {"status": "updated", "memory_id": body.memory_id}


@app.get("/api/memories/unused")
async def get_unused_memories(
    lookback_days: int = Query(30, ge=1),
    db: ObservatoryDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.get_unused_memories(lookback_days)


@app.post("/api/signals/correlation")
async def update_signal_correlation(
    body: SignalCorrelationUpdate,
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    await db.update_signal_correlation(
        body.signal_name, body.correlation_coefficient, body.p_value, body.sample_size
    )
    return {"status": "updated", "signal_name": body.signal_name}


@app.get("/api/signals/correlations")
async def get_signal_correlations(
    db: ObservatoryDatabase = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await db.get_signal_correlations()


@app.post("/api/capability/change")
async def record_capability_change(
    body: CapabilityChangeRecord,
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    await db.record_capability_change(
        body.task, body.date_from, body.date_to, body.score_change,
        body.change_type, body.factors, body.severity,
    )
    return {"status": "recorded", "task": body.task, "change_type": body.change_type}


@app.get("/api/capability/changes")
async def get_capability_changes(
    lookback_days: int = Query(7, ge=1),
    db: ObservatoryDatabase = Depends(get_db),
) -> Dict[str, List[Dict[str, Any]]]:
    return await db.get_capability_changes(lookback_days)


@app.post("/api/recipes/archive")
async def archive_old_recipes(
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    from .archive import ArchivePipeline
    pipeline = ArchivePipeline(db._db, archive_dir="archives")
    result = await pipeline.archive_recipes()
    return result


@app.get("/api/recipes/archive/verify")
async def verify_archive(
    filename: str = Query(...),
    db: ObservatoryDatabase = Depends(get_db),
) -> Dict[str, Any]:
    from .archive import ArchivePipeline
    pipeline = ArchivePipeline(db._db, archive_dir="archives")
    return await pipeline.verify_archive(filename)


@app.get("/api/observatory/stats", response_model=ObservatoryStats)
async def get_observatory_stats(
    db: ObservatoryDatabase = Depends(get_db),
) -> ObservatoryStats:
    stats = await db.get_observatory_stats()
    return ObservatoryStats(**stats)


@app.get("/api/observatory/report")
async def generate_report(
    date_from: str = Query(...),
    date_to: str = Query(...),
    format: str = Query("json", pattern=r"^(json|markdown)$"),
    db: ObservatoryDatabase = Depends(get_db),
) -> Dict[str, Any]:
    timeline = await db.get_timeline(date_from, date_to)
    obsolescent_prompts = await db.get_obsolescent_prompts()
    unused_memories = await db.get_unused_memories()
    signal_correlations = await db.get_signal_correlations()
    capability_changes = await db.get_capability_changes()

    report = {
        "report_title": f"Intelligence Report: {date_from} to {date_to}",
        "generated_at": datetime.now().isoformat(),
        "date_from": date_from,
        "date_to": date_to,
        "timeline": timeline,
        "obsolescent_prompts": obsolescent_prompts,
        "unused_memories": unused_memories,
        "signal_correlations": signal_correlations,
        "capability_changes": capability_changes,
        "summary": f"Report covers {len(timeline)} days with {len(obsolescent_prompts)} obsolescent prompts and {len(unused_memories)} unused memories.",
    }

    if format == "markdown":
        md = f"# Intelligence Report: {date_from} to {date_to}\n\n"
        md += f"Generated: {datetime.now().isoformat()}\n\n"
        md += f"## Summary\n{report['summary']}\n\n"
        md += f"## Timeline ({len(timeline)} entries)\n"
        for entry in timeline:
            md += f"- **{entry['date']}**: {entry['recipe_count']} recipes, avg score {entry['avg_score']:.2f}\n"
        if obsolescent_prompts:
            md += f"\n## Obsolescent Prompts ({len(obsolescent_prompts)})\n"
            for prompt in obsolescent_prompts[:10]:
                md += f"- **{prompt['prompt_name']}**: {prompt['usage_count']} uses, relevance {prompt['avg_relevance']:.2f}\n"
        return {"report": md, "format": "markdown"}

    return report


@app.websocket("/api/observatory/stream")
async def telemetry_websocket(websocket: WebSocket) -> None:
    await telemetry_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await telemetry_manager.disconnect(websocket)


@app.on_event("shutdown")
async def shutdown_telemetry() -> None:
    await telemetry_manager.shutdown()


@app.get("/api/health")
async def health_check(
    db: ObservatoryDatabase = Depends(get_db),
) -> dict:
    stats = await db.get_observatory_stats()
    return {"status": "healthy", "service": "intelligence-observatory", "stats": stats}
