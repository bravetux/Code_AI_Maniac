# AI Code Maniac — Agent Architecture & Code Flow

**AI Code Maniac** | Updated: 2026-04-04

This document describes the internal architecture of each agent, the orchestration pipeline that coordinates them, and the detailed code flow from user action to rendered result.

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [Orchestrator Code Flow](#2-orchestrator-code-flow)
3. [Agent Execution Contract](#3-agent-execution-contract)
4. [Phase 1 Agents — Foundation (15 agents)](#4-phase-1-agents--foundation)
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
                 │          PHASE 1  —  Foundation  (15 agents, parallel)│
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
```

**Why four phases?**

- **Phase 0** is regex-based (no LLM cost) and gates subsequent analysis — secrets can be redacted from content before any LLM sees it.
- **Phase 1** agents are **independent** — they only need raw file content. Running them in parallel maximises throughput and minimises total latency.
- **Phase 2** agents are **context-enriched** — `code_design` produces higher-quality reviews when it knows which bugs and static issues already exist; `refactoring_advisor` builds on complexity and duplication findings to avoid repeating discoveries.
- **Phase 3** agents **synthesise** earlier outputs — `comment_generator` combines bug and static perspectives into a unified PR voice; `secret_scan` validates Phase 0 regex findings with LLM intelligence.
- **Phase 4** (`threat_model`) consumes the widest context — bugs, static issues, secrets, and dependencies — to produce comprehensive security assessments.

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

## 4. Phase 1 Agents — Foundation

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

## 10. Inter-Agent Data Flow

```
Phase 0: secret_scanner (regex) → redact/block/pass
                              │
                     file_hash, content, language
                              │
         ┌────────────────────▼────────────────────────────┐
         │              PHASE 1 OUTPUT (15 agents)          │
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
        ├─ "all" or "" or "*" → ALL_AGENTS (all 8)
        │
        └─ "bug_analysis,static_analysis" → {bug_analysis, static_analysis}
                                             (intersected with ALL_AGENTS)
```

Disabled agents are:
1. Hidden from the feature checkboxes in the Streamlit UI.
2. Never called by the orchestrator (condition check before each phase).
3. Not present in `result_json` (no empty placeholder entries).
