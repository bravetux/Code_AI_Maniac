# Project Overview

**AI Code Maniac** — a multi-agent code analysis platform with a Streamlit frontend and AWS Strands + Bedrock backend.

Key capabilities:
- Accept code from GitHub/Gitea repositories or local files
- Support specifying line ranges within a file or entire files (up to 50 files)
- Use Amazon Bedrock via Strands Agents as the LLM backend
- 37 specialized agents across code analysis, test generation, traceability, commit analysis, and security (latest phase shipped: **Phase 6 Wave 6A**)
  - **Code Analysis (Phase 1):** Bug Analysis, Static Analysis, Code Flow, Requirements, Dependency Analysis, Code Complexity, Test Coverage, Duplication Detection, Performance Analysis, Type Safety, Architecture Mapper, License Compliance, Change Impact, Doxygen Docs, C Test Generator
  - **Code Analysis (Phase 2):** Code Design, Mermaid Diagrams, Refactoring Advisor, API Doc Generator, PR Comments
  - **Security (Phase 3-4):** Secret Scan, Threat Model
  - **Phase 5 — Quick wins (7 agents):** Unit Test Generator (F1), Story-to-TestCase (F2), BDD/Gherkin (F3), Test Data Generator (F8), Dead Code Detector (F17), API Contract Checker (F24), OpenAPI Generator (F37) — plus CLI/server tools for F20 (CI/CD webhook) and F21 (pre-commit reviewer)
  - **Phase 6 Wave 6A (3 agents):** API Test Generator (F5), Perf/Load Test Generator (F6), Traceability Matrix (F10)
  - **Commit Analysis:** Commit Analysis, Release Notes, Developer Activity, Commit Hygiene, Churn Analysis
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
  Sub-Agents (agents/) — 37 total:
  Phase 1: bug_analysis | static_analysis | code_flow | requirement
           dependency_analysis | code_complexity | test_coverage
           duplication_detection | performance_analysis | type_safety
           architecture_mapper | license_compliance | change_impact
           doxygen | c_test_generator
  Phase 2: code_design | mermaid | refactoring_advisor | api_doc_generator
  Phase 3: comment_generator | secret_scan
  Phase 4: threat_model
  Phase 5 (Quick wins): unit_test_generator | story_test_generator
           gherkin_generator | test_data_generator | dead_code_detector
           api_contract_checker | openapi_generator
  Phase 6 Wave 6A: api_test_generator | perf_test_generator | traceability_matrix
  Commit:  commit_analysis | release_notes | developer_activity
           commit_hygiene | churn_analysis
       ↕
  Shared Tool Layer (tools/):
  fetch_local | fetch_github | fetch_gitea | chunk_file | run_linter
  cache | run_doxygen | web_scraper
  Phase 5 tools:  openapi_parser | spec_fetcher
                  precommit_reviewer (F21) | webhook_server (F20)
  Wave 6A tools:  postman_emitter | load_profile_builder | test_scanner
       ↕
  DuckDB (data/arena.db)
       ↕
  Amazon Bedrock (via Strands Agents)
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
- `BEDROCK_MODEL_ID` (default: `anthropic.claude-3-5-sonnet-20241022-v2:0` or any supported model)

Optional:
- `GITHUB_TOKEN` — for GitHub file fetching
- `GITEA_URL` + `GITEA_TOKEN` — for Gitea integration
- `DB_PATH` — DuckDB file location (default: `data/arena.db`)
