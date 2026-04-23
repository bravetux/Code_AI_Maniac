# AI Arena — Code Analysis Platform Design Spec

**Date:** 2026-04-03  
**Use Case:** AI Code Maniac  
**Status:** Approved  
**Last Updated:** 2026-04-12

---

## Overview

AI Arena is a developer-facing code analysis platform with a Streamlit frontend and a multi-agent AI backend powered by AWS Strands Agents and Amazon Bedrock. Developers select source code (local files, GitHub, or Gitea), choose one or more analysis features, and receive structured results — bug reports, design docs, Mermaid diagrams, static analysis, and more — all in a single interface.

---

## Architecture

### High-Level

```
Streamlit Frontend
      ↓ job request
OrchestratorAgent (Strands)
  ├── Phase 1: Routes and parallelizes analysis sub-agent calls
  ├── Phase 2: Generates per-file and consolidated reports
  └── Aggregates results back to Streamlit
       ↕
  Analysis Agents (Strands):
  BugAnalysisAgent | CodeDesignAgent | CodeFlowAgent | MermaidAgent
  RequirementAgent | StaticAnalysisAgent | CommentGeneratorAgent | CommitAnalysisAgent
       ↕
  Report Agents (Strands):
  ReportPerFileAgent | ReportConsolidatedAgent
       ↕
  Shared Tool Layer:
  fetch_local | fetch_github | fetch_gitea | clone_repo | chunk_file
  run_linter | cache | language_detect | python_html_converter
       ↕
  DuckDB (local embedded database)
       ↕
  Amazon Bedrock (Claude via Strands)
```

### Key Principles

- Strands agents are the **only** layer that calls Bedrock — no direct Bedrock calls elsewhere
- All file fetching goes through the shared tool layer — agents never call GitHub/Gitea directly
- DuckDB is the single source of truth for jobs, cache, chunks, history, and metadata
- Streamlit polls job status from DuckDB — no direct agent ↔ UI coupling
- Sub-agents reuse each other's outputs to avoid redundant Bedrock calls

---

## Agent Design

### OrchestratorAgent
Parses the incoming job request, selects the appropriate sub-agents based on selected features, runs them in parallel where possible, and aggregates results. Handles cache checking before dispatching.

### Agent Reuse Map
```
BugAnalysisAgent  ──→ CommentGeneratorAgent (reuses bug results)
CodeFlowAgent     ──→ MermaidAgent          (reuses flow results)
StaticAnalysisAgent ──→ CommentGeneratorAgent (reuses linter results)
```

### Sub-Agent Specifications

#### Analysis Agents

| Agent | Input | Output | Strategy |
|---|---|---|---|
| BugAnalysisAgent | file(s) + optional line range | Bug list with severity, line number, description, fix suggestion, copy-ready GitHub comment text | Chunk by function/class boundary, analyze in parallel, deduplicate |
| CodeDesignAgent | file(s) | Markdown design doc — purpose, responsibilities, public API, dependencies, data contracts | Whole-file if under token limit, else summarize-then-synthesize |
| CodeFlowAgent | file(s) or entry point function | Step-by-step execution flow narrative | AST-aware chunking (Python `ast`, JS `tree-sitter`), LLM traces control flow |
| MermaidAgent | file(s) | Valid Mermaid diagram source (flowchart / sequence / class — user picks) | Reuses CodeFlowAgent output as context |
| RequirementAgent | file(s) | Structured "The system shall..." requirements grouped by component | Reverse-engineers from code — useful for undocumented legacy |
| StaticAnalysisAgent | file(s) | Linter findings + LLM semantic analysis merged | Layer 1: run pylint/flake8/eslint/semgrep locally. Layer 2: Bedrock analyzes patterns linters miss. L1 injected as L2 context |
| CommentGeneratorAgent | file(s) or PR diff | Ready-to-paste inline review comments (GitHub comment format) | Generate only — no write-back. Reuses BugAnalysis + StaticAnalysis results |
| CommitAnalysisAgent | repo + branch + date range or commit SHAs | Commit quality analysis, changelog summary, risky change patterns | Fetches via GitHub/Gitea API or local clone `git log`, analyzed in batches |

