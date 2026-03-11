"""
Image Generation Module - Using Google Gemini API
Generates images based on text prompts
"""

import os
import base64
from typing import Optional
import google.genai as genai
from google.genai import types


def _get_client():
    """Create a Gemini client from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    return genai.Client(api_key=api_key)


def _get_image_model():
    """Get image generation model from env, defaulting to the correct model."""
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-image-preview")


def _make_visual_prompt(user_prompt: str) -> str:
    """Convert any question or sentence into a rich visual image generation prompt."""
    # If it already looks like a visual description, use it as-is
    visual_keywords = ["photo", "image", "picture", "painting", "illustration",
                       "digital art", "render", "drawing", "showing", "depicting"]
    if any(kw in user_prompt.lower() for kw in visual_keywords):
        return user_prompt

    # Wrap question/topic into an explicit image prompt
    return (
        f"Create a rich, detailed, visually compelling illustration or digital art "
        f"that represents the topic: \"{user_prompt}\". "
        f"The image should visually explain or depict the core concept in an "
        f"informative and engaging way."
    )


def generate_image(prompt: str) -> dict:
    """
    Generate an image using Gemini's image generation model.

    Args:
        prompt: Text description or topic/question to visualise

    Returns:
        Dictionary with 'success', 'image_data', and optional 'error'
    """
    try:
        client = _get_client()
        model = _get_image_model()

        visual_prompt = _make_visual_prompt(prompt)
        print(f"🎨 Generating image for prompt: '{visual_prompt}' using {model}")

        response = client.models.generate_content(
            model=model,
            contents=visual_prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are an AI image generator. "
                    "Always produce an image that visually represents the given topic or concept. "
                    "Never respond with text only — always output an image."
                ),
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                mime_type = part.inline_data.mime_type or "image/jpeg"
                image_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                print(f"  ✅ Image generated (size: {len(image_data)} bytes)")
                return {
                    "success": True,
                    "image_data": f"data:{mime_type};base64,{image_data}",
                    "prompt": prompt,          # return original user prompt
                    "visual_prompt": visual_prompt,
                    "source": "gemini",
                }

        # Model returned only text — visible in logs for debugging
        text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, "text") and p.text]
        print(f"  ⚠️  Model returned text only: {' '.join(text_parts)[:200]}")
        return {
            "success": False,
            "error": "The model did not return an image for this prompt. Try rephrasing as a visual description."
        }

    except Exception as e:
        print(f"  ❌ Error generating image: {str(e)}")
        return {"success": False, "error": str(e)}


def create_image_prompt_from_answer(query: str, answer: str) -> str:
    """
    Create an optimized image generation prompt from the research answer.

    Args:
        query: Original user query
        answer: The AI-generated answer/research

    Returns:
        Optimized image generation prompt
    """
    try:
        client = _get_client()

        prompt = f"""Given this research query and answer, create a CONCISE image generation prompt (max 100 words).

Query: {query}

Answer excerpt: {answer[:500]}

Create a visual prompt that captures the essence of the topic. Be specific and descriptive.
Return ONLY the prompt, nothing else."""

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
        )
        image_prompt = response.text.strip()

        print(f"  📝 Created image prompt: {image_prompt}")
        return image_prompt

    except Exception as e:
        print(f"  ⚠️  Failed to create optimized prompt: {e}")
        return query[:100]
