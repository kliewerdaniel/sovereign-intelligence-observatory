"""Intelligence Observatory - HTTP API"""
from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime

from .database import ObservatoryDatabase

app = FastAPI(title="Sovereign Intelligence Observatory", version="1.0.0")
db = ObservatoryDatabase()


@app.post("/api/timeline")
async def update_timeline(date: str, recipes: List[Dict[str, Any]]):
    """Update intelligence timeline"""
    db.update_timeline(date, recipes)
    return {"status": "updated", "date": date, "recipe_count": len(recipes)}


@app.get("/api/timeline/{start_date}/{end_date}")
async def get_timeline(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get intelligence timeline"""
    return db.get_timeline(start_date, end_date)


@app.post("/api/prompts/obsolescent")
async def update_obsolescent_prompt(
    prompt_id: str,
    prompt_name: str,
    usage_count: int,
    avg_relevance: float,
    trend: str = 'stable'
):
    """Update obsolescent prompt"""
    db.update_obsolescent_prompts(prompt_id, prompt_name, usage_count, avg_relevance, trend)
    return {"status": "updated", "prompt_id": prompt_id}


@app.get("/api/prompts/obsolescent")
async def get_obsolescent_prompts(lookback_days: int = Query(30)) -> List[Dict[str, Any]]:
    """Get obsolescent prompts"""
    return db.get_obsolescent_prompts(lookback_days)


@app.post("/api/memories/unused")
async def update_unused_memory(
    memory_id: str,
    title: str,
    usage_count: int,
    last_retrieved: Optional[str] = None
):
    """Update unused memory"""
    db.update_unused_memories(memory_id, title, usage_count, last_retrieved)
    return {"status": "updated", "memory_id": memory_id}


@app.get("/api/memories/unused")
async def get_unused_memories(lookback_days: int = Query(30)) -> List[Dict[str, Any]]:
    """Get unused memories"""
    return db.get_unused_memories(lookback_days)


@app.post("/api/signals/correlation")
async def update_signal_correlation(
    signal_name: str,
    correlation_coefficient: float,
    p_value: float,
    sample_size: int
):
    """Update signal correlation"""
    db.update_signal_correlation(signal_name, correlation_coefficient, p_value, sample_size)
    return {"status": "updated", "signal_name": signal_name}


@app.get("/api/signals/correlations")
async def get_signal_correlations() -> List[Dict[str, Any]]:
    """Get signal correlations"""
    return db.get_signal_correlations()


@app.post("/api/capability/change")
async def record_capability_change(
    task: str,
    date_from: str,
    date_to: str,
    score_change: float,
    change_type: str,
    factors: List[str],
    severity: str = 'low'
):
    """Record capability change"""
    db.record_capability_change(task, date_from, date_to, score_change, change_type, factors, severity)
    return {"status": "recorded", "task": task, "change_type": change_type}


@app.get("/api/capability/changes")
async def get_capability_changes(lookback_days: int = Query(7)) -> Dict[str, List[Dict[str, Any]]]:
    """Get recent capability changes"""
    return db.get_capability_changes(lookback_days)


@app.get("/api/observatory/stats")
async def get_observatory_stats() -> Dict[str, Any]:
    """Get overall observatory statistics"""
    return db.get_observatory_stats()


@app.get("/api/observatory/report")
async def generate_report(
    date_from: str = Query(...),
    date_to: str = Query(...),
    format: str = Query('json')
) -> Dict[str, Any]:
    """Generate intelligence report"""
    timeline = db.get_timeline(date_from, date_to)
    obsolescent_prompts = db.get_obsolescent_prompts()
    unused_memories = db.get_unused_memories()
    signal_correlations = db.get_signal_correlations()
    capability_changes = db.get_capability_changes()
    
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
        "summary": f"Report covers {len(timeline)} days with {len(obsolescent_prompts)} obsolescent prompts and {len(unused_memories)} unused memories."
    }
    
    if format == 'json':
        return report
    else:
        # Return markdown format
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


@app.get("/api/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "intelligence-observatory",
        "stats": db.get_observatory_stats()
    }