#### Report Agents

| Agent | Input | Output | Strategy |
|---|---|---|---|
| ReportPerFileAgent | file path + all feature results for that file | Single structured markdown document per source file | Pure assembly — no LLM calls. Formats all feature results into one cohesive per-file report |
| ReportConsolidatedAgent | all per-file reports + full results dict | Single "mother document" narrative for the entire codebase | Three modes: `template` (no LLM), `llm` (full narrative), `hybrid` (structure + LLM sections) |

---

## Source Integration

Three source types supported — user selects whichever is configured:

| Source | Method | Auth |
|---|---|---|
| Local File | Streamlit file uploader or path input | None |
| GitHub | PyGithub + REST API (token-optional for public repos) | Personal access token (optional for public repos) |
| GitHub Clone | `git clone` to `data/repos/<owner>/<repo>/` | Token optional — only needed for private repos |
| Gitea (self-hosted) | httpx + Gitea REST API | API token (read-only) |

### GitHub Clone & Token-Optional Access

- **URL Parser** (`tools/clone_repo.py`): Accepts full URLs (`https://github.com/owner/repo.git`), short URLs (`github.com/owner/repo`), and slugs (`owner/repo`)
- **Clone-as-Local-Source**: Cloned repos are stored in `data/repos/<owner>/<repo>/` and treated as local files for all agents
- **Token-optional**: Public repos work without a GitHub token (unauthenticated PyGithub, 60 req/hr). Token enables private repo access (5000 req/hr)
- **Clone & Browse**: After cloning, the existing folder-recursive file selection UI lets users pick files from the cloned repo
- **Commit Analysis**: Three sources on the Commits page — GitHub (Clone) uses `git log` locally (no API limits), GitHub (API) uses PyGithub, Gitea uses Gitea API

### Gitea on Docker
```yaml
# docker/docker-compose.yml
services:
  gitea:
    image: gitea/gitea:latest
    ports:
      - "3000:3000"
      - "222:22"
    volumes:
      - ./gitea:/data
    environment:
      - GITEA__server__ROOT_URL=http://localhost:3000
```
Start with `docker compose up`. Generate API token in Gitea settings and paste into the app's Settings page.

---

## Streamlit UI

### Pages
```
app/
├── Home.py                  ← landing dashboard + features showcase
└── pages/
    ├── 1_Analysis.py        ← main analysis page with two-phase progress bar
    ├── 2_History.py         ← browse and search past analyses with filters
    ├── 3_Commits.py         ← commit analysis (GitHub Clone / GitHub API / Gitea)
    ├── 4_Presets.py         ← manage saved prompt presets
    ├── 5_Settings.py        ← credentials, temperature, DB backup/restore
    └── 6_Templates.py       ← prompt template management
```

### Analysis Page Layout

**Sidebar:**
- Source selector (Local File / GitHub / Gitea)
- Language text box with auto-detection from file extension (free text, e.g. "Python", "Go", "COBOL")
- Feature checkboxes (all 8 agents)
- Advanced / Fine-tune expandable panel:
  - Editable system prompt text area
  - Extra instructions field
  - Preset dropdown + Save Preset button
- Optional line range inputs (Start / End)
- Run Analysis button

**Main Panel:**
- Results as tabs — one tab per selected feature, populated as each agent completes
- Two-phase progress bar:
  - Phase 1 (Analysis): tracks `selected_features x number_of_files` agents
  - Phase 2 (Report Generation): tracks per-file reports, consolidated report, and HTML conversions
- Live activity log with timestamped events
- Mermaid diagrams rendered live via Mermaid.js v10
- Copy button on every result block
- Re-run button (bypasses cache)
- Download as `.md` or `.json`

### Prompt Fine-Tuning
- Each feature exposes its base system prompt in an editable text area
- Extra instructions field for one-off additions (e.g. "focus on security only")
- Named presets saved to DuckDB — selectable from dropdown on future runs
- Temperature slider (0.0–1.0) on Settings page, defaults to `BEDROCK_TEMPERATURE` from `.env`

