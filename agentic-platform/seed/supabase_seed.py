"""
Seed script for Supabase pgvector.

Creates the memories table and the vector similarity search function.
Run this once after creating your Supabase project.

Usage:
    python -m seed.supabase_seed
"""

from __future__ import annotations

import os
import sys

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


# ---------------------------------------------------------------------------
# SQL to run via Supabase's SQL editor API
# ---------------------------------------------------------------------------

SETUP_SQL = """
-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the memories table
CREATE TABLE IF NOT EXISTS memories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    content text NOT NULL,
    embedding vector(1536),
    created_at timestamptz DEFAULT now()
);

-- Index for fast user-scoped queries
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);

-- HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_memories_embedding
    ON memories USING hnsw (embedding vector_cosine_ops);

-- RPC function for vector similarity search scoped to a user
CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    match_user_id text,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    user_id text,
    content text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.user_id,
        m.content,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM memories m
    WHERE m.user_id = match_user_id
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""


def seed():
    """Run the setup SQL against Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        sys.exit(1)

    print(f"Setting up Supabase at {SUPABASE_URL}...")

    # Use the Supabase SQL endpoint
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        },
        json={"query": SETUP_SQL},
        timeout=30.0,
    )

    if resp.status_code == 404:
        # exec_sql RPC doesn't exist — need to run SQL via the dashboard
        print("\nThe exec_sql RPC function is not available.")
        print("Please run the following SQL in the Supabase SQL editor:\n")
        print("=" * 60)
        print(SETUP_SQL)
        print("=" * 60)
        print("\nYou can find the SQL editor at:")
        print(f"  {SUPABASE_URL.replace('.supabase.co', '')}/project/sql")
        return

    if resp.status_code >= 400:
        print(f"Error ({resp.status_code}): {resp.text}", file=sys.stderr)
        print("\nFallback: Run this SQL manually in the Supabase SQL editor:\n")
        print(SETUP_SQL)
        sys.exit(1)

    print("Done! Memories table and search function created.")

    # Verify by checking if the table exists
    verify = httpx.get(
        f"{SUPABASE_URL}/rest/v1/memories?select=count&limit=0",
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        },
    )
    if verify.status_code == 200:
        print("  Verified: memories table is accessible")
    else:
        print(f"  Warning: Could not verify table (status {verify.status_code})")


if __name__ == "__main__":
    seed()
