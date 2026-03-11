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
from image_gen import generate_image, create_image_prompt_from_answer
from wordpress import publish_search_result, upload_image
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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


class ImageGenerationRequest(BaseModel):
    prompt: str


class ImageFromAnswerRequest(BaseModel):
    query: str
    answer: str


class UploadImageToWordPressRequest(BaseModel):
    image_data: str
    title: str = "ai-image"


class PublishToWordPressRequest(BaseModel):
    query: str
    answer: str
    sources: list[dict] = []
    status: str = "draft"
    media_id: int | None = None
    image_url: str | None = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the new clean search interface."""
    try:
        with open("search.html", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to old index.html if search.html doesn't exist
        with open("index.html", encoding="utf-8") as f:
            return f.read()


@app.get("/old", response_class=HTMLResponse)
async def old_interface():
    """Serve the old interface."""
    with open("index.html", encoding="utf-8") as f:
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


@app.post("/generate-image")
async def generate_image_endpoint(req: ImageGenerationRequest):
    """Generate an image from a text prompt using Gemini."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    try:
        result = await asyncio.to_thread(generate_image, req.prompt)
        
        if result.get('success'):
            return {
                "success": True,
                "image_data": result.get('image_data'),
                "prompt": result.get('prompt'),
                "source": result.get('source', 'gemini')
            }
        else:
            raise HTTPException(
                status_code=422,
                detail=result.get('error', 'Failed to generate image')
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-image-from-answer")
async def generate_image_from_answer_endpoint(req: ImageFromAnswerRequest):
    """Generate an optimized image prompt from research answer, then generate the image."""
    if not req.query.strip() or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Query and answer cannot be empty")
    
    try:
        # First, create an optimized prompt from the answer
        optimized_prompt = await asyncio.to_thread(
            create_image_prompt_from_answer, 
            req.query, 
            req.answer
        )
        
        # Then generate the image
        result = await asyncio.to_thread(generate_image, optimized_prompt)
        
        if result.get('success'):
            return {
                "success": True,
                "image_data": result.get('image_data'),
                "prompt": optimized_prompt,
                "source": result.get('source', 'gemini')
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to generate image')
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/publish-to-wordpress")
async def publish_to_wordpress_endpoint(req: PublishToWordPressRequest):
    """Publish current search result to WordPress as draft/publish."""
    if not req.query.strip() or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Query and answer are required")

    status = req.status.strip().lower()
    if status not in {"draft", "publish"}:
        raise HTTPException(status_code=400, detail="Status must be 'draft' or 'publish'")

    try:
        result = await asyncio.to_thread(
            publish_search_result,
            req.query,
            req.answer,
            req.sources,
            status,
            req.media_id,
            req.image_url,
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-image-to-wordpress")
async def upload_image_to_wordpress_endpoint(req: UploadImageToWordPressRequest):
    """Upload a base64 image directly to the WordPress media library."""
    if not req.image_data.strip():
        raise HTTPException(status_code=400, detail="image_data cannot be empty")

    try:
        result = await asyncio.to_thread(upload_image, req.image_data, req.title)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
