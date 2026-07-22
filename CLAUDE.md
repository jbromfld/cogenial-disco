# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **CI/CD Agentic Memory Remediation System** — a Python framework that intercepts CI/CD pipeline failures, retrieves past solutions from a pgvector memory store, attempts automated remediation, and consolidates new solutions into long-term memory via a dual-LLM validation pattern.

The project is in early prototype stage. No build toolchain (package.json, requirements.txt, Makefile) exists yet; infrastructure must be set up manually per the steps below.

## Database Setup

The only setup step currently defined is initializing the PostgreSQL schema:

```bash
# Requires PostgreSQL with pgvector extension
psql -d <your_db> -f memory/sql/schema.sql
```

The schema creates the `agent_memory` table with a 1536-dimensional HNSW vector index (cosine ops) and a GIN index on the `cue_anchors` text array.

## Architecture

### Core Design Patterns

**MEMORA** — the memory schema pattern mapping four fields to every stored memory:
- `primary_abstraction`: Generalized concept label (e.g., `"NPM Dependency Conflict"`)
- `primary_embedding`: 1536-dim OpenAI vector of that label
- `memory_value`: JSONB blob of concrete remediation steps
- `cue_anchors`: String array of semantic tags for fast GIN filtering (e.g., `["repo:frontend", "stage:build", "error:ERESOLVE"]`)

**CaMeL** — dual-LLM separation of concerns:
- **P-Agent** (LangChain ReAct): Orchestrates the full flow — receives webhook, searches memory, applies/devises fix, commits result
- **Q-Agent** (LangChain `with_structured_output`): Sandboxed judge that compares proposed memory against retrieved memory and returns `{"action": "INSERT"|"UPDATE", "merged_content": "..."}`

### LangGraph Execution Flow

```
CI/CD Webhook → Error Ingestion (P-Agent)
    → pgvector similarity search (threshold: cosine distance < 0.20)
    → Remediation attempt (apply known fix OR devise new fix)
    → Q-Agent validation (INSERT vs. UPDATE decision)
    → Memory commit to PostgreSQL
```

### Memory Upsert Logic (`memory/tool.py`)

`upsert_agent_memory()` is the core MCP tool. It:
1. Queries `agent_memory` ordered by cosine distance, limit 1
2. If `distance < 0.20` (≥ 0.80 similarity): merges JSONB dicts and deduplicates cue anchors, then UPDATEs
3. Otherwise: INSERTs a new row

The LLM merge logic is a placeholder (`{**existing, **new}`) — the real implementation should call the Q-Agent here.

### Feedback Loop (Closing the Memory Loop)

Memory is only committed after a successful merge, not at fix-proposal time:
1. P-Agent generates a UUID correlation ID when proposing a fix
2. Branch is named `agent-remediation/fix-{uuid}`
3. Agent state is persisted (LangGraph SQLite checkpointer or JSON file)
4. On successful CI run post-merge, webhook payload's commit message is scanned for the UUID
5. UUID matches pending state → Q-Agent finalizes and P-Agent commits memory

### Local Simulation Approach

Per `ARCHITECTURE.md`, the intended local test harness (not yet built):
- `mock_ci.py`: Reads a dummy codebase file; fails on a sentinel string, passes otherwise; writes to `error.log` / `success.log`
- `agent_flow.py`: LangGraph app watching `error.log`; outputs a `.patch` file instead of pushing a PR
- Human reviewer applies patch with `patch < fix-{uuid}.patch`, reruns `mock_ci.py`
- `success.log` contains the UUID → agent wakes up and completes memory commit
