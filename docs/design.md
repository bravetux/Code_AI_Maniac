# AI Code Maniac — Detailed Design Document

**Project:** AI Code Maniac  
**Version:** 1.5  
**Date:** 2026-04-22  
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

AI Code Maniac is a self-hosted, multi-agent code analysis platform. It accepts source code from GitHub, Gitea, or local files, runs up to **41 specialized AI agents** organised across **six delivery phases** (Phase 0 pre-flight, Phase 1 foundation, Phase 2 context-aware, Phase 3 synthesis, Phase 4 threat model, Phase 5 quick wins, Phase 6 Wave 6A spec-driven test generation, Phase 6 Wave 6B PR-ready code-patching), and presents the results in a tabbed Streamlit UI with download options. A dedicated Commits page provides 5 analysis modes for git history, and two CLI/server tools (`webhook_server.py`, `precommit_reviewer.py`) expose the agents outside the UI.

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
┌──────────┐   ┌───────────────────────────────────────┐
│  Source  │   │   Agent Pool (41 agents, 6 phases)     │
│  Layer   │   │  P0 secret pre-flight · P1 foundation  │
│  tools/  │   │  P2 context · P3 synthesis · P4 threat │
│  fetch_* │   │  P5 quick wins · P6 Wave 6A tests      │
│          │   │  P6 Wave 6B code-patch (4 agents)      │
└──────────┘   └───────────────┬───────────────────────┘
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

### 3.2 Six-Phase Pipeline

The orchestrator executes agents in ordered phases based on data dependencies. Phases 0-4 form the original file-analysis pipeline; Phase 5 and Phase 6 Wave 6A add post-baseline capabilities (quick-win generators and spec-driven test generation):

```
Phase 0 — Pre-flight (regex-based, before LLM calls)
  └── secret_scanner             ← redact/block secrets before analysis

Phase 1 — Foundation (foundation agents run fully in parallel; Phase 2 agents listed below depend on Phase 1 outputs)
  ├── bug_analysis
  ├── static_analysis
  ├── code_flow
  ├── requirement
  ├── dependency_analysis
  ├── code_complexity
  ├── test_coverage
  ├── duplication_detection
  ├── performance_analysis
  ├── type_safety
  ├── architecture_mapper
  ├── license_compliance
  ├── change_impact
  ├── doxygen                  ← adds Doxygen headers to C/C++ code + runs doxygen CLI
  └── c_test_generator         ← generates Python pytest + ctypes tests for C code

Phase 2 — Context-Aware (run after Phase 1 completes; these five are also counted under Phase 1 Code Analysis in ALL_AGENTS)
  ├── code_design              ← receives bug_results + static_results
  ├── mermaid                  ← reuses code_flow context
  ├── refactoring_advisor      ← receives complexity + static + duplication results
  ├── api_doc_generator        ← reuses code_flow context
  └── comment_generator        ← aggregates bug + static findings (listed again in Phase 3 below for legacy reasons)

Phase 3 — Synthesis (runs after Phase 2 completes)
  ├── comment_generator        ← aggregates bug + static findings
  └── secret_scan              ← phase0 findings + static results

Phase 4 — Threat Model (runs after Phase 3 completes)
  └── threat_model             ← bug + static + secret + dependency results

Commit Agents (separate pipeline, not file-based)
  ├── commit_analysis          ← commit history review + risk assessment
  ├── release_notes            ← user-facing release notes from commits
  ├── developer_activity       ← contributor stats + activity patterns
  ├── commit_hygiene           ← Conventional Commits compliance audit
  └── churn_analysis           ← file hotspot detection (clone only)

Phase 5 — Quick Wins (7 agents + 2 CLI/server tools, dispatched from the sidebar UI)
  ├── unit_test_generator      (F1)  ← pytest/JUnit/xUnit/Jest units per function
  ├── story_test_generator     (F2)  ← BDD/story-driven tests from user narratives
  ├── gherkin_generator        (F3)  ← Gherkin .feature files from requirements
  ├── test_data_generator      (F8)  ← fixture/factory data for unit + API tests
  ├── dead_code_detector       (F17) ← unreachable / unused symbol sweep
  ├── api_contract_checker     (F24) ← OpenAPI-vs-implementation diff via openapi_parser
  ├── openapi_generator        (F37) ← infers OpenAPI spec from code via openapi_parser
  ├── tools/webhook_server.py  (F20) ← FastAPI webhook entrypoint (CLI/server, not in ALL_AGENTS)
  └── tools/precommit_reviewer.py (F21) ← git pre-commit hook entrypoint (CLI, not in ALL_AGENTS)

Phase 6 Wave 6A — Spec-Driven Test Generation (3 agents, share a Reports/<ts>/ folder)
  ├── api_test_generator       (F5)  ← framework-auto-picked API tests + Postman collection
  ├── perf_test_generator      (F6)  ← JMeter plan.jmx (default) or Gatling Simulation.scala
  └── traceability_matrix      (F10) ← AC-to-test matrix; auto-scans sibling F5/F6 outputs

Phase 6 Wave 6B — PR-Ready Code Patching (4 agents, share the same Reports/<ts>/ folder; all emit diffs via tools/patch_emitter.py)
  ├── self_healing_agent       (F9)  ← rewrites broken Selenium/Playwright/Cypress selectors from live DOM
  ├── sonar_fix_agent          (F11) ← ingests Sonar issues (prefix / JSON / live API) and emits per-file fixes
  ├── sql_generator            (F14) ← NL→SQL with DDL-parsed schema context (PostgreSQL-first, ANSI fallback, RLS-aware)
  └── auto_fix_agent           (F15) ← consumes Bug Analysis + Refactoring Advisor findings (prefix or sidecar) and emits a unified diff
```

