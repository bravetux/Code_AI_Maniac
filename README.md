# AI Code Maniac — Multi-Agent Code Analysis Platform

**Using: AWS Bedrock (Claude) · Strands Agents · Streamlit · DuckDB**

AI Code Maniac orchestrates **27 specialized AI agents** in a coordinated 4-phase pipeline to perform deep code analysis. Submit code from GitHub, Gitea, or local files and receive concurrent results across bug detection, complexity metrics, performance analysis, design review, refactoring advice, API documentation, security scanning, and more. A dedicated Commits page offers 5 analysis modes including release notes generation, developer activity stats, and churn analysis.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Agent Execution Flow](#agent-execution-flow)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Agent Gating](#agent-gating)
- [Using the UI](#using-the-ui)
- [Running Tests](#running-tests)
- [Self-Hosted Gitea](#self-hosted-gitea)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)

---

## Features

**27 specialized AI agents** organized into 7 functional categories:

### Code Quality & Metrics

| Agent Key | Agent | What It Produces |
|---|---|---|
| `bug_analysis` | Bug Analysis | Bugs with severity, root cause, runtime impact, and concrete fix suggestions |
| `static_analysis` | Static Analysis | Two-layer: flake8/ESLint linting + LLM semantic analysis (design smells, security anti-patterns, performance issues) |
| `code_complexity` | Code Complexity | Cyclomatic/cognitive complexity, maintainability index, per-function breakdown, hotspot identification |
| `duplication_detection` | Duplication Detection | Exact/near-duplicate code blocks, DRY violations, extraction suggestions with before/after code |
| `type_safety` | Type Safety | Type hint coverage, missing annotations, type issues, advanced typing suggestions |

### Code Understanding

| Agent Key | Agent | What It Produces |
|---|---|---|
| `code_flow` | Code Flow | Technical wiki-style execution-flow narrative for new team members |
| `requirement` | Requirement Analysis | Reverse-engineered functional & non-functional requirements in REQ-NNN format |
| `code_design` | Code Design | 3-turn principal-architect design review: understand → structured JSON → 9-section document |
| `architecture_mapper` | Architecture Mapper | Dependency map, import analysis, layer violations, coupling metrics, Mermaid component diagram |
| `mermaid` | Mermaid Diagrams | Flowchart, sequence, or class diagram as valid Mermaid syntax |
| `doxygen` | Doxygen Docs | Adds Doxygen comment headers to C/C++ functions, saves annotated source, generates HTML docs via Doxygen CLI |

### Performance & Optimization

| Agent Key | Agent | What It Produces |
|---|---|---|
| `performance_analysis` | Performance Analysis | Big-O analysis, memory patterns, N+1 queries, caching opportunities, scalability assessment |
| `refactoring_advisor` | Refactoring Advisor | Code smell inventory, Fowler-style refactoring suggestions with before/after code |

### Testing & Maintenance

| Agent Key | Agent | What It Produces |
|---|---|---|
| `test_coverage` | Test Coverage | Identifies untested functions, missing edge cases, suggests test cases and test skeletons |
| `c_test_generator` | C Test Generator | Generates Python pytest + ctypes test files for C code with type-safe bindings, saved to Reports/ |
| `change_impact` | Change Impact | Blast radius estimation, public API surface, change scenarios, side effect mapping |

### Security & Compliance

| Agent Key | Agent | What It Produces |
|---|---|---|
| `secret_scan` | Secret Scan | Phase 0 regex pre-flight + Phase 3 LLM deep scan for hardcoded secrets |
| `dependency_analysis` | Dependency Analysis | SCA: parses 20+ dependency file types, CVE lookup, risk assessment |
| `threat_model` | Threat Model | STRIDE formal analysis or attacker-narrative penetration test |
| `license_compliance` | License Compliance | License detection, compatibility matrix, copyleft obligations, attribution requirements |

### Documentation & Review

| Agent Key | Agent | What It Produces |
|---|---|---|
| `api_doc_generator` | API Doc Generator | Full API documentation: classes, functions, usage examples, error handling |
| `comment_generator` | PR Comments | GitHub-style review comments generated from bug + static findings |

### Commit Analysis (5 modes)

| Agent Key | Mode | What It Produces |
|---|---|---|
| `commit_analysis` | Commit Analysis | Release readiness, risk-level score, and changelog from git commit history |
| `release_notes` | Release Notes | Polished user-facing release notes grouped by features, fixes, improvements, breaking changes |
| `developer_activity` | Developer Activity | Contributor stats, activity timeline, collaboration patterns, bus-factor risks |
| `commit_hygiene` | Commit Hygiene | Conventional Commits compliance audit, message quality, squash candidates |
| `churn_analysis` | Churn Analysis | File hotspot detection, co-change patterns, stability report (clone source only) |

### Platform-Level Capabilities

- Multi-file and recursive-folder analysis (up to 50 files per job)
- Line-range targeting within a single file
- Composite result caching — same file + feature + language + prompt always hits cache, skipping Bedrock
- Named sidebar settings profiles — save/load/delete full analysis configurations across sessions
- Custom prompt overrides and per-feature prompt presets
- 13 enhanced prompt template categories (Deep Analysis, Security Focused, Performance, Compliance, etc.)
- JSON + Markdown export for every result tab
- Per-file and consolidated report generation (Markdown + HTML)
- Web scraper tool — extract clean text from any URL for analysis (`tools/web_scraper.py`)
- DuckDB-backed local storage for jobs, cache, history, presets, and profiles

---

## Architecture Overview

```mermaid
graph TD
    UI["Streamlit Frontend\n(app/)"]
    ORC["Orchestrator\nagents/orchestrator.py"]
    P0["Phase 0 — Pre-flight\nsecret_scanner (regex)"]
    P1["Phase 1 — Foundation (15 agents, parallel)\nbug · static · code_flow · requirement · dependency\ncomplexity · test_coverage · duplication · performance\ntype_safety · architecture · license · change_impact\ndoxygen · c_test_generator"]
    P2["Phase 2 — Context-Aware (4 agents)\ncode_design · mermaid\nrefactoring_advisor · api_doc_generator"]
    P3["Phase 3 — Synthesis\ncomment_generator · secret_scan"]
    P4["Phase 4 — Threat Model\nthreat_model"]
    COMMIT["Commit Agents (5 modes)\ncommit_analysis · release_notes\ndeveloper_activity · commit_hygiene · churn_analysis"]
    CACHE["Cache Layer\ntools/cache.py"]
    DB["DuckDB\ndata/arena.db"]
    BEDROCK["AWS Bedrock\nClaude via Strands"]
    SRC_LOCAL["Local Files"]
    SRC_GH["GitHub"]
    SRC_GT["Gitea"]

    UI -->|"job_id + config"| ORC
    SRC_LOCAL --> ORC
    SRC_GH --> ORC
    SRC_GT --> ORC
    ORC --> P0
    P0 --> P1
    P1 -->|"results context"| P2
    P2 --> P3
    P3 --> P4
    UI -->|"commit history"| COMMIT
    P1 & P2 & P3 & P4 & COMMIT --> CACHE
    CACHE --> DB
    P1 & P2 & P3 & P4 & COMMIT <-->|"Agent calls"| BEDROCK
    ORC -->|"save results"| DB
    DB -->|"poll + load"| UI
```

---

## Agent Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant ORC as Orchestrator
    participant DB as DuckDB
    participant P0 as Phase 0 Pre-flight
    participant P1 as Phase 1 (15 agents)
    participant P2 as Phase 2 (4 agents)
    participant P3 as Phase 3 Synthesis
    participant P4 as Phase 4 Threat Model
    participant LLM as AWS Bedrock

    User->>UI: Configure source + features, click Run
    UI->>DB: create_job() → job_id (status=pending)
    UI->>ORC: spawn background thread
    UI-->>User: Show progress indicator (polls every 2s)

    ORC->>DB: update_job_status(running)
    ORC->>ORC: _fetch_files() — local / GitHub / Gitea

    ORC->>P0: secret_scanner regex pre-flight
    P0-->>ORC: redact / block / pass

    ORC->>P1: bug · static · code_flow · requirement · dependency<br/>complexity · test_coverage · duplication · performance<br/>type_safety · architecture · license · change_impact<br/>doxygen · c_test_generator

    loop For each selected Phase 1 feature
        P1->>DB: check_cache(file_hash, feature)
        alt Cache hit
            DB-->>P1: cached result
        else Cache miss
            P1->>LLM: Agent call(s) — chunked if large
            LLM-->>P1: analysis result
            P1->>DB: write_cache + add_history
        end
    end

    P1-->>ORC: Phase 1 results

    ORC->>P2: code_design(bug, static)<br/>mermaid(flow) · refactoring(complexity, static, duplication)<br/>api_doc(flow)

    Note over P2,LLM: code_design uses 3 turns:<br/>understand → JSON → document

    P2->>DB: write_cache + add_history
    P2-->>ORC: Phase 2 results

    ORC->>P3: comment_generator(bug, static)<br/>secret_scan(phase0, static)
    P3->>DB: write_cache + add_history
    P3-->>ORC: Phase 3 results

    ORC->>P4: threat_model(bug, static, secret, dependency)
    P4->>DB: write_cache + add_history
    P4-->>ORC: Phase 4 results

    ORC->>DB: save_job_results(all_results)
    ORC->>DB: update_job_status(completed)

    UI->>DB: get_job_results(job_id)
    DB-->>UI: results dict
    UI-->>User: Render tabbed results + download buttons
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| AWS account with Bedrock access | — |
| Claude model enabled in Bedrock | `anthropic.claude-3-5-sonnet-20241022-v2:0` (default) |
| Docker (optional, for Gitea) | 20+ |

---

## Quick Start

### Windows (one-click)

```bat
startup.bat
```

The script activates the virtual environment, installs dependencies, kills stale Streamlit processes, and opens the app at `http://localhost:8501`.

### Linux / macOS

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
streamlit run app/Home.py
```

---

## Environment Variables

Copy `.env.example` to `.env`.

### Required — AWS Bedrock

| Variable | Default | Description |
|---|---|---|
| `AWS_REGION` | `us-east-1` | AWS region where Bedrock is enabled |
| `AWS_ACCESS_KEY_ID` | — | IAM access key ID |
| `AWS_SECRET_ACCESS_KEY` | — | IAM secret access key |
| `AWS_SESSION_TOKEN` | — | Optional; required for temporary / assumed-role credentials |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Claude model ID |
| `BEDROCK_TEMPERATURE` | `0.3` | Sampling temperature (0.0 – 1.0) |

### Optional — Integrations

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | — | Personal access token for private GitHub repos |
| `GITEA_URL` | `http://localhost:3000` | Base URL of your Gitea instance |
| `GITEA_TOKEN` | — | Gitea API token |

### Optional — App Settings

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `data/arena.db` | DuckDB file path |
| `MAX_FILES` | `50` | Max files per job (1 – 100) |
| `ENABLED_AGENTS` | `all` | Comma-separated agent keys; see [Agent Gating](#agent-gating) |

---

## Agent Gating

`ENABLED_AGENTS` controls which agents are available without touching code. Disabled agents are hidden from the UI and never invoked by the orchestrator.

```bash
# Full suite (default)
ENABLED_AGENTS=all

# Bug-finder profile
ENABLED_AGENTS=bug_analysis,static_analysis,comment_generator

# Design-review profile
ENABLED_AGENTS=code_design,requirement,code_flow,mermaid,architecture_mapper

# Quality & metrics profile
ENABLED_AGENTS=code_complexity,duplication_detection,performance_analysis,type_safety,refactoring_advisor

# Security-only profile
ENABLED_AGENTS=secret_scan,dependency_analysis,threat_model,license_compliance

# Commit-reviewer only
ENABLED_AGENTS=commit_analysis,release_notes,developer_activity,commit_hygiene,churn_analysis
```

Unknown keys are silently dropped.

---

## Using the UI

### Pages

| Page | Purpose |
|---|---|
| **Home** | Dashboard — recent jobs and quick stats |
| **Analysis** | Run a new analysis job |
| **History** | Browse past analyses with filter by feature and language |
| **Commits** | 5 commit analysis modes: Commit Analysis, Release Notes, Developer Activity, Commit Hygiene, Churn Analysis |
| **Presets** | Manage custom prompt presets |
| **Settings** | View config, adjust temperature, export/import database |

### Run a New Analysis

1. Go to **Analysis**.
2. In the sidebar, select a **source**:
   - **Local File** — upload files, enter a path, or scan a folder recursively.
   - **GitHub** — `owner/repo`, branch, file path.
   - **Gitea** — Gitea URL, `owner/repo`, branch, file path.
3. Optionally set a **line range** (start / end line).
4. Select one or more **agents** from the feature checkboxes.
5. Optionally set a **language** (auto-detected if blank) and **Mermaid type**.
6. Click **Run Analysis**. Results appear in tabs once the job completes.
7. Download any result as **JSON** or **Markdown** from the result tabs.

### Settings Profiles

Save the full sidebar configuration (source type, features, language, custom prompt, Mermaid type) as a named profile. Profiles persist across sessions in DuckDB.

### Prompt Presets

Override an agent's system prompt or append extra instructions for a single run from the **Advanced** expander. Save frequently used overrides as named presets.

---

## Running Tests

```bash
# Full suite
pytest

# Single file
pytest tests/agents/test_code_design.py -v

# Single test
pytest tests/db/test_queries.py::test_cache_store_and_hit -v
```

---

## Self-Hosted Gitea

```bash
cd docker && docker compose up -d
```

- Web UI: `http://localhost:3000`
- Complete the setup wizard on first visit.
- Create an account → **Settings → Applications → Generate API token**.
- Add to `.env`: `GITEA_TOKEN=<token>` and `GITEA_URL=http://localhost:3000`.

---

## Database Schema

```mermaid
erDiagram
    jobs {
        VARCHAR id PK
        VARCHAR status
        VARCHAR source_type
        VARCHAR source_ref
        VARCHAR language
        VARCHAR[] features
        TEXT custom_prompt
        JSON result_json
        TIMESTAMP created_at
        TIMESTAMP completed_at
    }
    results_cache {
        VARCHAR id PK
        VARCHAR job_id FK
        VARCHAR feature
        VARCHAR file_hash
        VARCHAR language
        JSON result_json
        TIMESTAMP created_at
    }
    file_chunks {
        VARCHAR id PK
        VARCHAR job_id FK
        VARCHAR file_path
        INTEGER chunk_index
        INTEGER start_line
        INTEGER end_line
        TEXT content
        INTEGER token_count
    }
    analysis_history {
        VARCHAR id PK
        VARCHAR job_id FK
        VARCHAR feature
        VARCHAR source_ref
        VARCHAR language
        TEXT summary
        TIMESTAMP created_at
    }
    repo_metadata {
        VARCHAR id PK
        VARCHAR source_type
        VARCHAR repo_url
        VARCHAR branch
        TIMESTAMP last_synced
        INTEGER commit_count
        JSON file_tree
    }
    commit_snapshots {
        VARCHAR id PK
        VARCHAR repo_id FK
        VARCHAR commit_sha
        VARCHAR author
        TEXT message
        TEXT diff_summary
        VARCHAR[] files_changed
        TIMESTAMP created_at
    }
    prompt_presets {
        VARCHAR id PK
        VARCHAR name
        VARCHAR feature
        TEXT system_prompt
        TEXT extra_instructions
        TIMESTAMP created_at
    }
    sidebar_profiles {
        VARCHAR id PK
        VARCHAR name
        VARCHAR source_type
        VARCHAR[] features
        VARCHAR language
        TEXT custom_prompt
        TEXT extra_instructions
        VARCHAR mermaid_type
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    jobs ||--o{ results_cache : "has"
    jobs ||--o{ file_chunks : "has"
    jobs ||--o{ analysis_history : "has"
    repo_metadata ||--o{ commit_snapshots : "has"
```

---

## Project Structure

```
ai_arena/1128/
├── app/
│   ├── Home.py                    # Landing page with quick stats and recent jobs
│   ├── components/
│   │   ├── feature_selector.py    # Agent checkboxes, language, presets
│   │   ├── mermaid_renderer.py    # Mermaid.js HTML component
│   │   ├── result_tabs.py         # Per-feature tabbed result renderers
│   │   ├── sidebar_profile.py     # Settings profile load/save/delete
│   │   └── source_selector.py     # Local / GitHub / Gitea input widget
│   └── pages/
│       ├── 1_Analysis.py          # Main analysis interface (background thread)
│       ├── 2_History.py           # Browse + filter past analyses
│       ├── 3_Commits.py           # Commit history analysis
│       ├── 4_Presets.py           # Prompt preset CRUD
│       └── 5_Settings.py          # Config display, temperature, DB backup
├── agents/
│   ├── _bedrock.py                # Bedrock model factory (boto3 session)
│   ├── orchestrator.py            # 4-phase pipeline coordinator
│   ├── bug_analysis.py            # Bug detection with severity + root cause
│   ├── static_analysis.py         # Linting + semantic analysis
│   ├── code_flow.py               # Execution flow narrative
│   ├── requirement.py             # Requirement reverse-engineering
│   ├── dependency_analysis.py     # SCA: dependency parsing + CVE lookup
│   ├── code_complexity.py         # Cyclomatic/cognitive complexity metrics
│   ├── test_coverage.py           # Test gap analysis + test case suggestions
│   ├── duplication_detection.py   # Code clone + DRY violation detection
│   ├── performance_analysis.py    # Big-O, memory, I/O, scalability analysis
│   ├── type_safety.py             # Type hint coverage + type issue detection
│   ├── architecture_mapper.py     # Module dependencies + layer violations
│   ├── license_compliance.py      # License detection + compatibility checks
│   ├── change_impact.py           # Blast radius + API surface analysis
│   ├── doxygen_agent.py           # Doxygen comment headers + HTML generation
│   ├── c_test_generator.py        # Python pytest + ctypes tests for C code
│   ├── code_design.py             # 3-turn design document generation
│   ├── mermaid.py                 # Mermaid diagram generation
│   ├── refactoring_advisor.py     # Code smells + refactoring suggestions
│   ├── api_doc_generator.py       # API documentation generation
│   ├── comment_generator.py       # GitHub-style PR review comments
│   ├── secret_scan.py             # Phase 0 regex + Phase 3 LLM secret detection
│   ├── threat_model.py            # STRIDE / attacker-narrative threat model
│   ├── commit_analysis.py         # Commit history + risk assessment
│   ├── release_notes.py           # User-facing release notes from commits
│   ├── developer_activity.py      # Contributor stats + activity patterns
│   ├── commit_hygiene.py          # Conventional Commits compliance audit
│   ├── churn_analysis.py          # File hotspot + co-change detection
│   ├── comparison.py              # Compare 2-5 analysis results
│   ├── report_per_file.py         # Per-file markdown report assembly
│   └── report_consolidated.py     # Consolidated report (template/LLM/hybrid)
├── tools/
│   ├── cache.py                   # SHA256-keyed composite cache helpers
│   ├── chunk_file.py              # Token-aware file splitter with overlap
│   ├── fetch_github.py            # PyGithub file + PR diff fetcher
│   ├── fetch_gitea.py             # httpx Gitea REST client
│   ├── fetch_local.py             # Local file I/O + recursive folder scan
│   ├── language_detect.py         # File extension → language name (40+ langs)
│   ├── run_linter.py              # flake8 / ESLint subprocess runner
│   ├── run_doxygen.py             # Doxygen CLI wrapper + Doxyfile generator
│   └── web_scraper.py             # URL text scraper (httpx, CLI + importable)
├── db/
│   ├── connection.py              # Thread-safe DuckDB singleton connection
│   ├── schema.py                  # 8-table DDL + auto-migration
│   └── queries/
│       ├── cache.py               # Cache read/write
│       ├── chunks.py              # File chunk store/retrieve
│       ├── history.py             # Analysis audit trail
│       ├── jobs.py                # Job CRUD
│       ├── presets.py             # Prompt preset CRUD
│       ├── repo_metadata.py       # Repo + commit snapshot storage
│       └── sidebar_profiles.py    # Settings profile CRUD
├── config/
│   └── settings.py                # Pydantic BaseSettings (.env-backed)
├── tests/                         # pytest suite (59 tests)
│   ├── agents/
│   ├── db/
│   ├── tools/
│   └── config/
├── docker/
│   └── docker-compose.yml         # Gitea self-hosted git service
├── data/                          # DuckDB file (auto-created on first run)
├── .env.example
├── requirements.txt
└── startup.bat                    # Windows one-click launcher
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit 1.56+ |
| AI Backend | AWS Bedrock — Claude (via Strands Agents 1.34+) |
| Database | DuckDB 1.5+ |
| GitHub integration | PyGithub 2.9+ |
| Gitea integration | httpx 0.28+ |
| Python linting | flake8 7+ |
| JS/TS linting | ESLint (subprocess) |
| Configuration | Pydantic Settings 2.x |
| Testing | pytest 9.x + pytest-mock 3.15+ |

---

*Developed by B.Vignesh Kumar — ic19939@gmail.com*
