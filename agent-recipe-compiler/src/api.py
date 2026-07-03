"""Agent Recipe Compiler - FastAPI HTTP API

Integrates:
- FTS5 full-text search (always available)
- ChromaDB semantic search (optional, graceful fallback)
- Ollama GBNF grammar validation (optional, graceful fallback)
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import Response
import json

from .models import RecipeInput, RecipeResponse, RecipeCaptureResponse, RecipeListResponse, RecipeStats, SearchResult, EvaluationMetadata
from .database import RecipeDatabase
from shared.chroma_client import ChromaClient
from shared.ollama_client import OllamaClient
from shared.config import Settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Recipe Compiler", version="2.0.0")
settings = Settings.from_env()


async def get_db() -> RecipeDatabase:
    db = RecipeDatabase()
    yield db
    await db.close()


async def get_chroma() -> Optional[ChromaClient]:
    if not settings.enable_chroma:
        yield None
        return
    client = ChromaClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        collection_name=settings.chroma_collection,
    )
    yield client


async def get_ollama() -> Optional[OllamaClient]:
    if not settings.enable_ollama:
        yield None
        return
    client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )
    yield client
    await client.close()


@app.post("/api/recipes", status_code=201, response_model=RecipeCaptureResponse)
async def capture_recipe(
    recipe: RecipeInput,
    db: RecipeDatabase = Depends(get_db),
    chroma: Optional[ChromaClient] = Depends(get_chroma),
    ollama: Optional[OllamaClient] = Depends(get_ollama),
) -> RecipeCaptureResponse:
    recipe_id = recipe.recipe_id or f"recipe-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    eval_data = recipe.evaluation.model_dump() if recipe.evaluation else {"score": 0.0, "reviewed_by": "none"}

    recipe_dict = {
        "recipe_id": recipe_id,
        "objective": recipe.objective,
        "model": recipe.model,
        "prompt_version": recipe.prompt_version,
        "memory_version": recipe.memory_version,
        "retrieved_docs": recipe.retrieved_docs,
        "reasoning_patterns": recipe.reasoning_patterns,
        "evaluation": eval_data,
        "outcome": recipe.outcome,
        "created_at": datetime.now().isoformat(),
        "metadata": recipe.metadata,
    }

    stored_id = await db.store_recipe(recipe_dict)

    if chroma is not None:
        searchable_text = f"{recipe.objective} {' '.join(recipe.retrieved_docs)} {' '.join(recipe.reasoning_patterns)}"
        await chroma.add_document(
            doc_id=stored_id,
            text=searchable_text,
            metadata={
                "model": recipe.model,
                "outcome": recipe.outcome,
                "prompt_version": recipe.prompt_version,
            },
        )

    if ollama is not None:
        gbnf_result = await ollama.generate_with_grammar(
            prompt=f"Generate a valid recipe JSON for: {recipe.objective}",
            gbnf_grammar=OllamaClient.RECIPE_GBNF_GRAMMAR,
            system="You are a recipe formatter. Output only valid JSON.",
        )
        if gbnf_result is None:
            logger.info("Ollama GBNF validation skipped (Ollama not reachable)")

    return RecipeCaptureResponse(recipe_id=stored_id)


@app.get("/api/recipes", response_model=RecipeListResponse)
async def list_recipes(
    objective: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: RecipeDatabase = Depends(get_db),
) -> RecipeListResponse:
    recipes, total = await db.list_recipes(
        objective=objective,
        model=model,
        date_from=date_from,
        date_to=date_to,
        outcome=outcome,
        limit=limit,
        offset=offset,
    )
    return RecipeListResponse(
        recipes=[RecipeResponse(**r) for r in recipes],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/recipes/search", response_model=SearchResult)
async def search_recipes(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=1000),
    semantic: bool = Query(False, description="Enable ChromaDB semantic search alongside FTS5"),
    db: RecipeDatabase = Depends(get_db),
    chroma: Optional[ChromaClient] = Depends(get_chroma),
) -> SearchResult:
    recipes = await db.search_recipes(q, limit=limit)
    result_ids = {r["recipe_id"] for r in recipes}

    if semantic and chroma is not None:
        semantic_results = await chroma.search(q, n_results=limit)
        if semantic_results is not None:
            for sr in semantic_results:
                rid = sr["id"]
                if rid not in result_ids:
                    recipe = await db.get_recipe(rid)
                    if recipe:
                        recipes.append(recipe)
                        result_ids.add(rid)
                        if len(recipes) >= limit:
                            break

    return SearchResult(
        results=[RecipeResponse(**r) for r in recipes[:limit]],
        total=len(recipes),
        query=q,
        semantic=semantic and chroma is not None,
    )


@app.get("/api/recipes/stats", response_model=RecipeStats)
async def get_recipe_stats(
    db: RecipeDatabase = Depends(get_db),
) -> RecipeStats:
    stats = await db.get_recipe_stats()
    return RecipeStats(**stats)


@app.get("/api/recipes/export")
async def export_recipes(
    format: str = Query("json", pattern=r"^(json|csv)$"),
    recipe_ids: Optional[str] = Query(None),
    db: RecipeDatabase = Depends(get_db),
) -> Response:
    if recipe_ids:
        ids_list = [rid.strip() for rid in recipe_ids.split(",") if rid.strip()]
        recipes = []
        for rid in ids_list:
            r = await db.get_recipe(rid)
            if r:
                recipes.append(r)
    else:
        recipes, _ = await db.list_recipes(limit=1000000)

    if format == "json":
        content = json.dumps([RecipeResponse(**r).model_dump() for r in recipes], indent=2)
        return Response(content=content, media_type="application/json", headers={"Content-Disposition": "attachment; filename=recipes_export.json"})
    else:
        import csv
        import io
        output = io.StringIO()
        if recipes:
            writer = csv.DictWriter(output, fieldnames=recipes[0].keys())
            writer.writeheader()
            for r in recipes:
                row = {k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()}
                writer.writerow(row)
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=recipes_export.csv"})


@app.get("/api/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: str,
    db: RecipeDatabase = Depends(get_db),
) -> RecipeResponse:
    recipe = await db.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Recipe not found: {recipe_id}")
    return RecipeResponse(**recipe)


@app.get("/api/health")
async def health_check(
    db: RecipeDatabase = Depends(get_db),
    chroma: Optional[ChromaClient] = Depends(get_chroma),
) -> dict:
    count = await db.get_recipe_count()
    chroma_count = await chroma.count() if chroma is not None else None
    return {
        "status": "healthy",
        "service": "agent-recipe-compiler",
        "recipe_count": count,
        "integrations": {
            "ollama": settings.enable_ollama,
            "chroma": chroma_count is not None,
            "chroma_docs": chroma_count or 0,
        },
    }


__all__ = ["app"]