**Rationale:** Running Phase 1 agents in parallel maximises throughput. Feeding their output to later agents eliminates redundant Bedrock calls and produces higher-quality results (e.g., code_design can frame bugs as design symptoms, refactoring_advisor builds on complexity and duplication findings).

**Phase 5 invocation:** Phase 5 agents are registered in `ALL_AGENTS` and dispatched by the orchestrator like any other file-mode agent (selected via sidebar checkboxes). `webhook_server.py` and `precommit_reviewer.py` are intentionally NOT in `ALL_AGENTS` — they are CLI/server entrypoints that invoke the orchestrator from outside the UI and are documented alongside Phase 5 because they ship in the same release.

**Phase 6 Wave 6A invocation:** F5, F6, F10 are dispatched by the orchestrator from the sidebar UI. They coordinate via the `JOB_REPORT_TS` environment variable (see "Cross-Agent Coordination" below) so that a multi-agent job (e.g., F5 + F10 together) produces a single `Reports/<ts>/` run folder.

**Phase 6 Wave 6B invocation:** F9, F11, F14, F15 are dispatched by the orchestrator from the sidebar UI and share the same `Reports/<JOB_REPORT_TS>/` folder as Wave 6A. Every Wave 6B agent produces a PR-ready artifact triple under its own subfolder — `patches/<file>` (rewritten content), `patches/<file>.diff` (unified diff), `pr_comment.md` (reviewer-facing summary), and `summary.json` (machine-readable index) — all written by the shared deterministic `tools/patch_emitter.py`. Typical invocation: sidebar checkbox + intake-prefix data in extra instructions (or, for F15, co-selection with `bug_analysis`/`refactoring_advisor` in the same run so it auto-picks up the `findings.json` sidecars).

### 3.2.1 Cross-Agent Coordination (Wave 6A + Wave 6B)

At the start of every `run_analysis(conn, job_id)` call, the orchestrator sets `JOB_REPORT_TS=<timestamp>` in the process environment. All 7 multi-wave agents (F5/F6/F10 from Wave 6A and F9/F11/F14/F15 from Wave 6B) read it via the shared `_report_ts()` helper with the fallback chain `JOB_REPORT_TS` → `WAVE6A_REPORT_TS` → `datetime.now()`. `WAVE6A_REPORT_TS` is retained as a back-compat alias for one release so that any external script setting the old name keeps working; new code paths should set `JOB_REPORT_TS`.

The reason this exists: F10 (traceability_matrix) needs to discover the `api_collection.json` that F5 wrote and the `plan.jmx`/`Simulation.scala` that F6 wrote **in the same run**. F15 (auto_fix_agent) similarly needs to find the `findings.json` sidecar files that `bug_analysis` and `refactoring_advisor` dropped next to their markdown output. Without a shared timestamp, every agent would write to its own `Reports/<ts>/` folder and downstream consumers would have no deterministic way to find their siblings. With the shared timestamp, F10's `_auto_scan_same_run()` walks `Reports/<shared_ts>/api_tests/` and `Reports/<shared_ts>/perf_tests/`, and F15's auto-scan walks `Reports/<shared_ts>/bug_analysis/` and `Reports/<shared_ts>/refactoring_advisor/` — no explicit overrides needed.

### 3.2.2 Intake Prefix Markers (Wave 6A + Wave 6B + generic)

Several agents accept custom_prompt prefix markers that switch modes or inject non-prompt data. These are stripped by `resolve_prompt()` or by agent-specific parsers before the text hits Bedrock:

| Marker | Consumer | Purpose |
|---|---|---|
| `__openapi_spec__\n<YAML>` | F5, F6 (spec mode) | Supplies an OpenAPI YAML spec; triggers spec-driven test generation instead of code-driven |
| `__mode__requirements\n<story>` | F6 | Switches F6 into requirements/story mode (load profile derived from narrative, not spec) |
| `__stories__\n<text>` | F10 | Provides user stories / acceptance criteria text for traceability extraction |
| `__tests_dir__=<path>` | F10 | Explicit override for the tests folder to scan (normally F10 auto-discovers siblings via `JOB_REPORT_TS`) |
| `__src_dir__=<path>` | F10 | Explicit source-code folder; when set, F10 invokes the `run_test_coverage` subagent to fill coverage gaps |
| `__findings__\n<json\|md>` | F15 | Explicit Bug Analysis + Refactoring Advisor findings feed (skips sidecar auto-scan) |
| `__sonar_issues__\n<json>` | F11 | Inline Sonar issues payload; alternative to fetching via `tools/sonar_fetcher.py` |
| `__sonar_top_n__=<int>` | F11 | Cap on issues processed (severity-sorted). Default 50 |
| `__db_schema__\n<DDL\|YAML>` | F14 | Database schema supplied as DDL text or YAML; parsed by `tools/ddl_parser.py` |
| `__prompt__\n<NL request>` | F14 (required) | Natural-language SQL request; the sole LLM input for F14 alongside the parsed schema |
| `__page_html__\n<html>` | F9 | Page DOM used to relocate broken UI-test selectors |
| `__page_url__=<url>` | F9 (reserved) | Live page URL; reserved for a future headless-browser fetch integration |
| `__append__\n` | All agents (via `agents/_bedrock._APPEND_PREFIX`) | Generic append-vs-overwrite toggle; F10's UI helper wraps its block with this so sibling agents keep their base prompts when F10 is co-selected |

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
3. For each file (up to `MAX_FILES`): run the four-phase pipeline.
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

