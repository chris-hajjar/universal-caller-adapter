-- Supabase pgvector setup for conversation memory
-- Run this in the Supabase SQL Editor

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Memories table — stores embedded conversation exchanges per user
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    content TEXT,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast user-scoped queries
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories (user_id);

-- Index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- RPC function for cosine similarity search (called by the memory middleware)
CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    match_user_id TEXT,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    user_id TEXT,
    content TEXT,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.user_id,
        m.content,
        1 - (m.embedding <=> query_embedding) AS similarity,
        m.created_at
    FROM memories m
    WHERE m.user_id = match_user_id
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Row Level Security (optional but recommended)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Policy: service role can do everything (used by the gateway)
CREATE POLICY "Service role full access"
    ON memories
    FOR ALL
    USING (true)
    WITH CHECK (true);
