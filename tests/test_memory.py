"""Tests for the memory sync module."""

import pytest
from unittest.mock import AsyncMock, patch

from gateway.memory import embed_text, store_memory, sync_memory


class TestEmbedText:
    @pytest.mark.asyncio
    async def test_returns_zero_vector_without_api_key(self):
        """Without OPENAI_API_KEY, should return a zero vector."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            # Re-import to pick up env change
            from gateway import memory
            original = memory.OPENAI_API_KEY
            memory.OPENAI_API_KEY = ""
            try:
                result = await embed_text("test content")
                assert len(result) == 1536
                assert all(v == 0.0 for v in result)
            finally:
                memory.OPENAI_API_KEY = original


class TestStoreMemory:
    @pytest.mark.asyncio
    async def test_skips_without_supabase_config(self):
        """Without Supabase config, should skip and return status."""
        from gateway import memory
        original_url = memory.SUPABASE_URL
        original_key = memory.SUPABASE_SERVICE_KEY
        memory.SUPABASE_URL = ""
        memory.SUPABASE_SERVICE_KEY = ""
        try:
            result = await store_memory(
                "test_user", "test content", [0.0] * 1536
            )
            assert result["status"] == "skipped"
        finally:
            memory.SUPABASE_URL = original_url
            memory.SUPABASE_SERVICE_KEY = original_key


class TestSyncMemory:
    @pytest.mark.asyncio
    async def test_sync_handles_errors_gracefully(self):
        """sync_memory should not raise — errors are logged."""
        with patch("gateway.memory.embed_text", side_effect=Exception("API down")):
            # Should not raise
            await sync_memory("test_user", "test content")