#### Agent Details — Code Quality & Metrics

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

**Code Complexity (`code_complexity.py`)**

- Computes cyclomatic complexity, cognitive complexity, maintainability index per function.
- Identifies hotspots (top 3-5 most complex functions) with simplification suggestions.
- Returns: `{markdown, summary}`

**Duplication Detection (`duplication_detection.py`)**

- Finds exact duplicates, near-duplicates (structural clones), and repeated patterns.
- Suggests concrete extractions (Extract Function, Base Class, Template Method).
- Returns: `{markdown, summary}`

**Type Safety (`type_safety.py`)**

- Type hint coverage audit: counts typed vs untyped functions.
- Flags missing annotations, overly broad types, and suggests advanced typing patterns.
- Language-aware (Python PEP 484+, TypeScript strict mode, etc.).
- Returns: `{markdown, summary}`

#### Agent Details — Code Understanding

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

**Architecture Mapper (`architecture_mapper.py`)**

- Maps module dependencies, imports, exports, and coupling metrics.
- Detects layer violations, circular dependencies, and God modules.
- Generates a Mermaid component diagram.
- Returns: `{markdown, summary}`

**Mermaid (`mermaid.py`)**

- If `code_flow` result is available, passes it as context (avoids a separate Bedrock call for code understanding).
- Otherwise sends raw file content.
- Diagram types: `flowchart`, `sequence`, `class`.
- Returns: `{diagram_type, mermaid_source, description}`

#### Agent Details — Performance & Optimization

**Performance Analysis (`performance_analysis.py`)**

- Big-O time and space complexity per function.
- Identifies N+1 queries, unbounded allocations, caching opportunities, scalability concerns.
- Returns: `{markdown, summary}`

**Refactoring Advisor (`refactoring_advisor.py`)**

- Receives Phase 1 context: `complexity_results`, `static_results`, `duplication_results`.
- Identifies code smells (God Class, Feature Envy, Long Method, etc.).
- Recommends Fowler-catalogue refactorings with before/after code sketches.
- Returns: `{markdown, summary}`

#### Agent Details — Testing & Maintenance

**Test Coverage (`test_coverage.py`)**

- Analyses code structure to identify untested functions and missing test cases.
- Produces function inventory with test priority ratings and test skeleton code.
- Returns: `{markdown, summary}`

**Change Impact (`change_impact.py`)**

- Estimates blast radius for modifications to this module.
- Maps public API surface, downstream dependents, and side effects.
- Generates specific change scenarios with migration guidance.
- Returns: `{markdown, summary}`

**C Test Generator (`c_test_generator.py`)**

- Takes C source code and generates a Python pytest file using `ctypes` bindings.
- Defines `argtypes`/`restype` for type-safe function calls.
- Generates test classes per function: happy path, boundary values, NULL pointers, error handling.
- Saves generated test file to `Reports/{timestamp}/c_tests/test_{filename}.py`.
- Returns: `{markdown, summary, test_code, output_path}`

#### Agent Details — Code Understanding (continued)

**Doxygen Docs (`doxygen_agent.py`)**

- Two-step agent: LLM annotation + Doxygen CLI tool execution.
- LLM adds `@brief`, `@param`, `@return`, `@file` headers to all C/C++ functions, structs, classes, enums.
- Saves annotated source to `Reports/{timestamp}/doxygen/sources/`.
- Runs `doxygen` CLI via `tools/run_doxygen.py` to generate HTML docs.
- Graceful if doxygen not installed — annotated code still returned.
- Returns: `{markdown, summary, annotated_code, doxygen_output_path, doxygen_ran}`

#### Agent Details — Security & Compliance

**Secret Scan (`secret_scan.py`)**

- Two-phase: Phase 0 regex pre-flight (12+ patterns) + Phase 3 LLM deep scan.
- Validates Phase 0 findings to filter false positives.
- Returns: `{secrets: [...], phase0_validation, narrative, summary}`

**Dependency Analysis (`dependency_analysis.py`)**

- Two-layer SCA: parses 20+ dependency file types, then runs CVE lookup + LLM risk assessment.
- Returns: `{dependencies: [...], risk_summary, remediation_plan, markdown, summary}`

**Threat Model (`threat_model.py`)**

- Two modes: Formal (STRIDE with trust boundaries, attack surface, data flow Mermaid) or Attacker Narrative (penetration tester perspective with POC).
- Receives all prior phase results (bug, static, secret, dependency).
- Returns: `{trust_boundaries, attack_surface, stride_analysis, ...}` (formal) or `{attack_scenarios, priority_ranking, ...}` (attacker)

**License Compliance (`license_compliance.py`)**

- Detects license headers, SPDX identifiers, and dependency licenses.
- Checks compatibility matrix and copyleft obligations.
- Flags missing attributions and incompatible license combinations.
- Returns: `{markdown, summary}`

#### Agent Details — Documentation & Review

**API Doc Generator (`api_doc_generator.py`)**

- Receives Phase 1 context: `flow_context` from code_flow.
- Generates full API documentation: module overview, class/function reference, usage examples.
- Returns: `{markdown, summary}`

**PR Comment Generator (`comment_generator.py`)**

