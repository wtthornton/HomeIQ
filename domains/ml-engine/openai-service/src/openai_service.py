"""
OpenAI Service - Thin wrapper for OpenAI API used by AI Core Service.
Exposes /health and /chat/completions for suggestion generation.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan: no heavy startup required."""
    yield


app = FastAPI(title="OpenAI Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check for docker-compose and ai-core-service."""
    return {"status": "ok"}


@app.post("/chat/completions")
async def chat_completions(body: dict):
    """
    Chat completions endpoint expected by ai-core-service.
    If OPENAI_API_KEY is set, proxies to OpenAI; otherwise returns a stub response.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import httpx
            prompt = body.get("prompt", "")
            model = body.get("model", "gpt-4o-mini")
            temperature = body.get("temperature", 0.7)
            max_tokens = body.get("max_tokens", 500)
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                r.raise_for_status()
                data = r.json()
                content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "[]")
                return {"response": content}
        except Exception as e:
            logger.warning("OpenAI API call failed: %s", e)
    # Stub: return empty suggestions list so ai-core fallback path works
    return {"response": "[]"}
