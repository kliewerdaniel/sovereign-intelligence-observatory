"""
Agent Recipe Compiler - HTTP API
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io
import uuid

from .models import Recipe
from .database import RecipeDatabase

app = FastAPI(title="Agent Recipe Compiler", version="1.0.0")
db = RecipeDatabase()


@app.post("/api/recipes", status_code=201)
async def capture_recipe(recipe: Dict[str, Any]) -> Dict[str, str]:
    """Capture a new recipe from agent run data"""
    try:
        # Validate required fields
        required_fields = ["objective", "model", "prompt_version", "memory_version"]
        for field in required_fields:
            if field not in recipe:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Add recipe_id if not provided
        if "recipe_id" not in recipe:
            recipe["recipe_id"] = f"recipe-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # Add metadata if not provided
        if "metadata" not in recipe:
            recipe["metadata"] = {}
        
        # Store recipe
        recipe_id = db.store_recipe(recipe)
        
        return {
            "recipe_id": recipe_id,
            "status": "captured"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to capture recipe: {str(e)}"
        )


@app.get("/api/recipes/{recipe_id}")
async def get_recipe(recipe_id: str) -> Dict[str, Any]:
    """Retrieve a recipe by ID"""
    recipe = db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=404,
            detail=f"Recipe not found: {recipe_id}"
        )
    return recipe


@app.get("/api/recipes")
async def list_recipes(
    objective: Optional[str] = Query(None, description="Filter by objective"),
    model: Optional[str] = Query(None, description="Filter by model"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    limit: int = Query(50, ge=1, le=1000, description="Number of recipes to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """List recipes with filters"""
    recipes = db.list_recipes(
        objective=objective,
        model=model,
        date_from=date_from,
        date_to=date_to,
        outcome=outcome,
        limit=limit,
        offset=offset
    )
    
    return {
        "recipes": recipes,
        "total": db.get_recipe_count(),
        "limit": limit,
        "offset": offset
    }


@app.get("/api/recipes/search")
async def search_recipes(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results")
) -> List[Dict[str, Any]]:
    """Full-text search on recipes"""
    recipes = db.search_recipes(q, limit=limit)
    return recipes


@app.get("/api/recipes/stats")
async def get_recipe_stats() -> Dict[str, Any]:
    """Get recipe statistics"""
    return db.get_recipe_stats()


@app.get("/api/recipes/export")
async def export_recipes(
    format: str = Query("json", description="Export format (json or csv)"),
    recipe_ids: Optional[List[str]] = Query(None, description="Specific recipe IDs to export")
) -> FileResponse:
    """Export recipes to JSON or CSV"""
    if recipe_ids:
        recipes = []
        for recipe_id in recipe_ids:
            recipe = db.get_recipe(recipe_id)
            if recipe:
                recipes.append(recipe)
    else:
        recipes = db.list_recipes(limit=1000000)  # Export all
    
    if format == "json":
        content = json.dumps(recipes, indent=2)
        filename = "recipes_export.json"
        media_type = "application/json"
    elif format == "csv":
        # Convert to CSV format
        output = io.StringIO()
        if recipes:
            writer = csv.DictWriter(output, fieldnames=recipes[0].keys())
            writer.writeheader()
            writer.writerows(recipes)
        content = output.getvalue()
        filename = "recipes_export.csv"
        media_type = "text/csv"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {format}. Use 'json' or 'csv'."
        )
    
    return FileResponse(
        path=None,
        content=content,
        filename=filename,
        media_type=media_type
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "recipe_count": db.get_recipe_count()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
