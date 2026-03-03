"""
Memory Middleware — async conversation memory sync.

After every MCP exchange, fires a background task to:
  1. Compose a text summary of the exchange
  2. Generate an embedding via OpenAI
  3. Write to Supabase pgvector (user-namespaced)
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


class MemoryMiddleware:
    """Handles async memory sync: embed + store in pgvector."""

    def __init__(self):
        self._openai_client: httpx.AsyncClient | None = None
        self._supabase_client: httpx.AsyncClient | None = None

    async def initialize(self):
        """Create HTTP clients for OpenAI and Supabase."""
        if OPENAI_API_KEY:
            self._openai_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            )
        else:
            logger.warning("OPENAI_API_KEY not set — memory embedding disabled")

        if SUPABASE_URL and SUPABASE_KEY:
            self._supabase_client = httpx.AsyncClient(
                base_url=SUPABASE_URL,
                timeout=30.0,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
            )
        else:
            logger.warning("SUPABASE_URL/SUPABASE_SERVICE_KEY not set — memory storage disabled")

    async def shutdown(self):
        if self._openai_client:
            await self._openai_client.aclose()
        if self._supabase_client:
            await self._supabase_client.aclose()

    async def sync_exchange(
        self,
        user_id: str,
        server_name: str,
        action: str,
        request_body: dict,
        response_body: dict,
    ):
        """
        Background task: embed the exchange and store in pgvector.

        Called via FastAPI BackgroundTasks — runs after response is sent.
        """
        try:
            content = self._compose_content(server_name, action, request_body, response_body)
            embedding = await self._embed(content)
            if embedding:
                await self._store(user_id, content, embedding)
                logger.info("Memory synced for user %s (server=%s, action=%s)", user_id, server_name, action)
        except Exception:
            logger.exception("Memory sync failed for user %s", user_id)

    def _compose_content(
        self,
        server_name: str,
        action: str,
        request_body: dict,
        response_body: dict,
    ) -> str:
        """Compose a text summary of the exchange for embedding."""
        # Strip internal fields
        clean_request = {k: v for k, v in request_body.items() if not k.startswith("_")}
        return (
            f"[{server_name}/{action}] "
            f"Request: {json.dumps(clean_request, default=str)[:500]} | "
            f"Response: {json.dumps(response_body, default=str)[:500]}"
        )

    async def _embed(self, text: str) -> list[float] | None:
        """Generate embedding via OpenAI API."""
        if not self._openai_client:
            return None

        resp = await self._openai_client.post(
            OPENAI_EMBED_URL,
            json={"input": text, "model": OPENAI_EMBED_MODEL},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]

    async def _store(self, user_id: str, content: str, embedding: list[float], memory_id: str | None = None):
        """Write memory row to Supabase pgvector."""
        if not self._supabase_client:
            return

        row = {
            "id": memory_id or str(uuid.uuid4()),
            "user_id": user_id,
            "content": content,
            "embedding": embedding,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        resp = await self._supabase_client.post(
            "/rest/v1/memories",
            json=row,
        )
        resp.raise_for_status()

    async def store(self, user_id: str, content: str) -> dict | None:
        """
        Explicitly store a memory (agent-callable).

        Unlike sync_exchange which fires implicitly, this lets the agent
        choose to remember something: "my name is Heisenberg".
        """
        try:
            embedding = await self._embed(content)
            if embedding:
                memory_id = str(uuid.uuid4())
                await self._store(user_id, content, embedding, memory_id=memory_id)
                logger.info("Explicit memory stored for user %s", user_id)
                return {"id": memory_id, "content": content}
        except Exception:
            logger.exception("Explicit memory store failed for user %s", user_id)
        return None

    async def delete(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory by ID (scoped to user)."""
        if not self._supabase_client:
            return False

        try:
            resp = await self._supabase_client.delete(
                "/rest/v1/memories",
                params={"id": f"eq.{memory_id}", "user_id": f"eq.{user_id}"},
            )
            resp.raise_for_status()
            logger.info("Memory %s deleted for user %s", memory_id, user_id)
            return True
        except Exception:
            logger.exception("Memory delete failed for user %s", user_id)
            return False

    async def list_memories(self, user_id: str, limit: int = 50) -> list[dict]:
        """List recent memories for a user (for admin UI)."""
        if not self._supabase_client:
            return []

        try:
            resp = await self._supabase_client.get(
                "/rest/v1/memories",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "id,user_id,content,created_at",
                    "order": "created_at.desc",
                    "limit": str(limit),
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception("Memory list failed for user %s", user_id)
            return []

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search user's memories by semantic similarity.

        Uses Supabase RPC to call a pgvector similarity function.
        """
        if not self._openai_client or not self._supabase_client:
            return []

        embedding = await self._embed(query)
        if not embedding:
            return []

        # Call Supabase RPC function for cosine similarity search
        resp = await self._supabase_client.post(
            "/rest/v1/rpc/search_memories",
            json={
                "query_embedding": embedding,
                "match_user_id": user_id,
                "match_count": limit,
            },
        )
        resp.raise_for_status()
        return resp.json()
