"""
FastAPI Web Server for Perplexity-like Search
Run: uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
from app_simple import run_search  # Import the simplified pipeline

app = FastAPI(title="Ollama Perplexity", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    model: str = "llama3.2:3b"


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the new clean search interface."""
    try:
        with open("search.html") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to old index.html if search.html doesn't exist
        with open("index.html") as f:
            return f.read()


@app.get("/old", response_class=HTMLResponse)
async def old_interface():
    """Serve the old interface."""
    with open("index.html") as f:
        return f.read()


@app.post("/search")
async def search(req: SearchRequest):
    """Run the full search pipeline and return results."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = await asyncio.to_thread(run_search, req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def list_models():
    """List available Ollama models."""
    import ollama
    try:
        models = ollama.list()
        return {"models": [m['model'] for m in models.get('models', [])]}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok"}
