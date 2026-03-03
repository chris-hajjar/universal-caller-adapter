"""
Memory sync — fires after every exchange to embed and store
conversation content in Supabase pgvector.

This runs as a FastAPI BackgroundTask so it never blocks the
response to the client. The user doesn't know it's happening.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_TABLE = "memories"


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

async def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for the given text using OpenAI's API.

    Returns a 1536-dimensional float vector.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning zero vector")
        return [0.0] * EMBEDDING_DIMENSIONS

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_EMBEDDING_MODEL,
                "input": text,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

async def store_memory(
    user_id: str,
    content: str,
    embedding: list[float],
) -> dict[str, Any]:
    """
    Write a memory record to Supabase pgvector.

    Each record is namespaced by user_id so users only see their own
    memories when searching.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning("Supabase not configured — skipping memory store")
        return {"status": "skipped", "reason": "supabase_not_configured"}

    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "content": content,
        "embedding": json.dumps(embedding),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=record,
            timeout=15.0,
        )
        resp.raise_for_status()
        logger.info(f"Stored memory for {user_id}: {content[:80]}...")
        return {"status": "stored", "id": record["id"]}


async def search_memories(
    user_id: str,
    query_embedding: list[float],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Search memories for a user by cosine similarity.

    Uses Supabase's pgvector RPC function for vector similarity search,
    scoped to the user's own memories.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/search_memories",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "query_embedding": json.dumps(query_embedding),
                "match_user_id": user_id,
                "match_count": limit,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Background task entry point
# ---------------------------------------------------------------------------

async def sync_memory(user_id: str, content: str) -> None:
    """
    Background task: embed conversation content and store in pgvector.

    Called by FastAPI's BackgroundTasks after every exchange. Failures
    are logged but never bubble up to the client.
    """
    try:
        logger.info(f"Syncing memory for {user_id}")
        embedding = await embed_text(content)
        await store_memory(user_id, content, embedding)
    except Exception:
        logger.exception(f"Failed to sync memory for {user_id}")
