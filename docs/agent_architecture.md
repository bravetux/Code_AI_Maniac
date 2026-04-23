# AI Code Maniac — Agent Architecture & Code Flow

**AI Code Maniac** | Updated: 2026-04-22 (Wave 6B refresh)

This document describes the internal architecture of each agent, the orchestration pipeline that coordinates them, and the detailed code flow from user action to rendered result.

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [Orchestrator Code Flow](#2-orchestrator-code-flow)
3. [Agent Execution Contract](#3-agent-execution-contract)
4. [Phase 1 Agents — Foundation (20 agents)](#4-phase-1-agents--foundation)
   - 4.1 [Bug Analysis](#41-bug-analysis)
   - 4.2 [Static Analysis](#42-static-analysis)
   - 4.3 [Code Flow](#43-code-flow)
   - 4.4 [Requirement Analysis](#44-requirement-analysis)
   - 4.5 [Dependency Analysis](#45-dependency-analysis)
   - 4.6 [Code Complexity](#46-code-complexity)
   - 4.7 [Test Coverage](#47-test-coverage)
   - 4.8 [Duplication Detection](#48-duplication-detection)
   - 4.9 [Performance Analysis](#49-performance-analysis)
   - 4.10 [Type Safety](#410-type-safety)
   - 4.11 [Architecture Mapper](#411-architecture-mapper)
   - 4.12 [License Compliance](#412-license-compliance)
   - 4.13 [Change Impact](#413-change-impact)
   - 4.14 [Doxygen Docs](#414-doxygen-docs)
   - 4.15 [C Test Generator](#415-c-test-generator)
5. [Phase 2 Agents — Context-Aware (4 agents)](#5-phase-2-agents--context-aware)
   - 5.1 [Code Design (3-Turn)](#51-code-design-3-turn)
   - 5.2 [Mermaid Diagrams](#52-mermaid-diagrams)
   - 5.3 [Refactoring Advisor](#53-refactoring-advisor)
   - 5.4 [API Doc Generator](#54-api-doc-generator)
6. [Phase 3 Agents — Synthesis](#6-phase-3-agents--synthesis)
   - 6.1 [PR Comment Generator](#61-pr-comment-generator)
   - 6.2 [Secret Scan](#62-secret-scan)
7. [Phase 4 — Threat Model](#7-phase-4--threat-model)
8. [Commit Analysis Agents (5 modes)](#8-commit-analysis-agents)
   - 8.1 [Commit Analysis](#81-commit-analysis)
   - 8.2 [Release Notes](#82-release-notes)
   - 8.3 [Developer Activity](#83-developer-activity)
   - 8.4 [Commit Hygiene](#84-commit-hygiene)
   - 8.5 [Churn Analysis](#85-churn-analysis)
8A. [Phase 5 Quick Wins (7 agents + 2 CLI/server tools)](#8a-phase-5-quick-wins)
8B. [Phase 6 Wave 6A — Spec-Driven Test Generation (3 agents)](#8b-phase-6-wave-6a-spec-driven-test-generation)
8C. [Phase 6 Wave 6B — PR-Ready Code Patching (4 agents)](#8c-phase-6-wave-6b-pr-ready-code-patching)
9. [Shared Infrastructure](#9-shared-infrastructure)
   - 9.1 [Bedrock Model Factory](#91-bedrock-model-factory)
   - 9.2 [Cache Layer](#92-cache-layer)
   - 9.3 [Chunker](#93-chunker)
   - 9.4 [Linter Runner](#94-linter-runner)
   - 9.5 [Doxygen Runner](#95-doxygen-runner)
   - 9.6 [Web Scraper](#96-web-scraper)
10. [Inter-Agent Data Flow](#10-inter-agent-data-flow)
11. [End-to-End Sequence Diagram](#11-end-to-end-sequence-diagram)
12. [Agent Output Schemas](#12-agent-output-schemas)

---

## 1. Pipeline Overview

```
                        ┌─────────────────────────────────────────┐
                        │            ORCHESTRATOR                  │
                        │        agents/orchestrator.py            │
                        └────────────┬───────────────┬────────────┘
                                     │               │
                 ┌───────────────────▼───────────────▼──────────────────┐
                 │     PHASE 0  —  Pre-flight (regex, no LLM)           │
                 │     secret_scanner → redact / block / pass            │
                 └───────────────────────────┬──────────────────────────┘
                                             ▼
                 ┌──────────────────────────────────────────────────────┐
                 │   PHASE 1  —  Foundation  (15 parallel; 5 more context-aware │
                 │                             run in Phases 2 & 3 below)       │
                 │                                                        │
                 │  bug_analysis  · static_analysis · code_flow           │
                 │  requirement   · dependency_analysis                    │
                 │  code_complexity · test_coverage · duplication_detection│
                 │  performance_analysis · type_safety                     │
                 │  architecture_mapper · license_compliance               │
                 │  change_impact · doxygen · c_test_generator             │
                 └───────────────┬────────────────────────────────────────┘
                  bug  static  flow  complexity  duplication  results...
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │      PHASE 2  —  Context-Aware (4 agents)         │
                 │                                                    │
                 │  code_design        ← bug + static                │
                 │  mermaid            ← code_flow                   │
                 │  refactoring_advisor← complexity + static + dup   │
                 │  api_doc_generator  ← code_flow                   │
                 └───────────────────────────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │      PHASE 3  —  Synthesis (2 agents)             │
                 │                                                    │
                 │  comment_generator  ← bug + static findings       │
                 │  secret_scan        ← phase0 + static results     │
                 └───────────────────────────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │      PHASE 4  —  Threat Model                     │
                 │                                                    │
                 │  threat_model  ← bug + static + secret + dep      │
                 └───────────────────────────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │      PHASE 5  —  Quick Wins (7 agents)            │
                 │                                                    │
                 │  unit_test_generator (F1)  story_test_gen (F2)    │
                 │  gherkin_generator (F3)    test_data_gen (F8)     │
                 │  dead_code_detector (F17)  api_contract_chk (F24) │
                 │  openapi_generator (F37)                          │
                 │                                                    │
                 │  + CLI/server tools (not in ALL_AGENTS):          │
                 │    webhook_server.py (F20)  precommit_rev (F21)   │
                 └───────────────────────────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │      PHASE 6 WAVE 6A — Spec-Driven Tests          │
                 │                                                    │
                 │  ┌─ set JOB_REPORT_TS at run_analysis() start ────┐│
                 │  │ (WAVE6A_REPORT_TS retained as back-compat alias)│
                 │  │ api_test_generator (F5) → api_tests/           ││
                 │  │   ├─ test_api.py (or .java/.cs/.ts)            ││
                 │  │   └─ api_collection.json (postman_emitter)     ││
                 │  │                                                 ││
                 │  │ perf_test_generator (F6) → perf_tests/          ││
                 │  │   └─ plan.jmx OR Simulation.scala               ││
                 │  │       (load shape from load_profile_builder)    ││
                 │  │                                                 ││
                 │  │ traceability_matrix (F10) → traceability/       ││
                 │  │   ├─ matrix.csv / matrix.md / gaps.md           ││
                 │  │   ├─ _auto_scan_same_run(<ts>) ← scans siblings ││
                 │  │   └─ test_scanner.py walks all frameworks       ││
                 │  └─ all three write under Reports/<shared ts>/ ────┘│
                 └───────────────────────────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │   PHASE 6 WAVE 6B — PR-Ready Code Patching        │
                 │                                                    │
                 │  ┌─ same Reports/<JOB_REPORT_TS>/ folder as 6A ──┐│
                 │  │                                                 ││
                 │  │ self_healing_agent (F9)  → self_healing/        ││
                 │  │   DOM via __page_html__ or sibling dom.html     ││
                 │  │                                                 ││
                 │  │ sonar_fix_agent (F11)    → sonar_fix/           ││
                 │  │   issues via prefix / sidecar / sonar_fetcher   ││
                 │  │                                                 ││
                 │  │ sql_generator (F14)      → sql_generator/       ││
                 │  │   DDL schema → ddl_parser → NL→SQL LLM call     ││
                 │  │                                                 ││
                 │  │ auto_fix_agent (F15)     → auto_fix/            ││
                 │  │   ▲                                             ││
                 │  │   │ reads findings.json sidecars from:          ││
                 │  │   ├─ Reports/<ts>/bug_analysis/                 ││
                 │  │   └─ Reports/<ts>/refactoring_advisor/          ││
                 │  │                                                 ││
                 │  │ every agent → tools/patch_emitter.py (shared)   ││
                 │  │   emits patches/<file>, .diff, pr_comment.md,   ││
                 │  │   summary.json per file under its subfolder     ││
                 │  └─────────────────────────────────────────────────┘│
                 └───────────────────────────────────────────────────┘
```

**Why six phases (and why split Wave 6A from Wave 6B)?**

- **Phase 0** is regex-based (no LLM cost) and gates subsequent analysis — secrets can be redacted from content before any LLM sees it.
- **Phase 1** agents are **independent** — they only need raw file content. Running them in parallel maximises throughput and minimises total latency.
- **Phase 2** agents are **context-enriched** — `code_design` produces higher-quality reviews when it knows which bugs and static issues already exist; `refactoring_advisor` builds on complexity and duplication findings to avoid repeating discoveries.
- **Phase 3** agents **synthesise** earlier outputs — `comment_generator` combines bug and static perspectives into a unified PR voice; `secret_scan` validates Phase 0 regex findings with LLM intelligence.
- **Phase 4** (`threat_model`) consumes the widest context — bugs, static issues, secrets, and dependencies — to produce comprehensive security assessments.
- **Phase 5** adds post-baseline "quick win" generators (tests, fixtures, OpenAPI, dead-code sweep, contract checking). They are registered in `ALL_AGENTS` and dispatched by the orchestrator; two companion tools (`webhook_server.py`, `precommit_reviewer.py`) are CLI/server entrypoints that invoke the orchestrator from outside the UI.
- **Phase 6 Wave 6A** is spec-driven test generation. F5/F6/F10 share a single `Reports/<ts>/` folder via the `JOB_REPORT_TS` process env var (formerly `WAVE6A_REPORT_TS`, retained as a back-compat alias for one release) set once at `run_analysis()` entry. F10 leverages this to auto-discover F5's `api_collection.json` and F6's `plan.jmx`/`Simulation.scala` siblings without explicit paths. Deterministic subagents (`postman_emitter`, `load_profile_builder`, `test_scanner`) take load-shape, collection-emission, and test-discovery decisions out of the LLM's hands.
- **Phase 6 Wave 6B** is the PR-ready code-patching wave. F9 (self-healing selectors), F11 (Sonar fixes), F14 (NL→SQL), and F15 (auto-fix from findings) are separated from Wave 6A because the concerns are orthogonal: Wave 6A *generates tests* — its outputs are greenfield files that no reviewer has to approve line-by-line. Wave 6B *modifies existing production code* — every artifact is a unified diff that a human reviewer must sign off on, so the four agents share a different contract (deterministic diff emission via `tools/patch_emitter.py`, per-file `pr_comment.md`, machine-readable `summary.json`). All four share the same `Reports/<JOB_REPORT_TS>/` folder as Wave 6A so that multi-wave runs stay coherent, and F15 specifically auto-reads the `findings.json` sidecars that `bug_analysis` and `refactoring_advisor` write into that same folder.

---

## 2. Orchestrator Code Flow

```
run_analysis(job_id)
│
├─ update_job_status(job_id, "running")
│
├─ job = get_job(job_id)
│
├─ _fetch_files(job)
│    ├─ Parse source_ref by source_type:
│    │    local  → split on "::" → [fetch_local_file(path, start, end), ...]
│    │    github → fetch_github_file(repo, path, branch, token, start, end)
│    │    gitea  → fetch_gitea_file(url, repo, path, branch, token, start, end)
│    └─ For each file:
│         detect_language(file_path)   ← if job.language is None
│         return {file_path, content, file_hash, language}
│
├─ For each file in file_list (up to MAX_FILES):
│    │
│    ├─ PHASE 1 (parallel execution)
│    │    ├─ "bug_analysis"    in features  → run_bug_analysis(...)
│    │    ├─ "static_analysis" in features  → run_static_analysis(...)
│    │    ├─ "code_flow"       in features  → run_code_flow(...)
│    │    └─ "requirement"     in features  → run_requirement(...)
│    │
│    ├─ Collect: bug_results, static_results, flow_ctx
│    │
│    ├─ PHASE 2
│    │    ├─ "code_design" in features
│    │    │    → run_code_design(..., bug_results=bug_results,
│    │    │                           static_results=static_results)
│    │    └─ "mermaid" in features
│    │         → run_mermaid(..., code_flow_ctx=flow_ctx,
│    │                           mermaid_type=job.mermaid_type)
│    │
│    └─ PHASE 3
│         └─ "comment_generator" in features
│              → run_comment_generator(..., bug_results=bug_results,
│                                          static_results=static_results)
│
├─ Merge per-file results:
│    single file → results[feature] = result
│    multi-file  → results[feature] = {_multi_file: True, files: {path: result}}
│
├─ save_job_results(job_id, results)
└─ update_job_status(job_id, "completed")
```

---

## 3. Agent Execution Contract

Every agent function follows this pattern:

```python
def run_<feature>(
    file_path: str,
    content: str,
    file_hash: str,
    language: str,
    custom_prompt: str | None,
    job_id: str,
    conn,
    **kwargs,
) -> dict:

    # 1. Check cache
    cached = check_cache(file_hash, feature, language, custom_prompt)
    if cached:
        return cached

    # 2. Prepare context
    model = make_bedrock_model()
    chunks = chunk_by_lines(content, max_tokens=<budget>)

    # 3. Run agent logic (may involve multiple Bedrock calls)
    result = <agent-specific logic>

    # 4. Store result
    write_cache(job_id, feature, file_hash, language, custom_prompt, result)
    add_history(job_id, feature, file_path, language, result.get("summary", ""))

    return result
```

**Cache key** = SHA-256(file_hash + ":" + feature + ":" + language + ":" + custom_prompt)

A cache hit returns the stored result immediately, with no Bedrock call and no history record.

---

## 4. Phase 1 Agents — Foundation (20 agents)

Phase 1 Code Analysis spans 20 agents total. The subsections below detail the 15 foundation-parallel agents; the remaining 5 (`code_design`, `mermaid`, `refactoring_advisor`, `api_doc_generator`, `comment_generator`) are context-aware and documented in sections 5 and 6 — they are still part of the Phase 1 Code Analysis bucket in `ALL_AGENTS`.

### 4.1 Bug Analysis

**File:** `agents/bug_analysis.py`  
**Model role:** Senior software engineer performing production code review

```
run_bug_analysis(file_path, content, file_hash, language, custom_prompt, job_id, conn)
│
├─ check_cache → hit: return early
│
├─ chunk_by_lines(content, max_tokens=3000)
│    → [{content, start_line, end_line, token_count}, ...]
│
├─ For each chunk:
│    ├─ Build system prompt (senior engineer persona + JSON output schema)
│    ├─ Append custom_prompt if provided
│    ├─ Bedrock call via Strands Agent
│    └─ Parse JSON response:
│         [{line, severity, description, runtime_impact, root_cause,
│           suggestion, github_comment}, ...]
│
├─ Merge bugs from all chunks
│    └─ Deduplicate by (line, description[:50])
│
├─ Build result:
│    {bugs: [...], narrative: "...", summary: "X critical, Y major, Z minor"}
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

**Output structure:**

```json
{
  "bugs": [
    {
      "line": 42,
      "severity": "critical",
      "description": "Null pointer dereference — user object not validated",
      "runtime_impact": "Crashes on any unauthenticated request",
      "root_cause": "Missing guard before .get() call",
      "suggestion": "Add `if user is None: raise AuthError` before line 42",
      "github_comment": "**Critical:** `user.get('id')` will raise `AttributeError`..."
    }
  ],
  "narrative": "Overall code quality: ...",
  "summary": "2 critical, 1 major, 3 minor bugs found"
}
```

---

### 4.2 Static Analysis

**File:** `agents/static_analysis.py`  
**Model role:** Static analysis expert: design patterns, security, performance

```
run_static_analysis(file_path, content, file_hash, language, custom_prompt, job_id, conn)
│
├─ check_cache → hit: return early
│
├─ LAYER 1 — Mechanical Linting
│    └─ run_linter(file_path, language)
│         ├─ Python → flake8 subprocess
│         │    parse: "path:line:col: CODE message"
│         │    → [{line, col, code, message, tool:"flake8"}, ...]
│         ├─ JS/TS  → eslint subprocess (--format json)
│         │    parse: JSON array → [{line, col, ruleId, message, tool:"eslint"}, ...]
│         └─ Other → {findings: [], skipped: True}
│
├─ LAYER 2 — LLM Semantic Analysis
│    ├─ Build prompt:
│    │    system: "Two-layer static analysis expert"
│    │    user:   linter_findings (JSON) + full file content
│    ├─ Bedrock call
│    └─ Parse JSON response:
│         [{line, category, severity, description, suggestion}, ...]
│         category: design_smell | security | performance |
│                   maintainability | concurrency | error_handling
│
├─ Build result:
│    {linter_findings: [...], semantic_findings: [...],
│     narrative: "...", linter_skipped: bool, summary: "..."}
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

---

### 4.3 Code Flow

**File:** `agents/code_flow.py`  
**Model role:** Technical documentation writer for new team members

```
run_code_flow(file_path, content, file_hash, language, custom_prompt, job_id, conn)
│
├─ check_cache → hit: return early
│
├─ chunk_by_lines(content, max_tokens=4000, overlap_lines=5)
│
├─ If single chunk:
│    └─ Bedrock call → markdown execution flow
│
├─ If multiple chunks:
│    ├─ For each chunk: Bedrock call → partial flow narrative
│    └─ Synthesis call:
│         prompt: "Given these partial analyses, produce a single coherent flow"
│         input:  all partial narratives concatenated
│         output: unified markdown
│
├─ Build result:
│    {markdown: "...", summary: first_sentence,
│     entry_points: [...], steps: [...]}
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

The `code_flow` result is passed to `mermaid` in Phase 2, avoiding a second content-comprehension call to Bedrock.

---

### 4.4 Requirement Analysis

**File:** `agents/requirement.py`  
**Model role:** Business analyst reverse-engineering requirements from source code

```
run_requirement(file_path, content, file_hash, language, custom_prompt, job_id, conn)
│
├─ check_cache → hit: return early
│
├─ chunk_by_lines(content, max_tokens=4000)
│
├─ For each chunk:
│    ├─ Bedrock call → markdown with REQ-NNN items
│    └─ Extract requirements list from response
│
├─ If multiple chunks:
│    └─ Synthesis + renumbering:
│         Combine all requirements → renumber REQ-001, REQ-002, ...
│         Re-run Bedrock to produce clean unified document
│
├─ Build result:
│    {markdown: "...", summary: "N functional, M non-functional requirements",
│     requirements: [{id, type, description, source_line, rationale}]}
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

**Sample requirement record:**

```json
{
  "id": "REQ-007",
  "type": "functional",
  "description": "The system shall validate user tokens on every API call",
  "source_line": 88,
  "rationale": "Inferred from auth middleware applied to all routes"
}
```

---

### 4.5 Dependency Analysis

**File:** `agents/dependency_analysis.py`
**Cache key:** `dependency_analysis`

Two-layer SCA approach:
1. **Parser layer** — `tools/dependency_parser.py` extracts packages from 20+ dependency file types (requirements.txt, package.json, pom.xml, go.mod, Cargo.toml, etc.)
2. **LLM analysis layer** — Bedrock evaluates risk, maps CVEs, and produces remediation guidance.

**Output:** `{dependencies: [...], risk_summary, remediation_plan, markdown, summary}`

---

### 4.6 Code Complexity

**File:** `agents/code_complexity.py`
**Cache key:** `code_complexity`

Analyses cyclomatic complexity, cognitive complexity, and maintainability index per function. Identifies the top 3-5 most complex functions as hotspots with concrete simplification suggestions.

**Key sections in output:** Summary Metrics table, Per-Function Breakdown table, Complexity Hotspots with refactoring suggestions, Patterns of Concern, Recommendations.

**Output:** `{markdown, summary}`

---

### 4.7 Test Coverage

**File:** `agents/test_coverage.py`
**Cache key:** `test_coverage`

Analyses code structure to identify untested functions, missing test cases, and testability issues. Does NOT run tests — it performs static analysis of what SHOULD be tested.

**Key sections:** Testability Assessment, Functions & Methods Inventory with test priority, Missing Test Cases (happy path, edge cases, error cases), Untestable Code, Suggested Test Skeleton in the detected language, Recommendations.

**Output:** `{markdown, summary}`

---

### 4.8 Duplication Detection

**File:** `agents/duplication_detection.py`
**Cache key:** `duplication_detection`

Finds exact duplicates, near-duplicates (structural clones), and repeated patterns. Distinguishes harmful duplication from acceptable repetition.

**Key sections:** Duplication Summary with DRY Score, Exact Duplicates, Near-Duplicates with similarity percentage, Repeated Patterns, Refactoring Suggestions (Extract Function, Base Class, Template Method, Strategy Pattern), Recommendations ordered by lines saved.

**Output:** `{markdown, summary}`

---

### 4.9 Performance Analysis

**File:** `agents/performance_analysis.py`
**Cache key:** `performance_analysis`

Analyses algorithmic complexity, memory usage, I/O efficiency, and scalability.

**Key sections:** Performance Summary table (algorithmic/memory/I/O/concurrency/caching ratings), Algorithmic Analysis (Big-O per function), Performance Issues (N+1, unbounded loops, resource leaks), Memory Analysis, Caching Opportunities, Scalability Assessment (10x, 100x, 1000x input growth), Recommendations by impact-to-effort ratio.

**Output:** `{markdown, summary}`

---

### 4.10 Type Safety

**File:** `agents/type_safety.py`
**Cache key:** `type_safety`

Type hint coverage audit. Language-aware: adapts to Python (PEP 484+), TypeScript strict mode, Java generics, etc.

**Key sections:** Type Coverage Summary (grade A-D), Untyped Functions table with priority, Type Issues (missing returns, broad Any types, mutable defaults), Type Improvement Suggestions with full signatures, Advanced Type Patterns (TypeVar, Protocol, TypedDict, Literal, Overload), Recommendations.

**Output:** `{markdown, summary}`

---

### 4.11 Architecture Mapper

**File:** `agents/architecture_mapper.py`
**Cache key:** `architecture_mapper`

Maps module dependencies, coupling metrics, and architectural patterns.

**Key sections:** Module Overview (responsibility, layer, patterns), Dependency Map (imports table with coupling assessment + exports), Dependency Analysis (afferent/efferent coupling, instability metric, abstractness), Layer Violations (circular deps, layer skipping, upward deps, God modules), Mermaid Component Diagram, Cohesion Assessment, Recommendations.

**Output:** `{markdown, summary}`

---

### 4.12 License Compliance

**File:** `agents/license_compliance.py`
**Cache key:** `license_compliance`

Detects license headers, SPDX identifiers, and dependency licenses. Checks compatibility.

**Key sections:** License Detection (file-level + dependency-level), License Compatibility Matrix (copyleft propagation, distribution implications), Compliance Issues (GPL in proprietary, missing attribution, no-license packages), Attribution Requirements table, Policy Recommendations.

**Output:** `{markdown, summary}`

---

### 4.13 Change Impact

**File:** `agents/change_impact.py`
**Cache key:** `change_impact`

Estimates blast radius for code modifications.

**Key sections:** Impact Overview (API surface, coupling points, blast radius rating, change confidence), Public API Surface table (stability, change risk), Dependency Chain Analysis (downstream/upstream), Change Scenarios (2-4 specific scenarios: adding parameter, changing return type, removing function), Side Effect Map, Safe Change Zones, Test Impact Assessment, Recommendations.

**Output:** `{markdown, summary}`

---

### 4.14 Doxygen Docs

**File:** `agents/doxygen_agent.py`
**Cache key:** `doxygen`

Two-step agent: LLM annotation + Doxygen CLI tool execution.

1. **LLM step:** Bedrock adds `@brief`, `@param`, `@return`, `@file`, `@note`, `@warning` headers to every function, struct, class, enum, macro, and typedef in C/C++ code. Original code preserved byte-for-byte.
2. **Tool step:** Saves annotated source to `Reports/{timestamp}/doxygen/sources/`. Generates a minimal `Doxyfile` via `tools/run_doxygen.py` and runs `doxygen` CLI to produce HTML docs at `Reports/{timestamp}/doxygen/html/`.

Graceful degradation: if `doxygen` CLI is not installed, the annotated code is still returned.

**Output:** `{markdown, summary, annotated_code, doxygen_output_path, doxygen_ran}`

---

### 4.15 C Test Generator

**File:** `agents/c_test_generator.py`
**Cache key:** `c_test_generator`

Takes C source code and generates a complete Python `pytest` + `ctypes` test file.

- Defines `argtypes`/`restype` for type-safe bindings per function
- Generates one test class per public C function with: happy path, boundary values, negative input, zero input, large input, NULL pointer handling, error return codes
- Includes build instruction comment (`gcc -shared -fPIC -o lib.so file.c`)
- Includes a `__main__` block for direct execution
- Saves test file to `Reports/{timestamp}/c_tests/test_{filename}.py`

**Output:** `{markdown, summary, test_code, output_path}`

---

## 5. Phase 2 Agents — Context-Aware

### 5.1 Code Design (3-Turn)

**File:** `agents/code_design.py`  
**Model role:** Principal architect conducting a design review

This is the most complex agent. It uses a **3-turn multi-message conversation** pattern with Bedrock to progressively deepen understanding before producing a design document.

```
run_code_design(file_path, content, file_hash, language, custom_prompt,
                job_id, conn, bug_results, static_results)
│
├─ check_cache → hit: return early
│
├─ ─────────────────────────────────────────────────
│  TURN 1 — UNDERSTAND
│  Budget: 6 000 tokens per chunk
│  Goal: Build structural understanding of the code
│  ─────────────────────────────────────────────────
│  ├─ chunk_by_lines(content, max_tokens=6000)
│  ├─ If single chunk:
│  │    Bedrock call: "Summarize the structure of this code"
│  │    → structural_notes (free-form text)
│  └─ If multiple chunks:
│       For each chunk: Bedrock call → section_summary
│       Synthesis call: combine section_summaries → structural_notes
│
├─ ─────────────────────────────────────────────────
│  TURN 2 — ANALYSE
│  Goal: Produce structured JSON design analysis
│  ─────────────────────────────────────────────────
│  ├─ Build prompt:
│  │    history: [Turn 1 user + assistant messages]
│  │    new user message:
│  │      "Based on your understanding above, and given these findings:
│  │       Bug findings: {bug_results}
│  │       Static findings: {static_results}
│  │       Produce a structured JSON design analysis."
│  ├─ Bedrock call (continues conversation)
│  ├─ Parse JSON response:
│  │    {title, purpose, design_assessment, design_issues,
│  │     public_api, dependencies, data_contracts, improvements}
│  └─ On parse failure → early return with raw response as markdown
│
├─ ─────────────────────────────────────────────────
│  TURN 3 — DOCUMENT
│  Goal: Produce 9-section markdown design document
│  ─────────────────────────────────────────────────
│  ├─ Build prompt:
│  │    history: [T1, T2 messages]
│  │    new user message:
│  │      "Using your analysis, write a comprehensive design document
│  │       with these 9 sections: [section list]"
│  ├─ Bedrock call (continues conversation)
│  ├─ Capture markdown output
│  └─ On exception → return T2 structured fields, design_document: ""
│
├─ Build result:
│    {title, purpose, design_document (markdown),
│     markdown (alias), design_assessment, design_issues,
│     public_api, improvements, dependencies}
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

**3-Turn Conversation Diagram:**

```
User: "Here is the code. Summarize its structure."
   │
   ▼
Assistant (T1): "This file implements an authentication service with..."
   │
   ▼
User: "Given your understanding and these bug/static findings,
       produce a structured JSON design analysis."
   │
   ▼
Assistant (T2): { "title": "AuthService", "design_issues": [...], ... }
   │
   ▼
User: "Using your analysis, write a 9-section design document."
   │
   ▼
Assistant (T3): "# AuthService Design Document\n## Executive Summary\n..."
```

**9 Document Sections:**
1. Executive Summary
2. Architecture Overview
3. Responsibilities & Scope
4. Interface & Public API
5. Data Flow
6. Design Decisions & Rationale
7. Known Issues & Technical Debt
8. Improvement Roadmap
9. Dependencies

---

### 5.2 Mermaid Diagrams

**File:** `agents/mermaid.py`  
**Model role:** Diagram specialist producing valid Mermaid syntax

```
run_mermaid(file_path, content, file_hash, language, custom_prompt,
            job_id, conn, code_flow_ctx, mermaid_type)
│
├─ check_cache → hit: return early
│
├─ Determine input context:
│    if code_flow_ctx is available:
│      Use code_flow_ctx as input (avoids a second content-comprehension call)
│    else:
│      Use raw file content
│
├─ Build prompt:
│    system: "Mermaid diagram specialist"
│    user:   "{diagram_type} diagram from this code/flow"
│             diagram_type: flowchart | sequence | class
│
├─ Bedrock call
├─ Parse JSON response:
│    {diagram_type, mermaid_source, description}
│    Validate mermaid_source starts with diagram keyword
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

**Output:**

```json
{
  "diagram_type": "flowchart",
  "mermaid_source": "flowchart TD\n  A[Start] --> B{Validate}\n  B -->|ok| C[Process]\n  B -->|fail| D[Error]",
  "description": "Main execution path showing validation branching"
}
```

---

### 5.3 Refactoring Advisor

**File:** `agents/refactoring_advisor.py`
**Cache key:** `refactoring_advisor`

**Dependencies from Phase 1:**
- `complexity_results` — from `code_complexity` (identifies hotspots to focus on)
- `static_results` — from `static_analysis` (design smells already found)
- `duplication_results` — from `duplication_detection` (DRY violations to address)

Identifies code smells from Martin Fowler's catalogue and recommends specific refactoring patterns. Provides before/after code sketches for the top 5-8 most impactful smells.

**Smells detected:** Long Method, God Class, Feature Envy, Data Clumps, Primitive Obsession, Switch/If Chains, Shotgun Surgery, Divergent Change, Dead Code, Deep Nesting, Magic Numbers, Long Parameter List, Speculative Generality, Message Chains, Inappropriate Intimacy.

**Key sections:** Code Smell Inventory table, Detailed Refactoring Recommendations (with before/after code), Design Pattern Opportunities, Quick Wins, Refactoring Roadmap (prioritised by impact-to-effort).

**Context usage:** Prior analysis results are appended to the prompt (truncated to 2000 chars each) with instructions to build on — not repeat — earlier findings.

**Output:** `{markdown, summary}`

---

### 5.4 API Doc Generator

**File:** `agents/api_doc_generator.py`
**Cache key:** `api_doc_generator`

**Dependencies from Phase 1:**
- `flow_context` — from `code_flow` (execution order understanding)

Generates comprehensive, polished API documentation suitable as official module docs.

**Key sections:** Module Overview, Quick Start example, API Reference (Classes with constructors/attributes/methods, Functions with params/returns/raises/examples, Constants, Type Definitions), Error Handling, Usage Examples (3-5 complete examples), Notes & Caveats.

**Output:** `{markdown, summary}`

---

## 6. Phase 3 Agents — Synthesis

### 6.1 PR Comment Generator

**File:** `agents/comment_generator.py`  
**Model role:** Thoughtful senior engineer writing constructive GitHub PR review comments

```
run_comment_generator(file_path, content, file_hash, language, custom_prompt,
                      job_id, conn, bug_results, static_results)
│
├─ check_cache → hit: return early
│
├─ Aggregate findings:
│    bug_findings    = bug_results.get("bugs", [])
│    static_findings = static_results.get("semantic_findings", [])
│                    + static_results.get("linter_findings", [])
│
├─ If no findings: return empty result early
│
├─ Build prompt:
│    system: "Senior engineer writing constructive PR review comments.
│             Not a linting bot. Be thoughtful and collegial."
│    user:   bug_findings (JSON) + static_findings (JSON)
│             "Produce PR-style review comments for each issue."
│
├─ Bedrock call
├─ Parse JSON response:
│    {comments: [{file, line, severity, body}], summary: "..."}
│
├─ write_cache(...)
├─ add_history(...)
└─ return result
```

**Output:**

```json
{
  "comments": [
    {
      "file": "src/auth.py",
      "line": 42,
      "severity": "critical",
      "body": "**Critical:** This will raise `AttributeError` at runtime when `user` is `None`. Consider adding a guard:\n```python\nif user is None:\n    raise AuthenticationError('User not found')\n```"
    }
  ],
  "summary": "**Must fix:** 2 critical issues. Code structure is clean overall, good separation of concerns."
}
```

---

### 6.2 Secret Scan

**File:** `agents/secret_scan.py`
**Cache key:** `secret_scan`

**Dependencies:** Phase 0 pre-flight findings + `static_results`

Two-phase secret detection:
1. **Phase 0 (Pre-flight):** Regex scanning via `tools/secret_scanner.py` — 12+ patterns for AWS keys, GitHub tokens, JWTs, connection strings, etc. Runs before any LLM sees the code.
2. **Phase 3 (Deep):** LLM analysis for what regex misses — base64-encoded secrets, split secrets, hardcoded fallbacks, env var fallbacks with literal defaults, secrets in comments/docstrings.

Validates Phase 0 findings to filter false positives.

**Output:** `{secrets: [...], phase0_validation, narrative, summary}`

---

## 7. Phase 4 — Threat Model

**File:** `agents/threat_model.py`
**Cache key:** `threat_model`

**Dependencies:** bug + static + secret + dependency results from all prior phases.

Two modes:
- **Formal Mode:** STRIDE methodology with trust boundaries, attack surface mapping, and data flow Mermaid diagram. Returns `{trust_boundaries, attack_surface, stride_analysis, data_flow_mermaid}`.
- **Attacker Mode:** Penetration tester narrative with realistic attack scenarios, prerequisites, proof-of-concept sketches, and mitigation. Returns `{executive_summary, attack_scenarios, priority_ranking}`.

---

## 8. Commit Analysis Agents (5 modes)

These agents operate on **git commit history** rather than file content. They are invoked from `3_Commits.py` directly, not through the standard orchestrator pipeline. The Commits page provides a mode selector to choose between 5 analysis types.

**Common pattern:** All commit agents use the same signature: `run_<name>(conn, job_id, repo_ref, commits, custom_prompt) → dict`. They batch commits, call Bedrock per batch, and synthesise across batches if needed.

### 8.1 Commit Analysis

**File:** `agents/commit_analysis.py`
**Batch size:** 20

Engineering lead reviewing commits for release readiness. Produces Commit Quality review, Changelog synthesis, Risk Assessment, and Recommendations. Extracts `risk_level` (high/medium/low) from markdown keywords.

**Output:** `{markdown, summary, risk_level}`

### 8.2 Release Notes

**File:** `agents/release_notes.py`
**Batch size:** 30

Transforms commit messages into polished, user-facing release notes. Groups into: Highlights, New Features, Improvements, Bug Fixes, Breaking Changes, Other Changes.

**Output:** `{markdown, summary}`

### 8.3 Developer Activity

**File:** `agents/developer_activity.py`
**Batch size:** 30

Contributor breakdown, activity timeline, collaboration patterns, bus-factor risks. **Graceful degradation:** inspects first commit for `date`/`files_changed` keys — if absent, prepends notes to the prompt skipping time-based or file-ownership analysis.

**Output:** `{markdown, summary}`

### 8.4 Commit Hygiene

**File:** `agents/commit_hygiene.py`
**Batch size:** 20

Audits commits against Conventional Commits spec. Compliance scoring (grade A-D), message quality issues, squash candidates, large commits (if file data available).

**Output:** `{markdown, summary}`

### 8.5 Churn Analysis

**File:** `agents/churn_analysis.py`
**Batch size:** 30

File hotspot detection: most frequently changed files, directory-level churn, co-change patterns, stability report. **Hard gate:** requires `files_changed` data (only from GitHub Clone source). Returns early with instructive message if data is absent.

**Output:** `{markdown, summary}`

---

## 8A. Phase 5 Quick Wins

Seven agents (registered in `ALL_AGENTS`) + two CLI/server tools (intentionally not in `ALL_AGENTS`). All seven agents follow the same execution contract as Phase 1 agents (cache-first, `resolve_prompt` for append/overwrite handling, `write_cache` + `add_history` on miss). Framework/language choices are driven by the sidebar `language` field.

### 8A.1 Unit Test Generator (F1)

**File:** `agents/unit_test_generator.py`
**Purpose:** Per-function unit test generation in the idiomatic framework for the detected language.
**Inputs:** `content`, `language`, `file_path`, `custom_prompt`.
**Prompts used:** Framework-specific system prompt (pytest for Python, JUnit 5 for Java/Kotlin, xUnit for C#/.NET, Jest for JS/TS, Catch2 for C/C++).
**Tools consumed:** `chunk_file.chunk_by_lines(max_tokens=3000)` for large files.
**Outputs:** `Reports/<ts>/unit_tests/test_<name>.<ext>`; returns `{markdown, summary, test_code, output_path}`.
**Typical invocation:** Sidebar checkbox "Unit Test Generator" with language set.

### 8A.2 Story Test Generator (F2)

**File:** `agents/story_test_generator.py`
**Purpose:** BDD-style story tests wired to actual functions (distinct from F3's pure Gherkin).
**Inputs:** `content` + user stories / acceptance criteria in `custom_prompt`.
**Prompts used:** Given/When/Then narrative prompt with binding-code guidance.
**Tools consumed:** None LLM-adjacent.
**Outputs:** `Reports/<ts>/story_tests/`; returns `{markdown, summary, test_code}`.
**Typical invocation:** Sidebar + user stories pasted into extra instructions.

### 8A.3 Gherkin Generator (F3)

**File:** `agents/gherkin_generator.py`
**Purpose:** Emits pure `.feature` files (Feature/Scenario/Given/When/Then) without binding code.
**Inputs:** `content` (source or requirements text).
**Prompts used:** Gherkin-style requirement extraction prompt.
**Tools consumed:** None.
**Outputs:** `Reports/<ts>/gherkin/*.feature`; returns `{markdown, summary, features}`.
**Typical invocation:** Sidebar checkbox; commonly co-selected with F10 for matrix input.

### 8A.4 Test Data Generator (F8)

**File:** `agents/test_data_generator.py`
**Purpose:** Realistic fixture/factory datasets (valid, edge, invalid, boundary).
**Inputs:** `content`; optional schema hints in `custom_prompt`.
**Prompts used:** Dataset synthesis prompt with diversity constraints.
**Tools consumed:** None.
**Outputs:** `Reports/<ts>/test_data/`; returns `{markdown, summary, datasets}`.
**Typical invocation:** Sidebar; output feeds F1 and F5 consumers.

### 8A.5 Dead Code Detector (F17)

**File:** `agents/dead_code_detector.py`
**Purpose:** Unreachable block + unused function/class/import sweep with confidence ranking.
**Inputs:** `content`, `language`.
**Prompts used:** Unreachability heuristics prompt with language-aware examples.
**Tools consumed:** None.
**Outputs:** `{markdown, summary, findings}` — no file artifacts, results rendered in a Streamlit tab.
**Typical invocation:** Sidebar checkbox.

### 8A.6 API Contract Checker (F24)

**File:** `agents/api_contract_checker.py`
**Purpose:** Diffs an OpenAPI spec against implementation routes — missing endpoints, extra endpoints, parameter/status-code mismatches.
**Inputs:** `content` (implementation); spec via `__openapi_spec__\n<YAML>` prefix or URL fetched by `tools/spec_fetcher.py`.
**Prompts used:** Contract-diff prompt; LLM compares canonicalised spec to route inventory.
**Tools consumed:** `tools/openapi_parser.py` (zero-LLM), `tools/spec_fetcher.py` (I/O).
**Outputs:** `{markdown, summary, diffs}`.
**Typical invocation:** Sidebar + spec URL/YAML in extra instructions.

### 8A.7 OpenAPI Generator (F37)

**File:** `agents/openapi_generator.py`
**Purpose:** Infers an OpenAPI 3.x YAML spec from API handler code.
**Inputs:** `content`, `language`, `file_path`.
**Prompts used:** OpenAPI schema synthesis prompt with strict YAML-only output constraint.
**Tools consumed:** `tools/openapi_parser.py` for canonical-shape validation of the generated YAML.
**Outputs:** `Reports/<ts>/openapi/openapi.yaml`; returns `{markdown, summary, spec_yaml, output_path}`.
**Typical invocation:** Sidebar checkbox.

### 8A.8 CLI/Server Tool Entrypoints (F20, F21 — not in `ALL_AGENTS`)

- **`tools/webhook_server.py` (F20).** FastAPI server exposing a webhook endpoint. Receives GitHub/Gitea push or PR events, authenticates the signature, resolves the changed-file diff, and calls the orchestrator. Started via `python tools/webhook_server.py` or the bundled `docker/webhook_start.bat`. Not an agent — it invokes the orchestrator rather than being dispatched by it.
- **`tools/precommit_reviewer.py` (F21).** CLI wrapper that runs a trimmed subset of agents (bug_analysis + static_analysis + secret_scan by default) against git-staged files and exits non-zero when critical findings exceed the threshold. Used as a `pre-commit` hook command.

---

## 8B. Phase 6 Wave 6A Spec-Driven Test Generation

All three agents share a single `Reports/<ts>/` run folder via the `JOB_REPORT_TS` environment variable (set once per `run_analysis(conn, job_id)` call by the orchestrator). Each agent reads the timestamp via the shared `_report_ts()` helper with fallback chain `JOB_REPORT_TS` → `WAVE6A_REPORT_TS` (back-compat alias for one release) → `datetime.now()`.

### 8B.1 API Test Generator (F5)

**File:** `agents/api_test_generator.py`
**Purpose:** Framework-auto-picked API tests plus a deterministic Postman v2.1 collection.
**Inputs:** `content`; optional `__openapi_spec__\n<YAML>` spec prefix; sidebar `language` drives framework selection.
**Prompts used:** Framework-specific API test prompt (pytest+requests, REST Assured+JUnit 5, xUnit+HttpClient, supertest+Jest). Postman-only path skips the LLM entirely when language is blank.
**Tools consumed:** `chunk_file` (large inputs), `tools/openapi_parser.py` (spec mode), `tools/postman_emitter.py` (always — zero-LLM deterministic subagent).
**Outputs:**
```
Reports/<ts>/api_tests/
├── test_api.py (or ApiTests.java / ApiTests.cs / api.test.ts)
└── api_collection.json
```
Returns `{markdown, summary, test_code, output_paths}`.
**Subagent structure:** 0 or 1 LLM calls (0 in Postman-only mode) + 1 deterministic Postman emit.
**Typical invocation:** Sidebar checkbox; often co-selected with F10 so the matrix picks up `api_collection.json` automatically.

### 8B.2 Perf Test Generator (F6)

**File:** `agents/perf_test_generator.py`
**Purpose:** JMeter `plan.jmx` (default) or Gatling `Simulation.scala` (java/scala/gatling) from a spec or requirement narrative.
**Inputs:** `content` + either `__openapi_spec__\n<YAML>` (spec mode) or `__mode__requirements\n<story>` (requirements mode).
**Prompts used:** Framework-specific load-plan composition prompt. Crucially, the prompt does **not** ask the LLM to decide VU count, ramp, or RPS — those come from `load_profile_builder.py`. The LLM's job is limited to framework syntax.
**Tools consumed:** `tools/openapi_parser.py` (spec mode), `tools/load_profile_builder.py` (always — zero-LLM deterministic subagent that returns `{vus, ramp_s, steady_s, think_ms, target_rps}`).
**Outputs:** `Reports/<ts>/perf_tests/plan.jmx` OR `Reports/<ts>/perf_tests/Simulation.scala`; returns `{markdown, summary, plan_code, output_path}`.
**Subagent structure:** 1 LLM call + 1 deterministic load-profile build.
**Typical invocation:** Sidebar checkbox; spec or story in extra instructions.

### 8B.3 Traceability Matrix (F10)

**File:** `agents/traceability_matrix.py`
**Purpose:** Maps acceptance criteria (ACs) from user stories to discovered tests; flags gaps.
**Inputs:** `__stories__\n<text>` for AC source; optional `__tests_dir__=<path>` override; optional `__src_dir__=<path>` to enable coverage-aware gap analysis.
**Prompts used:** Batched ambiguous-match prompt (one call for all ambiguous ACs); fallback AC-extraction prompt if deterministic parse fails.
**Tools consumed:** `tools/test_scanner.py` (zero-LLM — walks pytest/JUnit/xUnit/Jest/Gherkin/Robot/JMeter/Postman); `run_test_coverage` subagent when `__src_dir__` resolves; `_auto_scan_same_run(<JOB_REPORT_TS>)` to discover sibling `api_tests/` and `perf_tests/` folders.
**Matching algorithm:**
1. Deterministic Jaccard (threshold ≥ 0.7, stop-words filtered, case-insensitive) — locks confident matches.
2. Ambiguous ACs (spec §6.2 step 4: no test ≥ 0.5, OR top ∈ [0.5, 0.7), OR two ≥ 0.7 within 0.1 of each other) are passed in **one** batched LLM call.
**Outputs:**
```
Reports/<ts>/traceability/
├── matrix.csv
├── matrix.md
└── gaps.md
```
Returns `{markdown, summary, matrix, gaps}`.
**Subagent structure:** 0-2 LLM calls + deterministic scanner + optional coverage subagent.
**Typical invocation:** Sidebar checkbox with stories pasted into extra instructions; commonly co-selected with F5/F6 for full same-run traceability.

---

## 8C. Phase 6 Wave 6B PR-Ready Code Patching

Four agents dispatched from the sidebar UI that share the same `Reports/<JOB_REPORT_TS>/` folder as Wave 6A. Every agent follows the same output contract: the deterministic `tools/patch_emitter.py` shared helper writes a per-file artifact quartet — `patches/<file>` (rewritten content), `patches/<file>.diff` (unified diff), `pr_comment.md` (reviewer-facing), `summary.json` (machine-readable). The LLM's job in every Wave 6B agent is narrow: produce the new content or a diff; all PR-artifact materialisation is deterministic.

### 8C.1 Self-Healing Agent (F9)

**File:** `agents/self_healing_agent.py`
**Purpose:** Rewrites broken UI test selectors (Selenium, Playwright, Cypress) against a supplied DOM snapshot so flaky tests can self-heal after front-end changes.
**Inputs:** `content` (the failing UI test source); DOM via `__page_html__\n<html>` prefix or a sibling `dom.html` next to the test file; reserved `__page_url__=<url>` for a future headless-browser fetch integration.
**Prompts used:** Selector-rewrite prompt — the LLM is shown the original selector + surrounding test code + DOM and asked for the most stable equivalent selector.
**LLM subagent count:** 1.
**Pipeline-tool subagents:** `tools/patch_emitter.py` (shared Wave 6B diff emitter).
**Outputs:** `Reports/<ts>/self_healing/` with the standard patch quartet per rewritten test.
**Interaction with `patch_emitter`:** `new_content` mode — the agent hands patch_emitter the rewritten test source and lets it compute the diff from the original.

### 8C.2 Sonar Fix Agent (F11)

**File:** `agents/sonar_fix_agent.py`
**Purpose:** Ingests SonarQube/SonarCloud issues and emits per-file fixes as PR-ready patches.
**Inputs:** `content` (the file being fixed) plus Sonar issues sourced from one of `__sonar_issues__\n<json>` prefix, a sidecar JSON file, or a live API pull via `tools/sonar_fetcher.py`. Severity-sorted and capped by `__sonar_top_n__=<int>` (default 50).
**Prompts used:** Per-file fix prompt — one file and its issue cluster are handed to the LLM at a time; the LLM produces the corrected file content.
**LLM subagent count:** 1 per file being patched (bounded by the top-N grouping).
**Pipeline-tool subagents:** `tools/sonar_fetcher.py` (optional, dependency-light — stdlib `urllib`, paginates, handles 429 Retry-After); `tools/patch_emitter.py`.
**Outputs:** `Reports/<ts>/sonar_fix/` with a patch quartet per fixed file.
**Interaction with `patch_emitter`:** `new_content` mode per file.

### 8C.3 SQL Generator (F14)

**File:** `agents/sql_generator.py`
**Purpose:** Natural-language → SQL generation with DDL-parsed schema context. PostgreSQL-first, ANSI fallback, RLS-policy aware.
**Inputs:** Required `__prompt__\n<NL request>` plus DDL schema via `__db_schema__\n<DDL|YAML>`.
**Prompts used:** SQL-synthesis prompt that receives the canonicalised schema (tables, columns with parameterised numeric types, views, PG RLS policies) and the natural-language request.
**LLM subagent count:** 1.
**Pipeline-tool subagents:** `tools/ddl_parser.py` (zero-LLM regex DDL parser); `tools/patch_emitter.py`.
**Outputs:** `Reports/<ts>/sql_generator/` with `patches/<query>.sql` + `.diff`, `pr_comment.md`, `summary.json`.
**Interaction with `patch_emitter`:** `new_content` mode — the generated SQL is materialised as a new file artifact so reviewers can diff it against an empty base (or an existing query file when editing).

### 8C.4 Auto Fix Agent (F15)

**File:** `agents/auto_fix_agent.py`
**Purpose:** Consumes Bug Analysis + Refactoring Advisor findings and emits a unified diff that addresses them.
**Inputs:** Findings via `__findings__\n<json|md>` prefix OR — when the prefix is absent — auto-scanned from same-run sidecars at `Reports/<ts>/bug_analysis/findings.json` and `Reports/<ts>/refactoring_advisor/findings.json`.
**Prompts used:** Diff-generation prompt — the LLM receives the original file content + the aggregated findings and is asked to emit a unified diff that resolves them.
**LLM subagent count:** 1.
**Pipeline-tool subagents:** `tools/patch_emitter.py` in `diff + base_content` mode — the LLM's diff is handed back with the base file; patch_emitter reverse-applies the diff to validate it against the base before committing the artifact quartet.
**Existing-agent subagents:** `bug_analysis` (findings.json sidecar) + `refactoring_advisor` (findings.json sidecar; currently a regex-parsed markdown-table sidecar — a structured-output upgrade is tracked as follow-up work).
**Outputs:** `Reports/<ts>/auto_fix/` with the standard patch quartet.
**Interaction with `patch_emitter`:** `diff + base_content` mode so the emitter can detect malformed diffs and fall back gracefully (tolerates CRLF bases, bare empty-line hunk context, `\ No newline at end of file` markers, and empty-base `@@ -0,0 @@` hunks).

---

## 9. Shared Infrastructure

### 9.1 Bedrock Model Factory

**File:** `agents/_bedrock.py`

```python
def make_bedrock_model() -> BedrockModel:
    s = get_settings()
    session_kwargs = {"region_name": s.aws_region}
    if s.aws_access_key_id:
        session_kwargs["aws_access_key_id"] = s.aws_access_key_id
        session_kwargs["aws_secret_access_key"] = s.aws_secret_access_key
    if s.aws_session_token:
        session_kwargs["aws_session_token"] = s.aws_session_token
    boto_session = boto3.Session(**session_kwargs)
    return BedrockModel(
        model_id=s.bedrock_model_id,
        temperature=s.bedrock_temperature,
        boto_session=boto_session,
    )
```

Each agent call creates a fresh `BedrockModel` instance. The Strands `Agent` class wraps the model with a system prompt and manages the conversation turn history.

---

### 9.2 Cache Layer

**Files:** `tools/cache.py`, `db/queries/cache.py`

```
compute_cache_key(file_hash, feature, language, custom_prompt)
  → SHA256( file_hash + ":" + feature + ":" + language + ":" + (custom_prompt or "") )
  → hex string (64 chars)

check_cache(file_hash, feature, language, custom_prompt)
  → key = compute_cache_key(...)
  → SELECT result_json FROM results_cache WHERE file_hash = ?
  → Found: return dict (deserialized JSON)
  → Not found: return None

write_cache(job_id, feature, file_hash, language, custom_prompt, result)
  → key = compute_cache_key(...)
  → INSERT INTO results_cache (id, job_id, feature, file_hash, language, result_json)
```

Cache misses trigger the full agent execution path. Cache hits skip all Bedrock calls.

---

### 9.3 Chunker

**File:** `tools/chunk_file.py`

```python
def chunk_by_lines(content: str, max_tokens: int = 3000, overlap_lines: int = 0) -> list[dict]:
```

**Algorithm:**

```
lines = content.split("\n")
current_chunk_lines = []
current_tokens = 0
chunks = []

for line in lines:
    line_tokens = len(line) // 4   # approximate token count
    if current_tokens + line_tokens > max_tokens and current_chunk_lines:
        chunks.append(build_chunk(current_chunk_lines, ...))
        if overlap_lines > 0:
            current_chunk_lines = current_chunk_lines[-overlap_lines:]
            current_tokens = sum(len(l) // 4 for l in current_chunk_lines)
        else:
            current_chunk_lines = []
            current_tokens = 0
    current_chunk_lines.append(line)
    current_tokens += line_tokens

if current_chunk_lines:
    chunks.append(build_chunk(current_chunk_lines, ...))

return chunks
```

Each chunk dict: `{content: str, start_line: int, end_line: int, token_count: int}`

**Token budgets used by agents:**

| Agent | `max_tokens` | `overlap_lines` |
|---|---|---|
| bug_analysis | 3 000 | 0 |
| code_flow | 4 000 | 5 |
| requirement | 4 000 | 0 |
| code_design T1 | 6 000 | 0 |

---

### 9.4 Linter Runner

**File:** `tools/run_linter.py`

```
run_linter(file_path, language)
│
├─ language == "Python"
│    └─ _run_flake8(file_path)
│         subprocess: ["flake8", file_path]
│         parse stdout line by line:
│           pattern: r"(.+):(\d+):(\d+): ([A-Z]\d+) (.+)"
│           → {line, col, code, message, tool: "flake8"}
│
├─ language in ("JavaScript", "TypeScript")
│    └─ _run_eslint(file_path)
│         subprocess: ["eslint", "--format", "json", file_path]
│         parse JSON output array:
│           messages[].line, messages[].column,
│           messages[].ruleId, messages[].message
│           → {line, col, code, message, tool: "eslint"}
│
└─ other language
     → {findings: [], skipped: True, reason: "Unsupported language: {language}"}
```

If the linter binary is not found: `skipped: True, reason: "flake8 not found"`.

---

### 9.5 Doxygen Runner

**File:** `tools/run_doxygen.py`

```
generate_doxyfile(source_dir, output_dir, project_name)
│
└─ Writes minimal Doxyfile to output_dir/Doxyfile
   Configured for: C/C++/C# file patterns, EXTRACT_ALL=YES,
   HTML output only, no LaTeX, QUIET mode

run_doxygen_tool(source_dir, output_dir, project_name)
│
├─ Calls generate_doxyfile()
├─ subprocess: ["doxygen", doxyfile_path]  (timeout: 120s)
│
├─ Success: {success: True, output_path: ".../html/index.html"}
├─ doxygen not installed: {success: False, error: "doxygen is not installed..."}
└─ Timeout: {success: False, error: "doxygen timed out after 120 seconds"}
```

---

### 9.6 Web Scraper

**File:** `tools/web_scraper.py`

Standalone tool for extracting clean text content from any URL. Usable as CLI script or importable module.

```
scrape_url(url, timeout=30)
│
├─ httpx.Client(follow_redirects=True)
├─ GET url with User-Agent header
│
├─ Strip <script>, <style>, <noscript>, <svg>, <head> tags
├─ Convert <br>, </p>, </div>, </h1-6>, </li> to newlines
├─ Remove remaining HTML tags
├─ Decode HTML entities (named + numeric + hex)
├─ Collapse whitespace
│
├─ Success: {url, status: 200, title, text, length, error: ""}
├─ HTTP error: {url, status: 4xx/5xx, error: "HTTP 404: Not Found"}
└─ Connection error: {url, status: 0, error: "..."}
```

**CLI usage:**
```bash
python tools/web_scraper.py https://example.com
python tools/web_scraper.py https://example.com -o output.txt
```

---

### 9.7 Phase 5, Wave 6A, and Wave 6B Tools

Ten tools were added post-baseline. The table separates zero-LLM deterministic subagents (safe to depend on without Bedrock budget impact) from I/O tools (network/filesystem side effects).

| Tool | Role | LLM-free? | One-line description |
|---|---|---|---|
| `tools/openapi_parser.py` | Subagent | Yes | Parses OpenAPI/Swagger YAML/JSON into a canonical Python representation; consumed by F5, F24, F37 |
| `tools/spec_fetcher.py` | I/O | Yes (LLM-free, but does HTTP) | Fetches an OpenAPI spec from URL/file, auto-detects YAML vs JSON, feeds `openapi_parser.py` |
| `tools/precommit_reviewer.py` | CLI entrypoint | N/A (invokes agents that call Bedrock) | Git pre-commit hook — runs a trimmed agent subset against staged files and blocks on critical findings |
| `tools/webhook_server.py` | Server entrypoint | N/A (invokes orchestrator) | FastAPI webhook receiver for GitHub/Gitea push/PR events; dispatches to the orchestrator |
| `tools/postman_emitter.py` | Subagent | Yes | Deterministic Postman v2.1 collection emitter; F5 uses it every run |
| `tools/load_profile_builder.py` | Subagent | Yes | Deterministic VU/ramp/steady/think-time/RPS numbers for F6; keeps load-shape decisions out of the LLM |
| `tools/test_scanner.py` | Subagent | Yes | Multi-framework test discovery (pytest, JUnit, xUnit, Jest, Gherkin, Robot, JMeter, Postman); F10's canonical test inventory |
| `tools/patch_emitter.py` | Subagent | Yes | **Shared by all 4 Wave 6B agents.** Deterministic unified-diff + PR-artifact emitter. Three modes: `new_content`, `diff + base_content` (reverse-apply-validated), `base + new` (computes diff). Tolerates CRLF bases, bare empty-line hunk context, `\ No newline at end of file` markers, empty-base `@@ -0,0 @@` hunks |
| `tools/sonar_fetcher.py` | I/O | Yes (LLM-free, dependency-light — stdlib `urllib` only) | F11 live Sonar issue fetcher. Paginates `/api/issues/search`, honours `Retry-After` on HTTP 429, no external dependencies |
| `tools/ddl_parser.py` | Subagent | Yes | F14 regex DDL parser. Handles `CREATE TABLE` (including parameterised numeric types like `NUMERIC(12,2)`), views, PostgreSQL row-level-security policies |

---

## 10. Inter-Agent Data Flow

```
Phase 0: secret_scanner (regex) → redact/block/pass
                              │
                     file_hash, content, language
                              │
         ┌────────────────────▼────────────────────────────┐
         │   PHASE 1 OUTPUT (15 parallel foundation agents)  │
         │                                                   │
         │  bug_results ─── static_results ─── flow_ctx     │
         │  requirement ─── dependency_analysis              │
         │  complexity ──── duplication ──── performance     │
         │  type_safety ─── architecture ─── license        │
         │  change_impact ── doxygen ── c_test_generator     │
         └────────────────────┬────────────────────────────┘
                              │
     ┌────────┬───────────────┼───────────────┬────────────┐
     │        │               │               │            │
     ▼        ▼               ▼               ▼            ▼
  code_design  mermaid   refactoring     api_doc_gen
  (bug+static) (flow)   (complexity+    (flow)
   3-turn               static+dup)
                              │
                              ▼
              ┌───────────────┼──────────────────┐
              │               │                  │
              ▼               ▼                  ▼
        comment_gen      secret_scan         threat_model
        (bug+static)     (phase0+static)     (bug+static+
                                              secret+dep)
```

**Dependency summary table:**

| Agent | Phase | Receives From |
|---|---|---|
| code_design | 2 | bug_results, static_results |
| mermaid | 2 | flow_context (code_flow) |
| refactoring_advisor | 2 | complexity_results, static_results, duplication_results |
| api_doc_generator | 2 | flow_context (code_flow) |
| comment_generator | 3 | bug_results, static_results |
| secret_scan | 3 | phase0_findings, static_results |
| threat_model | 4 | bug_results, static_results, secret_results, dependency_results |
| unit_test_generator (F1) | 5 | raw `content` only; shares `chunk_file` pathway with F5 |
| api_contract_checker (F24) | 5 | `content` + OpenAPI spec via `openapi_parser.py` |
| openapi_generator (F37) | 5 | `content`; validates output via `openapi_parser.py` |
| api_test_generator (F5) | 6 Wave 6A | `content` (+ optional `__openapi_spec__` YAML); always emits via `postman_emitter.py`; shares `chunk_file` with F1 |
| perf_test_generator (F6) | 6 Wave 6A | `content` (+ `__openapi_spec__` or `__mode__requirements`); load shape from `load_profile_builder.py` |
| traceability_matrix (F10) | 6 Wave 6A | `__stories__` ACs + `test_scanner.py` inventory of sibling `api_tests/` (F5's `api_collection.json`) and `perf_tests/` (F6's `plan.jmx`/`Simulation.scala`); optionally calls `run_test_coverage` subagent when `__src_dir__` resolves |
| self_healing_agent (F9) | 6 Wave 6B | `content` + DOM via `__page_html__` (or sibling `dom.html`); emits via `tools/patch_emitter.py` to `Reports/<ts>/self_healing/` |
| sonar_fix_agent (F11) | 6 Wave 6B | `content` + Sonar issues via `__sonar_issues__` / sidecar / live `tools/sonar_fetcher.py` (optional); `__sonar_top_n__` cap; emits via `patch_emitter` to `Reports/<ts>/sonar_fix/` |
| sql_generator (F14) | 6 Wave 6B | `__prompt__` + `__db_schema__` parsed by `tools/ddl_parser.py`; emits via `patch_emitter` to `Reports/<ts>/sql_generator/` |
| auto_fix_agent (F15) | 6 Wave 6B | `__findings__` prefix OR sidecars `Reports/<ts>/bug_analysis/findings.json` + `Reports/<ts>/refactoring_advisor/findings.json`; emits via `patch_emitter` (`diff + base_content` mode) to `Reports/<ts>/auto_fix/` |

**Specific cross-dependencies called out:**

- **F10 consumes F5 + F6 via `test_scanner.py`.** Because all three Wave 6A agents share `JOB_REPORT_TS` (with `WAVE6A_REPORT_TS` retained as a back-compat alias), F10's `_auto_scan_same_run()` walks sibling subfolders of `Reports/<shared_ts>/` and picks up F5's `api_collection.json` and F6's `plan.jmx` / `Simulation.scala` without an explicit `__tests_dir__` override.
- **F10 → `run_test_coverage` subagent.** When `__src_dir__=<path>` resolves to a directory, F10 invokes the existing Phase 1 `test_coverage` agent internally to enrich gap analysis with source-coverage data.
- **F1 and F5 both use `chunk_file`.** Large files hit the same chunker with a 3 000-token budget for unit tests and a similar budget for API tests.
- **F37 and F24 both use `tools/openapi_parser.py`.** F37 validates its generated YAML; F24 canonicalises the reference spec before diffing.
- **All 4 Wave 6B agents share `tools/patch_emitter.py`.** Every PR-ready artifact quartet (`patches/<file>`, `patches/<file>.diff`, `pr_comment.md`, `summary.json`) is produced by the same deterministic helper — no agent hand-rolls diff formatting.
- **F15 auto-scans Bug Analysis + Refactoring Advisor sidecars via `JOB_REPORT_TS`.** Bug Analysis and Refactoring Advisor now write a structured `findings.json` next to their existing markdown output (the Refactoring Advisor sidecar is regex-parsed from its markdown table — structured output is tracked as follow-up). F15's auto-scan walks `Reports/<shared_ts>/bug_analysis/` and `Reports/<shared_ts>/refactoring_advisor/` so co-selecting F15 with the two findings agents produces a fully wired-up patch run without any `__findings__` prefix.
- **All 7 multi-wave agents (3 Wave 6A + 4 Wave 6B) share `Reports/<JOB_REPORT_TS>/`.** The orchestrator sets `JOB_REPORT_TS` once at `run_analysis()` entry; every consuming agent reads it via `_report_ts()` with the fallback chain `JOB_REPORT_TS` → `WAVE6A_REPORT_TS` → `datetime.now()`.

---

## 11. End-to-End Sequence Diagram

```
User         Streamlit UI        Orchestrator     Phase 1 Agents    Bedrock     DuckDB
 │                │                   │                 │               │           │
 │─ Configure ───▶│                   │                 │               │           │
 │  + Run         │                   │                 │               │           │
 │                │─ create_job ──────────────────────────────────────────────────▶│
 │                │◀─ job_id ─────────────────────────────────────────────────────│
 │                │─ spawn thread ───▶│                 │               │           │
 │                │                   │─ status=running ──────────────────────────▶│
 │                │                   │─ _fetch_files ─▶│               │           │
 │                │                   │◀─ file list ────│               │           │
 │                │                   │                 │               │           │
 │                │                   │─ run_bug ──────▶│               │           │
 │                │                   │─ run_static ───▶│               │           │  ← parallel
 │                │                   │─ run_flow ─────▶│               │           │
 │                │                   │─ run_req ──────▶│               │           │
 │                │                   │                 │               │           │
 │                │                   │                 │─ check_cache ─────────────▶│
 │                │                   │                 │◀─ miss ───────────────────│
 │                │                   │                 │─ Bedrock call ───────────▶│
 │                │                   │                 │◀─ result ─────────────────│
 │                │                   │                 │─ write_cache + history ───▶│
 │                │                   │◀─ P1 results ───│               │           │
 │                │                   │                 │               │           │
 │                │                   │─ run_code_design ──────────────▶│           │
 │                │                   │  (T1 → T2 → T3 Bedrock calls)  │           │
 │                │                   │─ run_mermaid ───────────────────▶│          │
 │                │                   │◀─ P2 results ───────────────────│           │
 │                │                   │                 │               │           │
 │                │                   │─ run_comment_gen ───────────────▶│          │
 │                │                   │◀─ P3 results ───────────────────│           │
 │                │                   │                 │               │           │
 │                │                   │─ save_results ────────────────────────────▶│
 │                │                   │─ status=completed ─────────────────────────▶│
 │                │                   │                 │               │           │
 │  ← poll 2s ───│                   │                 │               │           │
 │                │─ get_job ─────────────────────────────────────────────────────▶│
 │                │◀─ status=completed ───────────────────────────────────────────│
 │                │─ get_results ─────────────────────────────────────────────────▶│
 │                │◀─ results dict ───────────────────────────────────────────────│
 │                │                   │                 │               │           │
 │◀─ render tabs ─│                   │                 │               │           │
```

---

## 12. Agent Output Schemas

### Bug Analysis

```json
{
  "bugs": [
    {
      "line": 42,
      "severity": "critical | major | minor",
      "description": "string",
      "runtime_impact": "string",
      "root_cause": "string",
      "suggestion": "string",
      "github_comment": "markdown string"
    }
  ],
  "narrative": "string — overall assessment",
  "summary": "string — e.g. '2 critical, 1 major'"
}
```

### Static Analysis

```json
{
  "linter_findings": [
    {"line": 10, "col": 5, "code": "E501", "message": "line too long", "tool": "flake8"}
  ],
  "semantic_findings": [
    {
      "line": 22,
      "category": "security | design_smell | performance | maintainability | concurrency | error_handling",
      "severity": "critical | major | minor",
      "description": "string",
      "suggestion": "string"
    }
  ],
  "narrative": "string",
  "linter_skipped": false,
  "summary": "string"
}
```

### Code Flow

```json
{
  "markdown": "string — full execution flow document",
  "summary": "string — first sentence",
  "entry_points": ["function_name_1", "function_name_2"],
  "steps": ["step 1 description", "step 2 description"]
}
```

### Requirement Analysis

```json
{
  "markdown": "string — requirements document with REQ-NNN format",
  "summary": "string — e.g. '5 functional, 2 non-functional'",
  "requirements": [
    {
      "id": "REQ-001",
      "type": "functional | non-functional",
      "description": "string",
      "source_line": 88,
      "rationale": "string"
    }
  ]
}
```

### Code Design

```json
{
  "title": "string — component name",
  "purpose": "string — one paragraph",
  "design_document": "string — 9-section markdown",
  "markdown": "string — alias for design_document",
  "design_assessment": "string — strengths vs weaknesses",
  "design_issues": [
    {
      "issue": "string",
      "impact": "string",
      "recommendation": "string"
    }
  ],
  "public_api": [
    {"name": "string", "signature": "string", "description": "string"}
  ],
  "dependencies": ["string"],
  "data_contracts": ["string"],
  "improvements": ["string — prioritized recommendation"]
}
```

### Mermaid

```json
{
  "diagram_type": "flowchart | sequence | class",
  "mermaid_source": "string — valid Mermaid syntax",
  "description": "string — what the diagram shows"
}
```

### PR Comment Generator

```json
{
  "comments": [
    {
      "file": "string — file path",
      "line": 42,
      "severity": "critical | major | minor | suggestion",
      "body": "string — full markdown review comment"
    }
  ],
  "summary": "string — top-level PR review summary"
}
```

### New Code Analysis Agents (all share markdown pattern)

The following agents all return the same base schema:

```json
{
  "markdown": "string — full markdown report",
  "summary": "string — one-line description"
}
```

Applies to: `code_complexity`, `test_coverage`, `duplication_detection`, `performance_analysis`, `type_safety`, `architecture_mapper`, `license_compliance`, `change_impact`, `refactoring_advisor`, `api_doc_generator`

### Doxygen Docs

```json
{
  "markdown": "string — annotated code display + paths",
  "summary": "string — e.g. 'Added Doxygen headers to file.c. HTML docs generated.'",
  "annotated_code": "string — full C/C++ source with Doxygen comment headers",
  "doxygen_output_path": "string — path to generated html/index.html",
  "doxygen_ran": true
}
```

### C Test Generator

```json
{
  "markdown": "string — test code display + paths",
  "summary": "string — e.g. 'Generated 12 pytest+ctypes tests for math_utils.c'",
  "test_code": "string — full Python pytest file content",
  "output_path": "string — path to saved test file in Reports/"
}
```

### Commit Analysis

```json
{
  "markdown": "string — full report with Commit Quality, Changelog, Risk Assessment, Recommendations",
  "summary": "string — e.g. '12 commits analysed'",
  "risk_level": "high | medium | low"
}
```

### Commit Agents (shared pattern)

The following commit agents all return the same schema:

```json
{
  "markdown": "string — full markdown report",
  "summary": "string — one-line description"
}
```

Applies to: `release_notes`, `developer_activity`, `commit_hygiene`, `churn_analysis`

---

## Agent Gating Reference

```
ENABLED_AGENTS env var
        │
        ▼
config/settings.py → Settings.enabled_agents (string)
        │
        ▼
orchestrator.py / feature_selector.py
        │
        ├─ "all" or "" or "*" → ALL_AGENTS (all 41 — see config/settings.py::ALL_AGENTS)
        │
        └─ "bug_analysis,static_analysis" → {bug_analysis, static_analysis}
                                             (intersected with ALL_AGENTS)
```

Disabled agents are:
1. Hidden from the feature checkboxes in the Streamlit UI.
2. Never called by the orchestrator (condition check before each phase).
3. Not present in `result_json` (no empty placeholder entries).

`ALL_AGENTS` currently holds **41** keys across Phase 1 Code Analysis (20), Phase 2 Commit Analysis (5), Phase 3-4 Security (2), Phase 5 Quick Wins (7), Phase 6 Wave 6A (3), and Phase 6 Wave 6B (4). The `webhook_server.py` (F20) and `precommit_reviewer.py` (F21) entrypoints are Phase 5 deliverables but intentionally **not** members of `ALL_AGENTS` — they invoke the orchestrator rather than being dispatched by it.
