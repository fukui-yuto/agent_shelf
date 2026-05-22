# agent-shelf

Convention-over-configuration AI agent framework.

Place a directory under `agents/` and it becomes a specialized AI agent -- no config files needed.

## Quick Start

### Install

```bash
uv sync
```

### Setup

```bash
cp .env.example .env
# Edit .env with your API keys
```

### Create an Agent

```
agents/
└── my-agent/
    ├── knowledge/        # Documents for RAG (md, txt, html)
    ├── skills/           # Python scripts as tools
    └── prompts/          # System prompts
```

All subdirectories are optional. Even an empty directory is recognized as an agent.

### CLI Commands

```bash
# List detected agents
agent list

# Interactive chat
agent run my-agent

# Single query
agent query my-agent "How do I do X?"

# Re-index knowledge base
agent index my-agent

# List available skills
agent skills my-agent
```

## Configuration

All configuration is done via environment variables (or `.env` file):

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | LLM backend (`claude` / `ollama`) | `claude` |
| `LLM_MODEL` | Model name | `claude-sonnet-4-20250514` |
| `LLM_BASE_URL` | API base URL (for Ollama) | `http://localhost:11434` |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key (for embeddings) | - |
| `EMBEDDING_PROVIDER` | Embedding backend (`local` / `openai`) | `local` |

## Agent Directory Structure

### knowledge/

Place documents (`.md`, `.txt`, `.html`) here. They are automatically chunked, embedded, and indexed into ChromaDB for RAG retrieval.

### skills/

Python scripts with a frontmatter block defining the tool interface:

```python
# skills/get_status.py
# ---
# description: Get the status of a service
# parameters:
#   service_name: string - Name of the service
# ---

def run(service_name: str) -> dict:
    return {"status": "running"}
```

The framework registers these as LLM tools and calls `run()` when the LLM invokes them.

### prompts/

- `system.md` -- Main system prompt (falls back to a default if absent)
- `*.md` -- Additional context files, merged into the system prompt

## Architecture

```
Interface Layer (CLI)
        |
  Agent Router         -- auto-detects agents/ directories
        |
  Agent Runtime        -- orchestrates components below
   ├── RAG Engine      -- ChromaDB + embeddings
   ├── Skill Executor  -- dynamic Python skill loading
   ├── Prompt Manager  -- system prompt assembly
   └── LLM Adapter     -- Claude / Ollama
```

## Tech Stack

- Python 3.12+ / uv
- ChromaDB (vector store)
- sentence-transformers (local embeddings)
- Anthropic SDK / Ollama (LLM)
- Click + Rich (CLI)
