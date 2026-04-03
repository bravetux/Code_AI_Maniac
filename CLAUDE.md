# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AG-UC-1128** — AI Arena: a multi-agent code analysis platform with a Streamlit frontend and AWS Strands + Bedrock backend.

Key capabilities:
- Accept code from GitHub/Gitea repositories or local files
- Support specifying line ranges within a file or entire files (up to 50 files)
- Use Amazon Bedrock (Claude 3.5 Sonnet) via Strands Agents as the LLM backend
- 8 specialized agents: Bug Analysis, Code Design, Code Flow, Mermaid Diagrams, Requirements, Static Analysis, PR Comments, Commit Analysis
- DuckDB local storage for jobs, cache, chunks, history, and presets

## Tech Stack

Python 3.11+, Streamlit, AWS Strands Agents, Amazon Bedrock, DuckDB, PyGithub, httpx, flake8, pytest

## Commands

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the app
```bash
streamlit run app/Home.py
```

### Run all tests
```bash
pytest
```

### Run a single test file
```bash
pytest tests/agents/test_bug_analysis.py -v
```

### Run a single test
```bash
pytest tests/db/test_queries.py::test_cache_store_and_hit -v
```

### Start Gitea (Docker)
```bash
cd docker && docker compose up -d
```

## Architecture

```
Streamlit Frontend (app/)
      ↓ job request
OrchestratorAgent (agents/orchestrator.py)
  ├── Routes and parallelizes sub-agent calls
  └── Aggregates results back to Streamlit
       ↕
  Sub-Agents (agents/):
  bug_analysis | code_design | code_flow | mermaid
  requirement  | static_analysis | comment_generator | commit_analysis
       ↕
  Shared Tool Layer (tools/):
  fetch_local | fetch_github | fetch_gitea | chunk_file | run_linter | cache
       ↕
  DuckDB (data/arena.db)
       ↕
  Amazon Bedrock (Claude via Strands)
```

## Running Gitea (Self-Hosted Git)

```bash
cd docker && docker compose up -d
```

- Web UI: http://localhost:3000
- First visit: complete the installation wizard (leave defaults)
- Create an account → Settings → Applications → Generate API token
- Paste token into `.env` as `GITEA_TOKEN=...`
- Set `GITEA_URL=http://localhost:3000`

## Environment Setup

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required for AWS Bedrock:
- `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `BEDROCK_MODEL_ID` (default: `anthropic.claude-3-5-sonnet-20241022-v2:0`)

Optional:
- `GITHUB_TOKEN` — for GitHub file fetching
- `GITEA_URL` + `GITEA_TOKEN` — for Gitea integration
- `DB_PATH` — DuckDB file location (default: `data/arena.db`)
