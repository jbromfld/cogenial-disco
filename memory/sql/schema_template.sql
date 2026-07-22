-- Parameterized schema — rendered by memory/migrate.py.
-- {embedding_dim} is substituted with the EMBEDDING_DIM value from .env.
-- Do not execute this file directly with psql.

-- 1. Enable the vector extension if not already done
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the memory table
CREATE TABLE IF NOT EXISTS agent_memory (
    id SERIAL PRIMARY KEY,
    primary_abstraction TEXT NOT NULL,
    primary_embedding VECTOR({embedding_dim}),
    memory_value JSONB NOT NULL,
    cue_anchors TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Index for fast similarity search (HNSW, cosine)
CREATE INDEX IF NOT EXISTS idx_memory_embedding
    ON agent_memory USING hnsw (primary_embedding vector_cosine_ops);

-- 4. Index for fast keyword lookup on cue anchors (GIN)
CREATE INDEX IF NOT EXISTS idx_memory_cue_anchors
    ON agent_memory USING GIN (cue_anchors);

-- 5. Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_agent_memory_updated_at'
    ) THEN
        CREATE TRIGGER update_agent_memory_updated_at
            BEFORE UPDATE ON agent_memory
            FOR EACH ROW
            EXECUTE PROCEDURE update_updated_at_column();
    END IF;
END;
$$;
