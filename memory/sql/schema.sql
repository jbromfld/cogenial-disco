-- 1. Enable the vector extension if not already done
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the memory table
CREATE TABLE agent_memory (
    id SERIAL PRIMARY KEY,
    -- The core concept summary (e.g., "Project Timeline")
    primary_abstraction TEXT NOT NULL, 
    -- Vector embedding of the primary_abstraction
    primary_embedding VECTOR(1536), 
    -- The detailed raw content/episodic information
    memory_value JSONB NOT NULL, 
    -- A list of semantic hooks: ["Jane", "hiking", "2026-07-05"]
    cue_anchors TEXT[] DEFAULT '{}', 
    -- Timestamp for temporal reasoning
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Index for fast similarity search (Vector)
CREATE INDEX idx_memory_embedding ON agent_memory USING hnsw (primary_embedding vector_cosine_ops);

-- 4. Index for fast keyword lookup on Cue Anchors (GIN)
CREATE INDEX idx_memory_cue_anchors ON agent_memory USING GIN (cue_anchors);

-- 5. Helper function to update the 'updated_at' column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agent_memory_updated_at
    BEFORE UPDATE ON agent_memory
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();