- Receives merged `bug_findings + static_findings` from Phase 1.
- Calls Bedrock once with a constructive senior-engineer system prompt.
- Returns: `{comments: [{file, line, severity, body}], summary}`

#### Agent Details — Commit Analysis (5 modes)

These agents operate on git commit history, not file content. Invoked from `3_Commits.py` directly.

**Commit Analysis (`commit_analysis.py`)**

- Batches commits 20 at a time.
- If >20 commits: synthesizes batch results into a final report.
- Extracts `risk_level` by scanning markdown for "high risk" / "medium risk" / "low risk" keywords.
- Returns: `{markdown, summary, risk_level}`

**Release Notes (`release_notes.py`)**

- Transforms commit messages into polished user-facing release notes.
- Groups into: Highlights, New Features, Improvements, Bug Fixes, Breaking Changes, Other Changes.
- Batches at 30 commits; synthesizes across batches.
- Returns: `{markdown, summary}`

**Developer Activity (`developer_activity.py`)**

- Contributor breakdown, activity timeline, collaboration patterns, bus-factor risks.
- Graceful degradation: skips time/file analysis when date/files_changed fields are absent (API sources).
- Returns: `{markdown, summary}`

**Commit Hygiene (`commit_hygiene.py`)**

- Audits against Conventional Commits spec (feat:, fix:, chore:, etc.).
- Compliance scoring (grade A-D), message quality issues, squash candidates.
- Returns: `{markdown, summary}`

**Churn Analysis (`churn_analysis.py`)**

- File hotspot detection: most frequently changed files, directory-level churn, co-change patterns.
- Hard gate: requires `files_changed` data (clone source only).
- Returns: `{markdown, summary}`

#### Agent Details — Phase 5 Quick Wins

**Unit Test Generator (`unit_test_generator.py`) — F1**