---

## DuckDB Schema

```sql
jobs (
  id           UUID PRIMARY KEY,
  status       VARCHAR,          -- pending | running | completed | failed
  source_type  VARCHAR,          -- local | github | gitea
  source_ref   VARCHAR,          -- file path, repo+branch, commit SHA
  language     VARCHAR,
  features     VARCHAR[],
  custom_prompt TEXT,
  created_at   TIMESTAMP,
  completed_at TIMESTAMP
)

results_cache (
  id           UUID PRIMARY KEY,
  job_id       UUID,
  feature      VARCHAR,
  file_hash    VARCHAR,          -- SHA256 of file content
  language     VARCHAR,
  result_json  JSON,
  created_at   TIMESTAMP
)

file_chunks (
  id           UUID PRIMARY KEY,
  job_id       UUID,
  file_path    VARCHAR,
  chunk_index  INTEGER,
  start_line   INTEGER,
  end_line     INTEGER,
  content      TEXT,
  token_count  INTEGER
)

analysis_history (
  id           UUID PRIMARY KEY,
  job_id       UUID,
  feature      VARCHAR,
  source_ref   VARCHAR,
  language     VARCHAR,
  summary      TEXT,
  created_at   TIMESTAMP
)

repo_metadata (
  id           UUID PRIMARY KEY,
  source_type  VARCHAR,
  repo_url     VARCHAR,
  branch       VARCHAR,
  last_synced  TIMESTAMP,
  commit_count INTEGER,
  file_tree    JSON
)

commit_snapshots (
  id           UUID PRIMARY KEY,
  repo_id      UUID,
  commit_sha   VARCHAR,
  author       VARCHAR,
  message      TEXT,
  diff_summary TEXT,
  files_changed VARCHAR[],
  created_at   TIMESTAMP
)

prompt_presets (
  id                 UUID PRIMARY KEY,
  name               VARCHAR,
  feature            VARCHAR,
  system_prompt      TEXT,
  extra_instructions TEXT,
  created_at         TIMESTAMP
)
```

### Backup & Restore

Implemented in `5_Settings.py` using DuckDB's native `EXPORT/IMPORT DATABASE`:

- **Export:** "Export DB" button → user provides a backup name → app runs `EXPORT DATABASE 'path' (FORMAT PARQUET)` → zips the output folder → Streamlit `st.download_button` delivers the `.zip` file. Works while app is running.
- **Import:** "Import DB" button → Streamlit file uploader accepts a `.zip` → app extracts to a temp folder → runs `IMPORT DATABASE 'path'` → reloads connection. App warns user that existing data will be overwritten before proceeding.

Parquet format is used so backup files are portable and human-inspectable outside the app.

---

### Cache Strategy
Cache hit = same `file_hash` + same `feature` + same `language`. Custom prompt content is included in the hash — changing the prompt invalidates the cache. Results are reused across jobs.

---

## Project Structure

