# AI Code Maniac — Detailed Design Document

**Project:** AG-UC-1128  
**Version:** 1.2  
**Date:** 2026-04-04  
**Author:** Engineering Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Context](#2-system-context)
3. [Architecture Overview](#3-architecture-overview)
4. [Component Design](#4-component-design)
   - 4.1 [Streamlit Frontend](#41-streamlit-frontend)
   - 4.2 [Orchestrator](#42-orchestrator)
   - 4.3 [Agent Layer](#43-agent-layer)
   - 4.4 [Tools Layer](#44-tools-layer)
   - 4.5 [Persistence Layer](#45-persistence-layer)
   - 4.6 [Configuration](#46-configuration)
5. [Data Models](#5-data-models)
6. [Key Flows](#6-key-flows)
7. [Caching Strategy](#7-caching-strategy)
8. [Multi-File Handling](#8-multi-file-handling)
9. [Agent Gating](#9-agent-gating)
10. [Error Handling & Resilience](#10-error-handling--resilience)
11. [Security Considerations](#11-security-considerations)
12. [Performance Characteristics](#12-performance-characteristics)
13. [Testing Strategy](#13-testing-strategy)
14. [Known Limitations & Technical Debt](#14-known-limitations--technical-debt)
15. [Future Roadmap](#15-future-roadmap)

---

## 1. Executive Summary

AI Code Maniac is a self-hosted, multi-agent code analysis platform. It accepts source code from GitHub, Gitea, or local files, runs up to eight specialized AI agents in a coordinated three-phase pipeline, and presents the results in a tabbed Streamlit UI with download options.

**Core design goals:**

| Goal | Design Decision |
|---|---|
| Concurrency without shared state | Phase 1 agents run fully in parallel via Python threads |
| Avoid redundant LLM calls | Composite SHA-256 cache keyed on (file + feature + language + prompt) |
| Flexible deployment posture | Per-agent gating via `ENABLED_AGENTS` env var |
| Large-file support | Token-aware chunker with configurable overlap |
| Self-contained operation | DuckDB — no external database server required |
| Non-blocking UI | Background daemon thread for analysis; 2-second polling loop |

---

## 2. System Context

```
┌─────────────────────────────────────────────┐
│                   User Browser               │
└──────────────────────┬──────────────────────┘
                       │ HTTP :8501
┌──────────────────────▼──────────────────────┐
│            Streamlit Application             │
│               (app/)                         │
└──────────────────────┬──────────────────────┘
                       │ Python function calls
┌──────────────────────▼──────────────────────┐
│            Orchestrator Agent                │
│          (agents/orchestrator.py)            │
└──┬───────────────────┬──────────────────────┘
   │                   │
   │ Fetch             │ Run agents
   ▼                   ▼
┌──────────┐   ┌───────────────────────────────┐
│  Source  │   │       Agent Pool (8 agents)    │
│  Layer   │   │  bug · static · flow · req     │
│  tools/  │   │  design · mermaid · comments   │
│  fetch_* │   │  commit_analysis               │
└──────────┘   └───────────────┬───────────────┘
                               │ Strands SDK calls
                ┌──────────────▼───────────────┐
                │        AWS Bedrock            │
                │    Claude 3.5 Sonnet          │
                └──────────────────────────────┘
┌──────────────────────────────────────────────┐
│              DuckDB  (data/arena.db)          │
│  jobs · cache · chunks · history · presets   │
│  repo_metadata · commit_snapshots · profiles │
└──────────────────────────────────────────────┘
```

**External dependencies:**

| System | Role | Required |
|---|---|---|
| AWS Bedrock | LLM inference via Claude | Yes |
| GitHub API | Source code fetching | Optional |
| Gitea REST API | Source code + commit fetching | Optional |
| flake8 | Python static linting | Optional (falls back gracefully) |
| ESLint | JS/TS static linting | Optional (falls back gracefully) |

---

## 3. Architecture Overview

### 3.1 Layer Separation

```
┌──────────────────────────────────────────────────┐
│  Presentation Layer   app/pages/, app/components/ │
├──────────────────────────────────────────────────┤
│  Orchestration Layer  agents/orchestrator.py      │
├──────────────────────────────────────────────────┤
│  Agent Layer          agents/*.py                 │
├──────────────────────────────────────────────────┤
│  Tools Layer          tools/*.py                  │
├──────────────────────────────────────────────────┤
│  Persistence Layer    db/connection.py + queries/ │
└──────────────────────────────────────────────────┘
```

### 3.2 Three-Phase Pipeline

The orchestrator executes agents in three ordered phases based on data dependencies:

```
Phase 1 — Foundation (fully parallel, no dependencies)
  ├── bug_analysis
  ├── static_analysis
  ├── code_flow
  └── requirement

Phase 2 — Context-Aware (runs after Phase 1 completes)
  ├── code_design        ← receives bug_results + static_results from Phase 1
  └── mermaid            ← reuses code_flow context from Phase 1

Phase 3 — Synthesis (runs after Phase 2 completes)
  └── comment_generator  ← aggregates bug + static findings from Phase 1
```

**Rationale:** Running Phase 1 agents in parallel maximises throughput. Feeding their output to later agents eliminates redundant Bedrock calls and produces higher-quality results (e.g., code_design can frame bugs as design symptoms).

### 3.3 Background Execution Model

The Streamlit page spawns a **daemon thread** for the analysis job. The UI auto-refreshes every 2 seconds by polling `get_job(job_id).status`. This keeps the UI responsive during analysis and does not block the Streamlit event loop.

```
Streamlit thread ──→ create_job() → spawn daemon thread → render spinner
                                          │
                         ┌────────────────▼─────────────────┐
                         │  Background Thread                 │
                         │  orchestrator.run_analysis(job_id) │
                         │  … (seconds to minutes)            │
                         │  save_job_results()                │
                         │  update_job_status("completed")    │
                         └──────────────────────────────────┘
Streamlit thread ──→ poll every 2s ──→ detect "completed" ──→ render results
```

---

## 4. Component Design

### 4.1 Streamlit Frontend

#### Pages

| File | Route | Responsibility |
|---|---|---|
| `app/Home.py` | `/` | Dashboard: quick stats (total analyses, completed, languages) and recent 10 jobs |
| `app/pages/1_Analysis.py` | `/Analysis` | Primary workflow: source selection, feature selection, job submission, live status, tabbed results |
| `app/pages/2_History.py` | `/History` | Browse and filter `analysis_history` records |
| `app/pages/3_Commits.py` | `/Commits` | GitHub/Gitea commit fetching and `commit_analysis` runner |
| `app/pages/4_Presets.py` | `/Presets` | Prompt preset CRUD |
| `app/pages/5_Settings.py` | `/Settings` | Read-only config display, temperature slider, database export/import |

#### Components

**`source_selector.py` — `render_source_selector()`**

Renders a radio group (Local / GitHub / Gitea) and source-specific input fields:

- Local: file upload (multi-file), manual path input, or recursive folder scan (respects `MAX_FILES`).
- GitHub: `owner/repo`, branch, file path, optional token override.
- Gitea: Gitea URL, `owner/repo`, branch, file path, optional token override.
- Common: optional line-range (start_line, end_line).

Returns: `{source_type, source_ref, start_line, end_line}`

**`feature_selector.py` — `render_feature_selector(conn)`**

Renders feature checkboxes filtered by `ENABLED_AGENTS`, language input, Mermaid-type selectbox, and an **Advanced / Fine-tune** expander for:

- Preset load by name
- **Prompt mode toggle** — horizontal radio with two options:
  - *Append to default* — user text is concatenated after the agent's built-in system prompt (enhances without replacing)
  - *Overwrite default* — user text replaces the built-in system prompt entirely
- System prompt text area (placeholder text changes to reflect the selected mode)
- Extra instructions text input (always appended regardless of prompt mode)
- Save-as-preset button

The selected mode is encoded as a `__append__\n` prefix on `custom_prompt` when Append is chosen; agents call `resolve_prompt()` to decode it. This means append vs overwrite on the same text produces different cache keys automatically.

Returns: `{features, language, custom_prompt, mermaid_type}`

**`sidebar_profile.py` — `render_sidebar_profile(conn)`**

Renders a selectbox of saved profile names with **Load** and **Delete** buttons, plus a name input and **Save** button. Loading a profile writes all its fields back into `st.session_state` so downstream widgets pick up the values on the next rerun.

**`result_tabs.py` — `render_results(results_dict)`**

Creates one tab per completed feature. Each tab contains:
- Feature-specific structured display (grouped by severity, collapsible expanders per finding).
- **JSON download** and **Markdown download** buttons.
- Multi-file mode: nested expanders per file path when `_multi_file: true`.

Bug Analysis tab specifics:
- Overall assessment narrative is rendered **first** (before counts or bug list) to give context.
- "No bugs found" success banner is only shown when the bug list is empty **and** no narrative is present — preventing contradictions with a narrative that describes findings.
- Each bug expander includes a **2-column code comparison** (Original Code | Fixed Code) with syntax highlighting using the job language. If snippets are absent (e.g., old cached result), a re-run caption is shown instead of hiding the columns.

**`mermaid_renderer.py` — `render_mermaid(mermaid_source)`**

Injects a Mermaid.js CDN script and renders the diagram in an `st.components.v1.html` block. The raw Mermaid source is shown in a collapsible expander below the rendered diagram.

---

### 4.2 Orchestrator

**File:** `agents/orchestrator.py`

**Public interface:**

```python
def run_analysis(job_id: str) -> None
```

**Internal steps:**

1. `update_job_status(job_id, "running")`
2. `_fetch_files(job)` — resolves `source_ref` to a list of `{file_path, content, file_hash, language}` dicts.
3. For each file (up to `MAX_FILES`): run the three-phase pipeline.
4. Merge per-file results; wrap multi-file outputs under `_multi_file` flag.
5. `save_job_results(job_id, results)`
6. `update_job_status(job_id, "completed")`

**File fetch routing:**

| source_type | Format | Tool |
|---|---|---|
| `local` | `/path/a.py::/path/b.py` | `fetch_local_file()` |
| `github` | `owner/repo::branch::path` | `fetch_github_file()` |
| `gitea` | `owner/repo::branch::path` | `fetch_gitea_file()` |

Language is auto-detected via `detect_language(file_path)` if not specified in the job.

---

### 4.3 Agent Layer

Each agent follows the same contract:

```python
def run_<feature>(
    file_path: str,
    content: str,
    file_hash: str,
    language: str,
    custom_prompt: str | None,
    job_id: str,
    conn,
    **kwargs,          # feature-specific context (e.g., bug_results for code_design)
) -> dict
```

All agents check the cache first. On a miss they call Bedrock, store the result in cache, and add an `analysis_history` record.

All agents use `resolve_prompt(custom_prompt, base_prompt)` from `agents/_bedrock.py` to determine the effective system prompt:

```python
def resolve_prompt(custom_prompt: str | None, base_prompt: str) -> str:
    if not custom_prompt:
        return base_prompt                          # no override
    if custom_prompt.startswith("__append__\n"):
        return base_prompt + "\n\n" + user_text     # append mode
    return custom_prompt                            # overwrite mode
```

#### Agent Details

**Bug Analysis (`bug_analysis.py`)**

- Chunks file at 3 000 token max.
- Per-chunk: calls Bedrock with senior-engineer reviewer system prompt.
- Deduplicates bugs by `(line, description[:50])`.
- After deduplication, **`original_snippet`** is extracted programmatically from the file content using `BUG_CONTEXT_LINES` lines above and below the reported line. Line numbers from the LLM are coerced to `int` (handles cases where the LLM returns a string).
- **`fixed_snippet`** is requested from the LLM as part of the JSON schema — the corrected code block that resolves the bug.
- Cache key uses versioned constant `"bug_analysis:v2"` — bumping this forces re-analysis when the output schema changes.
- Returns: `{bugs: [...], narrative, summary, language}`

Bug record shape:
```json
{
  "line": 42,
  "severity": "critical|major|minor",
  "description": "...",
  "runtime_impact": "...",
  "root_cause": "...",
  "suggestion": "...",
  "fixed_snippet": "corrected code block from LLM",
  "original_snippet": "N context lines around the bug line (extracted from file)",
  "snippet_start_line": 37,
  "github_comment": "PR-ready markdown"
}
```

**Static Analysis (`static_analysis.py`)**

Two-layer approach:
1. **Linter layer** — runs flake8 (Python) or ESLint (JS/TS) as subprocess, parses output into `linter_findings`.
2. **LLM semantic layer** — sends linter output + full code to Bedrock; identifies design smells, security anti-patterns, performance issues, maintainability issues, error-handling gaps.

Returns: `{linter_findings, semantic_findings, narrative, linter_skipped, summary}`

**Code Flow (`code_flow.py`)**

- Chunks at 4 000 tokens with overlap for continuity.
- Each chunk analyzed independently.
- If >1 chunk, a synthesis call combines chunk narratives into a single coherent document.
- Returns: `{markdown, summary, entry_points, steps}`

**Requirement Analysis (`requirement.py`)**

- Chunks at configurable budget.
- Each chunk yields REQ-NNN requirements in markdown.
- Multi-chunk synthesis renumbers REQ IDs sequentially.
- Returns: `{markdown, summary, requirements}`

**Code Design (`code_design.py`) — 3-Turn Conversation**

The most complex agent; uses a multi-turn conversation pattern with Bedrock:

| Turn | Budget | Input | Output |
|---|---|---|---|
| Turn 1 — Understand | 6 000 tokens | Chunked code sections | Structural notes (free-form) |
| Turn 2 — Analyse | — | T1 notes + bug findings + static findings | Structured JSON: title, purpose, design_assessment, design_issues, public_api, dependencies, data_contracts, improvements |
| Turn 3 — Document | — | T2 JSON | 9-section markdown design document |

Fallback handling: if Turn 2 JSON parse fails → store raw response; if Turn 3 fails → store structured fields, leave `design_document` empty.

9 document sections:
1. Executive Summary
2. Architecture Overview
3. Responsibilities & Scope
4. Interface & Public API
5. Data Flow
6. Design Decisions & Rationale
7. Known Issues & Technical Debt
8. Improvement Roadmap
9. Dependencies

**Mermaid (`mermaid.py`)**

- If `code_flow` result is available, passes it as context (avoids a separate Bedrock call for code understanding).
- Otherwise sends raw file content.
- Diagram types: `flowchart`, `sequence`, `class`.
- Returns: `{diagram_type, mermaid_source, description}`

**PR Comment Generator (`comment_generator.py`)**

- Receives merged `bug_findings + static_findings` from Phase 1.
- Calls Bedrock once with a constructive senior-engineer system prompt.
- Returns: `{comments: [{file, line, severity, body}], summary}`

**Commit Analysis (`commit_analysis.py`)**

- Batches commits 20 at a time.
- If >20 commits: synthesizes batch results into a final report.
- Extracts `risk_level` by scanning markdown for "high risk" / "medium risk" / "low risk" keywords.
- Returns: `{markdown, summary, risk_level}`

---

### 4.4 Tools Layer

#### `fetch_local.py`

| Function | Description |
|---|---|
| `fetch_local_file(path, start, end)` | Reads file with UTF-8 error handling; returns `{file_path, content, total_lines, start_line, end_line, file_hash, extension}` |
| `fetch_multiple_local_files(paths)` | Batch wrapper around `fetch_local_file` |
| `scan_folder_recursive(folder, exts)` | Walks directory tree, skips `.git`, `.venv`, `__pycache__`; filters by extension list |

#### `fetch_github.py`

| Function | Description |
|---|---|
| `fetch_github_file(repo, path, branch, token, start, end)` | PyGithub — returns same schema as local fetcher |
| `fetch_github_pr_diff(repo, pr_number, token)` | Returns PR files with patch content and change status |

#### `fetch_gitea.py`

| Function | Description |
|---|---|
| `fetch_gitea_file(url, repo, path, branch, token, start, end)` | httpx REST — `GET /api/v1/repos/{repo}/contents/{path}?ref={branch}`; base64 decodes content |
| `fetch_gitea_commits(url, repo, branch, token, limit)` | Returns `[{sha, message, author}]` list |

#### `chunk_file.py`

```python
def chunk_by_lines(content: str, max_tokens: int = 3000, overlap_lines: int = 0) -> list[dict]
```

Token estimate: `len(text) // 4`.

Each chunk dict: `{content, start_line, end_line, token_count}`.

Overlap support allows context continuity between chunks for synthesis tasks.

#### `run_linter.py`

```python
def run_linter(file_path: str, language: str) -> dict
```

- Python → flake8 subprocess. Parses `path:line:col: CODE message`.
- JavaScript/TypeScript → ESLint subprocess with `--format json`.
- Returns: `{findings: [{line, col, code, message, tool}], skipped, reason}`.
- If linter is not installed or language is unsupported: `skipped=True`.

#### `language_detect.py`

```python
def detect_language(file_path: str) -> str
```

Maps 40+ file extensions to human-readable language names. Special-cases: `Makefile`, `Dockerfile`, `Gemfile`, `Podfile`.

#### `cache.py`

```python
def compute_cache_key(file_hash, feature, language, custom_prompt) -> str  # SHA-256 hex
def check_cache(file_hash, feature, language, custom_prompt) -> dict | None
def write_cache(job_id, feature, file_hash, language, custom_prompt, result) -> None
```

**Schema versioning convention:** When an agent's output schema changes (new fields added), the `feature` value passed to cache functions is bumped (e.g., `"bug_analysis"` → `"bug_analysis:v2"`). Old entries remain in the table but are no longer consulted, forcing a fresh Bedrock call.

---

### 4.5 Persistence Layer

#### Connection Management (`db/connection.py`)

Thread-safe singleton using double-checked locking. Auto-creates the `data/` directory. Raises `RuntimeError` if the database file is locked by another process. `reset_connection()` is available for test isolation.

#### Schema (`db/schema.py`)

Eight tables initialized on first connection:

| Table | Purpose |
|---|---|
| `jobs` | Job lifecycle records (pending → running → completed/failed) |
| `results_cache` | Agent output cache keyed by composite SHA-256 hash |
| `file_chunks` | Chunked file content for large-file jobs |
| `analysis_history` | Audit trail: one row per agent run |
| `repo_metadata` | Repository info for commit analysis |
| `commit_snapshots` | Individual commit records with UNIQUE(repo_id, commit_sha) |
| `prompt_presets` | Named custom prompt configurations |
| `sidebar_profiles` | Named full-sidebar analysis configurations |

#### Query Modules (`db/queries/`)

Each module covers CRUD for one domain. All queries use parameterized statements (no string interpolation) to prevent SQL injection.

---

### 4.6 Configuration

**File:** `config/settings.py`

Pydantic `BaseSettings` model backed by `.env` file. All fields are validated on startup; missing required AWS fields will surface as a `ValidationError` with clear field names.

Key settings with defaults:

```python
class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_temperature: float = 0.3
    db_path: str = "data/arena.db"
    max_files: int = 50
    bug_context_lines: int = 5   # lines above/below bug line in code comparison (0–20)
    enabled_agents: str = "all"
```

`get_settings()` is a cached factory (singleton) so `.env` is parsed once per process.

---

## 5. Data Models

### Job

```python
{
    "id": "uuid4",
    "status": "pending | running | completed | failed",
    "source_type": "local | github | gitea",
    "source_ref": "string — path or owner/repo::branch::path",
    "language": "Python | JavaScript | ...",
    "features": ["bug_analysis", "code_design", ...],
    "custom_prompt": "optional string",
    "result_json": { ...agent results... },
    "created_at": "ISO timestamp",
    "completed_at": "ISO timestamp | null"
}
```

### Agent Result (per feature)

Single-file:
```json
{
  "bug_analysis": { "bugs": [...], "narrative": "...", "summary": "...", "language": "Python" }
}
```

Multi-file:
```json
{
  "bug_analysis": {
    "_multi_file": true,
    "summary": "2 file(s) analysed.",
    "files": {
      "src/foo.py": { "bugs": [...], "narrative": "...", "summary": "..." },
      "src/bar.py": { "bugs": [...], "narrative": "...", "summary": "..." }
    }
  }
}
```

### Cache Key

```
SHA256( file_hash + ":" + feature + ":" + language + ":" + (custom_prompt or "") )
```

`custom_prompt` encodes both the text **and** the prompt mode — an `__append__\n` prefix is prepended when Append mode is selected in the UI. This means the same prompt text in Append vs Overwrite mode produces distinct cache entries.

`feature` may include a version suffix (e.g., `"bug_analysis:v2"`) to invalidate all prior entries when the output schema changes.

---

## 6. Key Flows

### 6.1 New Analysis Job (happy path)

```
1.  User configures source + features in sidebar → clicks "Run Analysis"
2.  1_Analysis.py: create_job(source_type, source_ref, language, features, custom_prompt) → job_id
3.  1_Analysis.py: spawn daemon thread → orchestrator.run_analysis(job_id)
4.  Streamlit enters polling loop (st.rerun every 2s)

5.  Orchestrator: update_job_status(job_id, "running")
6.  Orchestrator: _fetch_files(job) → file list
7.  Orchestrator: detect_language per file (if not overridden)

8.  Phase 1 — run in parallel (ThreadPoolExecutor or asyncio):
    a. run_bug_analysis(file, ...)
       - check_cache → miss
       - chunk_by_lines(content, max_tokens=3000)
       - for each chunk: Bedrock call
       - merge + deduplicate bugs
       - write_cache + add_history
    b. run_static_analysis — linter subprocess + Bedrock semantic
    c. run_code_flow — chunk + Bedrock + synthesis if multi-chunk
    d. run_requirement — chunk + Bedrock + synthesis

9.  Phase 2:
    a. run_code_design(bug_results, static_results)
       - Turn 1: summarize chunks
       - Turn 2: inject Phase 1 context → JSON analysis
       - Turn 3: JSON → 9-section markdown
    b. run_mermaid(code_flow_context)
       - Single Bedrock call with diagram_type parameter

10. Phase 3:
    a. run_comment_generator(bug_findings + static_findings)
       - Single Bedrock call
       - Returns PR-style comments

11. Orchestrator: save_job_results(job_id, merged_results)
12. Orchestrator: update_job_status(job_id, "completed")

13. Streamlit poll detects "completed"
14. get_job_results(job_id) → results dict
15. render_results(results_dict) → tabbed UI
```

### 6.2 Cache Hit Flow

```
Phase 1 agent called
  → compute_cache_key(file_hash, feature, language, custom_prompt)
  → SELECT from results_cache WHERE file_hash = ?
  → Row found → return cached result dict immediately
  → No Bedrock call, no history record
```

### 6.3 Settings Profile Load

```
User selects profile name → clicks "Load"
  → get_profile(name) → profile dict
  → Write all fields to st.session_state
  → st.rerun() → widgets initialize from session_state
```

---

## 7. Caching Strategy

### Cache Key Design

The composite SHA-256 key is computed from four dimensions:

```
key = SHA256( file_hash + ":" + feature + ":" + language + ":" + custom_prompt )
```

| Dimension | Change behavior |
|---|---|
| `file_hash` | File edit → hash changes → cache miss |
| `feature` | Different agent → different cache entry |
| `language` | Changing language → new entry (language influences prompt behavior) |
| `custom_prompt` | Any prompt change → new entry (different instructions → different result) |

### Invalidation

Cache entries are **never automatically invalidated** (no TTL). The only events that produce a cache miss are:

- The file content changes (SHA-256 hash changes).
- The language or custom prompt is different.
- A new feature is selected that has no prior entry.

For a fresh analysis run on a cached file, the user must change the file content, the language, or the custom prompt.

### Storage

Results are stored in the `results_cache` DuckDB table as JSON. Cache entries are persisted across app restarts.

---

## 8. Multi-File Handling

### Source Reference Formats

| Source | Single File | Multi-File |
|---|---|---|
| Local | `/path/to/file.py` | `/path/a.py::/path/b.py::/path/c.py` |
| GitHub | `owner/repo::branch::path` | Not supported (single file per job) |
| Gitea | `owner/repo::branch::path` | Not supported (single file per job) |

Local multi-file refs are split on `::` by the orchestrator. Folder scan (via `scan_folder_recursive`) also produces a `::` joined ref string up to `MAX_FILES`.

### Per-File Processing

Each file in the list is processed through the full three-phase pipeline independently. Results are stored per file path.

### Result Merging

```python
results[feature] = {
    "_multi_file": True,
    "summary": f"{len(files)} file(s) analysed.",
    "files": {
        file_path: per_file_result,
        ...
    }
}
```

The `result_tabs.py` component detects `_multi_file: true` and renders nested expanders, one per file.

---

## 9. Agent Gating

`ENABLED_AGENTS` is parsed at startup into a Python set of agent keys. The orchestrator and feature_selector both respect this set.

### Validation Logic

```python
ALL_AGENTS = {"bug_analysis", "code_design", "code_flow", "mermaid",
              "requirement", "static_analysis", "comment_generator", "commit_analysis"}

if value in ("all", "*", ""):
    enabled = ALL_AGENTS
else:
    requested = {k.strip() for k in value.split(",")}
    enabled = requested & ALL_AGENTS  # silently drops typos
```

### Enforcement Points

1. **`feature_selector.py`** — only renders checkboxes for enabled agents.
2. **`orchestrator.py`** — skips Phase 1/2/3 calls for disabled agents.
3. **`run_analysis()`** — feature list is already filtered by the user's selection, which was already filtered by `ENABLED_AGENTS`.

---

## 10. Error Handling & Resilience

### Per-Feature Errors

If an individual agent call fails (Bedrock timeout, JSON parse error, etc.), the error is stored under the feature key rather than failing the whole job:

```json
{
  "bug_analysis": {"error": "Bedrock throttling: rate limit exceeded"},
  "code_flow": { ... successful result ... }
}
```

The `render_results()` function renders an error message for failed features while displaying results for successful ones.

### Job-Level Errors

If the job fails entirely (e.g., file fetch fails, invalid source_ref), the orchestrator:

1. Catches the top-level exception.
2. `update_job_status(job_id, "failed")`
3. Stores `{"error": str(exception)}` as `result_json`.
4. The UI displays the error message when the polling loop detects `status=failed`.

### Linter Fallbacks

If flake8 or ESLint is not installed, `run_linter()` returns `{findings: [], skipped: True, reason: "flake8 not found"}`. `static_analysis.py` proceeds with only the LLM semantic layer.

### Code Design Turn Fallbacks

| Failure | Behavior |
|---|---|
| Turn 2 JSON parse fails | Returns `{markdown: raw_response, design_document: ""}` |
| Turn 3 Bedrock exception | Returns structured T2 fields, `design_document: ""` |
| Turn 1 Bedrock exception | Propagates as feature-level error |

---

## 11. Security Considerations

### Credential Handling

- All credentials (AWS keys, tokens) are stored in `.env` (not in code).
- `.env` must be excluded from version control via `.gitignore`.
- The Settings page masks credential values in the UI (read-only display with partial masking).
- Credentials are never logged.

### SQL Injection Prevention

All DuckDB queries use parameterized statements:

```python
conn.execute("SELECT * FROM jobs WHERE id = ?", [job_id])
```

No user input is ever interpolated directly into SQL strings.

### File Path Security

- Local file paths from user input are used directly. The platform is intended for self-hosted use by trusted users. In a multi-tenant deployment, path traversal validation would be required.
- Uploaded files are written to a temporary directory (`tempfile.mkdtemp()`); they are not persisted after the session ends.

### LLM Prompt Security

- Custom prompts from the user are appended as extra instructions, not injected into the system prompt position.
- System prompts are hardcoded in each agent file and cannot be replaced via the UI (only supplemented via extra instructions).

---

## 12. Performance Characteristics

### Latency

| Scenario | Expected Latency |
|---|---|
| Cache hit (all features) | < 1 second |
| Single small file, all 8 agents | 20 – 60 seconds (Bedrock latency × phases) |
| Large file (chunked, all agents) | 60 – 180 seconds |
| Multi-file (10 files) | 2 – 10 minutes (sequential per file) |

### Bedrock Call Budget

Per single-file analysis (8 agents, no cache):

| Phase | Calls |
|---|---|
| Phase 1 (4 agents) | 4 × N_chunks each |
| Phase 2 — code_design | 3 (Turn 1, Turn 2, Turn 3) |
| Phase 2 — mermaid | 1 |
| Phase 3 — comment_generator | 1 |
| Total (small file) | ~9 – 12 calls |

### Token Budget per Agent

| Agent | Max tokens per chunk |
|---|---|
| bug_analysis | 3 000 |
| static_analysis | Full file (no chunking; linter runs on disk) |
| code_flow | 4 000 |
| requirement | 4 000 |
| code_design Turn 1 | 6 000 |
| commit_analysis | 20 commits per call |

---

## 13. Testing Strategy

### Test Pyramid

```
                  ┌───────────────┐
                  │  Integration   │  tests/db/test_schema.py
                  │   Tests        │  tests/tools/test_fetch_github.py
                 ┌┴───────────────┴┐
                 │   Unit Tests     │  tests/agents/test_*
                 │   (mocked LLM)   │  tests/tools/test_chunk_file.py
                 │                  │  tests/db/test_queries.py
                ┌┴──────────────────┴┐
                │   Config Tests      │  tests/config/test_config.py
                └────────────────────┘
```

### Key Test Patterns

**Orchestrator tests (`test_orchestrator.py`):**

- Mock `_fetch_files()` to return a fake file list.
- Mock each agent function (`run_bug_analysis`, etc.).
- Assert correct agents called based on features list.
- Assert disabled agents (via `ENABLED_AGENTS`) are never called.
- Assert multi-file results have `_multi_file: True`.
- Assert job status transitions: pending → running → completed.

**Database tests:**

- Use in-memory DuckDB via `conftest.py` fixture.
- Test full CRUD lifecycle for each query module.
- Test cache hit/miss logic with same and differing parameters.

**Tool tests:**

- `test_chunk_file.py` — boundary conditions for token-based splitting.
- `test_run_linter.py` — subprocess mock; parse output format variations.
- `test_fetch_local.py` — file read, missing file error path, line-range slicing.

### Running Tests

```bash
pytest                                          # all tests
pytest tests/agents/ -v                        # agent tests only
pytest tests/db/test_queries.py -v             # DB query tests only
pytest -k "cache" -v                           # tests matching "cache"
```

---

## 14. Known Limitations & Technical Debt

| Item | Impact | Severity |
|---|---|---|
| Multi-file GitHub/Gitea not supported | Cannot analyze entire repos directly; must specify individual files | Medium |
| No cache TTL or eviction | Cache grows indefinitely; old entries are never cleaned | Low |
| Sequential per-file processing in multi-file jobs | 10-file job takes 10× single-file time | Medium |
| `comment_generator` depends on Phase 1 but Phase 1 errors are silently skipped | May produce empty PR comments if bug_analysis fails | Low |
| No authentication/authorization | Platform is single-user; adding multi-user would require session auth | Medium |
| Mermaid.js loaded from CDN | Fails in air-gapped deployments | Low |
| Database backup is full DuckDB export | No incremental backup; large DBs take significant time | Low |
| Temperature UI override is session-only | Does not persist across page reloads | Low |

---

## 15. Future Roadmap

| Feature | Description |
|---|---|
| Parallel multi-file processing | Use `ThreadPoolExecutor` to analyze files concurrently |
| GitHub/Gitea multi-file support | Fetch and analyze all files in a repo path |
| Webhook integration | Trigger analysis automatically on PR open / push events |
| Cache TTL and eviction | Time-based or size-based cache cleanup |
| User authentication | Basic login gate for shared/team deployments |
| CI/CD export | Export findings as SARIF or JUnit XML for integration with GitHub Actions |
| Streaming results | Stream Bedrock responses to show partial results as they arrive |
| Model selection per agent | Allow each agent to use a different Claude model |
| Local LLM support | Swap Bedrock for Ollama or other local inference |
| VS Code extension | Trigger analysis from the editor context menu |