- Inputs: `content`, `language`, `file_path`. Chunks large files via `chunk_file` (3 000-token budget).
- Generates language-appropriate unit tests per function: pytest (Python), JUnit 5 (Java/Kotlin), xUnit (C#/.NET), Jest (JS/TS), Catch2 (C/C++).
- Output: `Reports/<ts>/unit_tests/test_<name>.<ext>`; returns `{markdown, summary, test_code, output_path}`.
- Cache key: `unit_test_generator`.

**Story Test Generator (`story_test_generator.py`) — F2**

- Inputs: `content` + `custom_prompt` containing user stories or acceptance criteria.
- Produces BDD-style story tests (high-level Given/When/Then scenarios wired to actual functions) distinct from F3's pure Gherkin output.
- Output: `Reports/<ts>/story_tests/`; returns `{markdown, summary, test_code}`.
- Cache key: `story_test_generator`.

**Gherkin Generator (`gherkin_generator.py`) — F3**

- Inputs: `content` (source or requirements text).
- Emits pure `.feature` files with Feature/Scenario/Given/When/Then, no binding code.
- Output: `Reports/<ts>/gherkin/*.feature`; returns `{markdown, summary, features}`.
- Cache key: `gherkin_generator`.

**Test Data Generator (`test_data_generator.py`) — F8**

- Inputs: `content`, optional schema hints via `custom_prompt`.
- Generates realistic fixtures/factories (valid, edge, invalid, boundary) sized for consumption by F1/F5/F2.
- Output: `Reports/<ts>/test_data/`; returns `{markdown, summary, datasets}`.
- Cache key: `test_data_generator`.

**Dead Code Detector (`dead_code_detector.py`) — F17**

- Inputs: `content`, `language`.
- Identifies unreachable blocks, unused functions/classes/imports, always-false branches; prioritises by confidence.
- Output: structured findings list; returns `{markdown, summary, findings}`.
- Cache key: `dead_code_detector`.

**API Contract Checker (`api_contract_checker.py`) — F24**

- Inputs: `content` (implementation code) plus an OpenAPI spec provided via `custom_prompt` (`__openapi_spec__\n<YAML>`) or resolved through `tools/spec_fetcher.py`.
- Subagent/tool dependency: `tools/openapi_parser.py` (deterministic, zero-LLM) parses the spec into a canonical representation. LLM compares against implementation routes.
- Output: diff of missing/extra endpoints, param mismatches, status-code divergence.
- Cache key: `api_contract_checker`.

**OpenAPI Generator (`openapi_generator.py`) — F37**

- Inputs: `content`, `language`, `file_path`.
- Subagent/tool dependency: `tools/openapi_parser.py` for canonical shape validation of the generated YAML.
- Output: `Reports/<ts>/openapi/openapi.yaml` + markdown summary; returns `{markdown, summary, spec_yaml, output_path}`.
- Cache key: `openapi_generator`.

**Phase 5 CLI/Server Tools (not registered in `ALL_AGENTS`):**

- `tools/webhook_server.py` — F20. FastAPI server exposing a webhook endpoint that receives GitHub/Gitea push or PR events and invokes the orchestrator. Started via `python tools/webhook_server.py` (or bundled `docker/webhook_start.bat`).
- `tools/precommit_reviewer.py` — F21. CLI that hooks into `pre-commit`/`git commit` and runs a lightweight subset of agents against staged files; blocks the commit if critical findings exceed a threshold.

#### Agent Details — Phase 6 Wave 6A Spec-Driven Test Generation

**API Test Generator (`api_test_generator.py`) — F5**

- Inputs: `content` plus optional `__openapi_spec__\n<YAML>` custom_prompt prefix; language from sidebar drives framework auto-pick.
- Framework auto-pick: python→pytest+requests; java/kotlin→REST Assured+JUnit 5; csharp/c#/.net→xUnit+HttpClient; typescript/javascript→supertest+Jest; blank/other→Postman only (skips the code-mode LLM call entirely).
- Subagent/tool dependencies: `chunk_file` for large code inputs; `tools/openapi_parser.py` for spec parsing; `tools/postman_emitter.py` (zero-LLM deterministic) always emits `api_collection.json` regardless of language.
- Outputs: `Reports/<ts>/api_tests/test_api.py` (or `ApiTests.java` / `ApiTests.cs` / `api.test.ts`) and `Reports/<ts>/api_tests/api_collection.json`.
- Cache key: `api_test_generator`.

**Perf Test Generator (`perf_test_generator.py`) — F6**

- Inputs: `content` plus either `__openapi_spec__\n<YAML>` (spec mode) or `__mode__requirements\n<story>` (requirements mode); language drives framework.
- Framework auto-pick: java/scala/gatling→Gatling `Simulation.scala`; everything else→JMeter `plan.jmx`.
- Subagent/tool dependencies: `tools/load_profile_builder.py` (zero-LLM deterministic) supplies fixed VU count, ramp duration, steady-state time, think-time, and target RPS so the LLM only composes framework-specific syntax.
- Outputs: `Reports/<ts>/perf_tests/plan.jmx` or `Reports/<ts>/perf_tests/Simulation.scala`.
- Cache key: `perf_test_generator`.

**Traceability Matrix (`traceability_matrix.py`) — F10**

- Inputs: stories via `__stories__\n<text>` prefix (or auto-extracted from `content`); optional `__tests_dir__=<path>` and `__src_dir__=<path>` overrides.
- Subagent/tool dependencies: `tools/test_scanner.py` (zero-LLM deterministic) scans pytest, JUnit, xUnit, Jest, Gherkin, Robot, JMeter, and Postman tests into a canonical `{test_id, name, tags, file}` list. `_auto_scan_same_run()` walks sibling subfolders of the shared `Reports/<WAVE6A_REPORT_TS>/` to discover F5's `api_collection.json` and F6's `plan.jmx`/`Simulation.scala` without explicit paths. When `__src_dir__` resolves, F10 invokes the `run_test_coverage` subagent to flag ACs that have tests but no covered source.
- Matching: deterministic Jaccard first pass (threshold ≥ 0.7, stop-words filtered, case-insensitive) locks confident AC→test links. Ambiguous ACs (no test ≥ 0.5, OR top ∈ [0.5, 0.7), OR two candidates ≥ 0.7 within 0.1 of each other) are passed in **one batched LLM call**.
- Outputs: `Reports/<ts>/traceability/matrix.csv`, `matrix.md`, `gaps.md`.
- Cache key: `traceability_matrix`.

#### Agent Details — Phase 6 Wave 6B PR-Ready Code Patching

All 4 Wave 6B agents share `Reports/<JOB_REPORT_TS>/` and emit the same per-file artifact triple (`patches/<file>`, `patches/<file>.diff`, `pr_comment.md`, `summary.json`) through the deterministic `tools/patch_emitter.py` shared helper.

**Self-Healing Agent (`self_healing_agent.py`) — F9**

- Inputs: `content` (failing UI test source — Selenium/Playwright/Cypress); DOM via `__page_html__\n<html>` prefix or a sibling `dom.html` file; reserved `__page_url__=<url>` for future headless-browser fetch.
- Subagent/tool dependencies: 1 LLM call to the selector-rewrite subagent; `tools/patch_emitter.py` produces the diff + PR artifacts.
- Output: `Reports/<ts>/self_healing/patches/<test_file>`, matching `.diff`, `pr_comment.md`, `summary.json`.
- Cache key: `self_healing_agent`.

**Sonar Fix Agent (`sonar_fix_agent.py`) — F11**

- Inputs: `content` (the file being fixed) plus Sonar issues from one of three sources: `__sonar_issues__\n<json>` prefix, a sidecar JSON file, or a live API pull via `tools/sonar_fetcher.py`. Severity-sorted; capped by `__sonar_top_n__=<int>` (default 50).
- Subagent/tool dependencies: 1 LLM call per file being patched; `tools/sonar_fetcher.py` (optional, network-only); `tools/patch_emitter.py` for artifact emission.
- Output: `Reports/<ts>/sonar_fix/patches/<file>` + `.diff`, `pr_comment.md`, `summary.json`.
- Cache key: `sonar_fix_agent`.

**SQL Generator (`sql_generator.py`) — F14**

- Inputs: required `__prompt__\n<NL request>` + DDL schema via `__db_schema__\n<DDL|YAML>`. PostgreSQL-first, ANSI fallback, RLS-policy aware.
- Subagent/tool dependencies: `tools/ddl_parser.py` (zero-LLM; handles tables, parameterized numeric types, views, PG RLS policies); 1 LLM call to the SQL-gen subagent; `tools/patch_emitter.py` to materialize the generated SQL as a patch artifact.
- Output: `Reports/<ts>/sql_generator/patches/<query>.sql` + `.diff`, `pr_comment.md`, `summary.json`.
- Cache key: `sql_generator`.

**Auto Fix Agent (`auto_fix_agent.py`) — F15**

- Inputs: findings from Bug Analysis + Refactoring Advisor, either via `__findings__\n<json|md>` prefix or auto-scanned from same-run sidecars (`Reports/<ts>/bug_analysis/findings.json`, `Reports/<ts>/refactoring_advisor/findings.json`).
- Subagent/tool dependencies: 1 LLM call to the diff-generation subagent; `tools/patch_emitter.py` for unified diff emission. Existing-agent dependencies: `bug_analysis` and `refactoring_advisor` findings.json sidecars (Refactoring Advisor currently emits a regex-parsed markdown-table sidecar; a structured output upgrade is tracked as follow-up work).
- Output: `Reports/<ts>/auto_fix/patches/<file>` + `.diff`, `pr_comment.md`, `summary.json`.
- Cache key: `auto_fix_agent`.

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

#### `run_doxygen.py`

```python
def generate_doxyfile(source_dir: str, output_dir: str, project_name: str) -> str
def run_doxygen_tool(source_dir: str, output_dir: str, project_name: str) -> dict
```

- Generates a minimal `Doxyfile` config programmatically (no user-provided config needed).
- Runs `doxygen Doxyfile` subprocess with 120s timeout.
- Returns: `{success, output_path, error}`.
- Graceful if `doxygen` not installed: `success=False`, descriptive error.

#### `web_scraper.py`

```python
def scrape_url(url: str, timeout: int = 30) -> dict
```

- Fetches a URL via httpx with redirect following.
- Strips `<script>`, `<style>`, `<noscript>`, `<svg>` tags.
- Converts block HTML elements to newlines for readability.
- Decodes HTML entities (named, numeric, hex).
- Returns: `{url, status, title, text, length, error}`.
- CLI: `python tools/web_scraper.py <url> [-o output.txt]`

#### `openapi_parser.py` (Phase 5 subagent — zero-LLM)

Deterministic parser that loads OpenAPI/Swagger YAML or JSON into a canonical Python representation (endpoints, operations, parameters, schemas, responses). Used by F24 (`api_contract_checker`), F37 (`openapi_generator`), and F5 (`api_test_generator`) in spec mode.

#### `spec_fetcher.py` (Phase 5 — I/O)

Fetches an OpenAPI spec from a URL or file path (follows redirects, handles YAML/JSON auto-detection). Feeds the result into `openapi_parser.py`.

#### `precommit_reviewer.py` (Phase 5 — CLI entrypoint)

CLI wrapper that runs a trimmed subset of agents (bug_analysis + static_analysis + secret_scan by default) against git-staged files. Exits non-zero when critical findings exceed the configured threshold, allowing `pre-commit` to block the commit.

#### `webhook_server.py` (Phase 5 — CLI/server entrypoint)

FastAPI server listening on a configurable port. Accepts GitHub/Gitea webhook deliveries, authenticates the signature, resolves the PR/push diff, and invokes the orchestrator asynchronously. Results are written back as a PR comment when credentials allow.

#### `postman_emitter.py` (Wave 6A subagent — zero-LLM)

Deterministic Postman v2.1 collection emitter. Given a parsed OpenAPI spec (or a list of endpoints), produces a valid `api_collection.json` with per-endpoint requests, environment placeholders, and basic assertions. F5 always emits the collection regardless of the chosen code-mode framework.

#### `load_profile_builder.py` (Wave 6A subagent — zero-LLM)

Deterministic load-profile generator. Returns fixed VU count, ramp-up duration, steady-state length, think-time, and target RPS numbers keyed off endpoint count and expressed throughput. Used by F6 so the LLM only composes JMeter/Gatling syntax — load-shape decisions are not delegated to the model.

#### `test_scanner.py` (Wave 6A subagent — zero-LLM)

Deterministic multi-framework test discovery. Walks a directory and recognises pytest, JUnit, xUnit, Jest, Gherkin `.feature`, Robot Framework, JMeter `.jmx`, and Postman `.json` tests; extracts `{test_id, name, tags, file, framework}` records for F10's matching pipeline.

#### `patch_emitter.py` (Wave 6B subagent — zero-LLM, shared by all 4 Wave 6B agents)

Deterministic unified-diff + PR-artifact emitter. Pure-Python stdlib. Three operating modes: `new_content` (agent supplies the rewritten file — tool computes the diff against the original), `diff + base_content` (agent supplies both — tool reverse-applies the diff to validate it matches the base), and `base + new` (tool computes both directions). Tolerates CRLF base content (normalized), bare empty-line hunk context, `\ No newline at end of file` markers, and empty-base `@@ -0,0 @@` hunks for new files. Emits the per-file artifact quartet (`patches/<file>`, `patches/<file>.diff`, `pr_comment.md`, `summary.json`) under the target agent's `Reports/<ts>/<agent>/` folder.

#### `sonar_fetcher.py` (Wave 6B — I/O, zero-LLM, dependency-light)

F11's live SonarQube/SonarCloud REST fetcher. Stdlib `urllib` only — no external dependencies. Paginates through `/api/issues/search`, honours `Retry-After` on HTTP 429, and hands normalized issue records back to `sonar_fix_agent`. Entirely optional — F11 can run from an inline `__sonar_issues__` prefix instead.

#### `ddl_parser.py` (Wave 6B subagent — zero-LLM)

F14's regex-based DDL parser. Handles `CREATE TABLE` (including parameterized numeric types such as `NUMERIC(12,2)` and quoted identifiers), `CREATE VIEW`, and PostgreSQL row-level-security policy statements. Feeds the canonicalised schema to the SQL-gen LLM subagent so the model only has to compose the query — schema comprehension is deterministic.

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

7b. Phase 0 — Pre-flight secret scan (regex, no LLM):
    a. secret_scanner.scan_secrets() per file
    b. Action: redact secrets in content / block job / pass through

8.  Phase 1 — run in parallel (13 foundation agents):
    a. run_bug_analysis(file, ...)
       - check_cache → miss
       - chunk_by_lines(content, max_tokens=3000)
       - for each chunk: Bedrock call
       - merge + deduplicate bugs
       - write_cache + add_history
    b. run_static_analysis — linter subprocess + Bedrock semantic
    c. run_code_flow — chunk + Bedrock + synthesis if multi-chunk
    d. run_requirement — chunk + Bedrock + synthesis
    e. run_dependency_analysis — parse + CVE lookup + LLM risk
    f. run_code_complexity — complexity metrics per function
    g. run_test_coverage — test gap analysis + test skeletons
    h. run_duplication_detection — clone detection + DRY audit
    i. run_performance_analysis — Big-O + memory + scalability
    j. run_type_safety — type hint coverage + type issues
    k. run_architecture_mapper — dependency map + coupling metrics
    l. run_license_compliance — license detection + compatibility
    m. run_change_impact — blast radius + API surface analysis
    n. run_doxygen — add Doxygen headers + run doxygen CLI
    o. run_c_test_generator — generate Python pytest + ctypes tests

9.  Phase 2 — context-aware (4 agents):
    a. run_code_design(bug_results, static_results)
       - Turn 1: summarize chunks
       - Turn 2: inject Phase 1 context → JSON analysis
       - Turn 3: JSON → 9-section markdown
    b. run_mermaid(code_flow_context)
       - Single Bedrock call with diagram_type parameter
    c. run_refactoring_advisor(complexity, static, duplication results)
       - Code smells + Fowler refactoring catalogue
    d. run_api_doc_generator(code_flow_context)
       - Full API documentation generation

10. Phase 3 — synthesis:
    a. run_comment_generator(bug_findings + static_findings)
       - Single Bedrock call → PR-style comments
    b. run_secret_scan(phase0_findings + static_results)
       - LLM deep scan for what regex missed

11. Phase 4 — threat model:
    a. run_threat_model(bug, static, secret, dependency results)
       - STRIDE formal or attacker narrative mode

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

Each file in the list is processed through the full four-phase pipeline independently. Results are stored per file path.

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

### 8.1 Per-Run Artifact Layout (Reports folder)

File-generating agents (c_test_generator, doxygen, unit_test_generator, story_test_generator, gherkin_generator, test_data_generator, openapi_generator, api_test_generator, perf_test_generator, traceability_matrix, self_healing_agent, sonar_fix_agent, sql_generator, auto_fix_agent) write artifacts under a shared per-run folder. All Wave 6A + Wave 6B agents share the same `<ts>` subfolder via `JOB_REPORT_TS` (with `WAVE6A_REPORT_TS` retained as a back-compat alias):

```
Reports/<ts>/
├── c_tests/                   (c_test_generator)
├── doxygen/                   (doxygen — sources/ + html/)
├── unit_tests/                (unit_test_generator)
├── story_tests/               (story_test_generator)
├── gherkin/                   (gherkin_generator — .feature files)
├── test_data/                 (test_data_generator)
├── openapi/                   (openapi_generator — openapi.yaml)
├── api_tests/                 (api_test_generator — Wave 6A)
│   ├── test_api.py (or ApiTests.java / ApiTests.cs / api.test.ts)
│   └── api_collection.json    (always emitted via postman_emitter)
├── perf_tests/                (perf_test_generator — Wave 6A)
│   └── plan.jmx (OR Simulation.scala)
├── traceability/              (traceability_matrix — Wave 6A)
│   ├── matrix.csv
│   ├── matrix.md
│   └── gaps.md
├── self_healing/              (self_healing_agent — Wave 6B)
│   ├── patches/<test_file>
│   ├── patches/<test_file>.diff
│   ├── pr_comment.md
│   └── summary.json
├── sonar_fix/                 (sonar_fix_agent — Wave 6B)
│   ├── patches/<file>         +  patches/<file>.diff per fixed file
│   ├── pr_comment.md
│   └── summary.json
├── sql_generator/             (sql_generator — Wave 6B)
│   ├── patches/<query>.sql    +  patches/<query>.sql.diff
│   ├── pr_comment.md
│   └── summary.json
├── auto_fix/                  (auto_fix_agent — Wave 6B)
│   ├── patches/<file>         +  patches/<file>.diff per fixed file
│   ├── pr_comment.md
│   └── summary.json
├── bug_analysis/              (bug_analysis — findings.json sidecar added in Wave 6B;
│   └── findings.json           markdown output still lands under per_file/)
└── refactoring_advisor/       (refactoring_advisor — findings.json sidecar added in Wave 6B;
    └── findings.json           regex-parsed from the existing markdown table)
```

F10 auto-scans `api_tests/` and `perf_tests/` siblings of the same `<ts>` when those folders exist, so a single analysis run that selects F5 + F6 + F10 produces a fully cross-linked matrix without user intervention. F15 auto-scans `bug_analysis/findings.json` and `refactoring_advisor/findings.json` under the same `<ts>` to drive its diff generation when no explicit `__findings__` prefix is supplied.

---

## 9. Agent Gating

`ENABLED_AGENTS` is parsed at startup into a Python set of agent keys. The orchestrator and feature_selector both respect this set.

### Validation Logic

`ALL_AGENTS` currently contains **41** keys spanning Phases 1-6. The authoritative set is defined in `config/settings.py::ALL_AGENTS` — refer to that symbol rather than duplicating the list here. The membership breakdown:

| Phase | Count | Agent keys |
|---|---|---|
| Phase 1 Code Analysis | 20 | `bug_analysis`, `static_analysis`, `code_complexity`, `duplication_detection`, `type_safety`, `code_flow`, `requirement`, `code_design`, `architecture_mapper`, `mermaid`, `performance_analysis`, `refactoring_advisor`, `test_coverage`, `c_test_generator`, `change_impact`, `license_compliance`, `api_doc_generator`, `doxygen`, `comment_generator`, `dependency_analysis` |
| Phase 2 Commit Analysis | 5 | `commit_analysis`, `release_notes`, `developer_activity`, `commit_hygiene`, `churn_analysis` |
| Phase 3-4 Security | 2 | `secret_scan`, `threat_model` |
| Phase 5 Quick Wins | 7 | `unit_test_generator`, `story_test_generator`, `gherkin_generator`, `test_data_generator`, `dead_code_detector`, `api_contract_checker`, `openapi_generator` |
| Phase 6 Wave 6A | 3 | `api_test_generator`, `perf_test_generator`, `traceability_matrix` |
| Phase 6 Wave 6B | 4 | `self_healing_agent`, `sonar_fix_agent`, `sql_generator`, `auto_fix_agent` |

Note: `tools/webhook_server.py` (F20) and `tools/precommit_reviewer.py` (F21) are Phase 5 deliverables but are CLI/server entrypoints — they are **not** registered in `ALL_AGENTS` because they invoke the orchestrator themselves rather than being dispatched by it.

```python
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
| Single small file, typical 8-agent subset | 20 – 60 seconds (Bedrock latency × phases) |
| Single small file, all 41 agents | 3 – 10 minutes (dominated by Phase 1 parallel + Phase 5/6 serial) |
| Large file (chunked, all agents) | 60 – 180 seconds |
| Multi-file (10 files) | 2 – 10 minutes (sequential per file) |

### Bedrock Call Budget

Per single-file analysis (all file-mode agents selected, no cache):

| Phase | Calls |
|---|---|
| Phase 0 — secret pre-flight | 0 (regex, no LLM) |
| Phase 1 (15 foundation agents in the original pipeline + 5 later additions) | 20 × N_chunks each |
| Phase 2 — code_design | 3 (Turn 1, Turn 2, Turn 3) |
| Phase 2 — mermaid | 1 |
| Phase 2 — refactoring_advisor | 1 |
| Phase 2 — api_doc_generator | 1 |
| Phase 3 — comment_generator | 1 |
| Phase 3 — secret_scan | 1 |
| Phase 4 — threat_model | 1 |
| Phase 5 — unit_test_generator / story_test_generator / gherkin_generator / test_data_generator / dead_code_detector / api_contract_checker / openapi_generator | 1 each (7 calls, chunked for large files) |
| Phase 6 Wave 6A — api_test_generator (F5) | 1 LLM call when language is set (code-mode); **0** when language is blank (Postman-only mode) |
| Phase 6 Wave 6A — perf_test_generator (F6) | 1 LLM call (composes JMeter/Gatling syntax only; load numbers come from `load_profile_builder.py`) |
| Phase 6 Wave 6A — traceability_matrix (F10) | 1-2 LLM calls: optional AC-extraction fallback when deterministic parse fails, plus 1 batched call for ambiguous matches |
| Phase 6 Wave 6B — self_healing_agent (F9) | 1 LLM call (selector rewrite against the supplied DOM) |
| Phase 6 Wave 6B — sonar_fix_agent (F11) | 1 LLM call per file being patched, bounded by the `__sonar_top_n__` grouping (default 50) |
| Phase 6 Wave 6B — sql_generator (F14) | 1 LLM call (schema comprehension is deterministic via `ddl_parser.py`) |
| Phase 6 Wave 6B — auto_fix_agent (F15) | 1 LLM call (diff generation; findings come deterministically from sidecars or the `__findings__` prefix) |
| Total (small file, all 41 agents) | ~40 – 55 calls |

**Zero-LLM subagents:** `tools/postman_emitter.py`, `tools/load_profile_builder.py`, `tools/test_scanner.py`, `tools/openapi_parser.py`, `tools/patch_emitter.py`, `tools/sonar_fetcher.py`, and `tools/ddl_parser.py` are deterministic pipeline tools — they contribute **no** Bedrock calls to the budget. F5 always emits `api_collection.json` through `postman_emitter` for free; F6's load shape is supplied by `load_profile_builder` for free; F10's full test inventory is built by `test_scanner` for free; every Wave 6B agent (F9, F11, F14, F15) emits its PR-ready patch artifact triple through `patch_emitter` for free; F11's optional live issue pull through `sonar_fetcher` adds only network latency; F14's DDL comprehension via `ddl_parser` costs no LLM budget.

In practice, users select a subset of agents. A typical "lint + tests + auto-fix" subset (bug_analysis + static_analysis + unit_test_generator + auto_fix_agent): ~5-7 calls.

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
| Wave 6A/6B `JOB_REPORT_TS` is a process env var | Cross-agent coordination is per-process; not safe for multi-process deployments where Wave 6A/6B agents might run on different workers (`WAVE6A_REPORT_TS` retained as back-compat alias for one release) | Low |
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