```
ai-arena/
├── app/
│   ├── Home.py
│   ├── pages/
│   │   ├── 1_Analysis.py
│   │   ├── 2_History.py
│   │   ├── 3_Commits.py
│   │   ├── 4_Presets.py
│   │   ├── 5_Settings.py
│   │   └── 6_Templates.py
│   └── components/
│       ├── source_selector.py
│       ├── feature_selector.py
│       ├── result_tabs.py
│       ├── sidebar_profile.py
│       └── mermaid_renderer.py
├── agents/
│   ├── orchestrator.py
│   ├── _bedrock.py
│   ├── bug_analysis.py
│   ├── code_design.py
│   ├── code_flow.py
│   ├── mermaid.py
│   ├── requirement.py
│   ├── static_analysis.py
│   ├── comment_generator.py
│   ├── commit_analysis.py
│   ├── comparison.py
│   ├── report_per_file.py
│   └── report_consolidated.py
├── tools/
│   ├── fetch_local.py
│   ├── fetch_github.py
│   ├── fetch_gitea.py
│   ├── clone_repo.py
│   ├── chunk_file.py
│   ├── language_detect.py
│   ├── run_linter.py
│   ├── cache.py
│   └── python_html_converter.py
├── db/
│   ├── connection.py
│   ├── schema.py
│   └── queries/
│       ├── jobs.py
│       ├── job_events.py
│       ├── cache.py
│       ├── chunks.py
│       ├── history.py
│       ├── presets.py
│       ├── repo_metadata.py
│       └── sidebar_profiles.py
├── config/
│   ├── settings.py
│   ├── prompt_templates.py
│   ├── language_families.py
│   └── templates/
├── docker/
│   ├── docker-compose.yml
│   └── gitea/
├── data/
│   └── arena.db
├── Reports/                     ← timestamped report output directories
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── db/
│   ├── tools/
│   └── agents/
├── docs/superpowers/
│   ├── specs/                   ← design specifications
│   └── plans/                   ← implementation plans
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

---

## Key Dependencies

```txt
streamlit
strands-agents
strands-agents-tools
boto3
duckdb
PyGithub
httpx
pylint
flake8
semgrep
python-dotenv
pydantic
markdown
pygments
```

---

## Environment Configuration

```env
# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_TEMPERATURE=0.3

# GitHub (token optional for public repos)
GITHUB_TOKEN=...

# Gitea (self-hosted)
GITEA_URL=http://localhost:3000
GITEA_TOKEN=...

# Report generation
REPORT_PER_FILE=true              # Generate per-file reports (MD combining all features for one file)
REPORT_CONSOLIDATED=true          # Generate consolidated mother document
REPORT_FORMAT_MD=true             # Output markdown files
REPORT_FORMAT_HTML=true           # Output HTML files (converted from MD)
CONSOLIDATED_MODE=hybrid          # hybrid | llm | template

# Analysis limits
MAX_FILES=50                      # Maximum files per analysis run
BUG_CONTEXT_LINES=3               # Lines of context around each bug finding
```

---

## Report Generation

### Pipeline

After all analysis agents complete (Phase 1), the orchestrator runs report generation (Phase 2):

```
Phase 1: Analysis (features × files agents)
    ↓
Phase 2: Report Generation
    ├── Per-file reports (1 per source file, pure assembly)
    ├── Consolidated report (1 "mother document", template/llm/hybrid)
    └── HTML conversion (per-file + consolidated, via python_html_converter)
```

### Report Output Structure

```
Reports/20260411_143022/
  per_file/
    auth_service.md
    auth_service.html
  consolidated_report.md
  consolidated_report.html
```

### Consolidated Report Modes

| Mode | LLM Calls | Description |
|------|-----------|-------------|
| `template` | None | Structured assembly with TOC, per-file sections, summary stats |
| `llm` | Single large prompt | Fully synthesized narrative document |
| `hybrid` (default) | Targeted sections | Template skeleton + LLM-generated executive summary, cross-file narrative, architecture overview, and conclusion |

### HTML Converter (`tools/python_html_converter.py`)

Standalone + importable module producing self-contained HTML with:
- Professional typography and responsive layout
- Syntax highlighting via Pygments
- Collapsible sections, sidebar TOC with scroll-spy
- Print-friendly CSS
- No external dependencies (all CSS/JS inline)

---

## Constraints & Decisions

- Max 50 files per analysis run (`MAX_FILES` env var)
- Single-user architecture now; DB schema is multi-user ready (add `user_id` FK later)
- No write-back to GitHub/Gitea — comment generation is copy-paste only
- Temperature configurable via `.env` and Settings page at runtime
- Language is free-text input, auto-detected from file extension, fully overridable
- DuckDB chosen over SQLite for columnar analytical queries, native JSON, and multi-reader concurrency
- GitHub token optional for public repos; required only for private repository access
- `REPORT_FORMAT_HTML=true` requires `REPORT_FORMAT_MD=true` (HTML is converted from MD)
- `REPORT_CONSOLIDATED=true` requires `REPORT_PER_FILE=true` (consolidated builds on per-file)
