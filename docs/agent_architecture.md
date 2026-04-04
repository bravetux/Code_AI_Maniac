# AI Arena — Agent Architecture & Code Flow

**AG-UC-1128** | Updated: 2026-04-04

This document describes the internal architecture of each agent, the orchestration pipeline that coordinates them, and the detailed code flow from user action to rendered result.

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [Orchestrator Code Flow](#2-orchestrator-code-flow)
3. [Agent Execution Contract](#3-agent-execution-contract)
4. [Phase 1 Agents — Foundation](#4-phase-1-agents--foundation)
   - 4.1 [Bug Analysis](#41-bug-analysis)
   - 4.2 [Static Analysis](#42-static-analysis)
   - 4.3 [Code Flow](#43-code-flow)
   - 4.4 [Requirement Analysis](#44-requirement-analysis)
5. [Phase 2 Agents — Context-Aware](#5-phase-2-agents--context-aware)
   - 5.1 [Code Design (3-Turn)](#51-code-design-3-turn)
   - 5.2 [Mermaid Diagrams](#52-mermaid-diagrams)
6. [Phase 3 Agents — Synthesis](#6-phase-3-agents--synthesis)
   - 6.1 [PR Comment Generator](#61-pr-comment-generator)
7. [Special Agent — Commit Analysis](#7-special-agent--commit-analysis)
8. [Shared Infrastructure](#8-shared-infrastructure)
   - 8.1 [Bedrock Model Factory](#81-bedrock-model-factory)
   - 8.2 [Cache Layer](#82-cache-layer)
   - 8.3 [Chunker](#83-chunker)
   - 8.4 [Linter Runner](#84-linter-runner)
9. [Inter-Agent Data Flow](#9-inter-agent-data-flow)
10. [End-to-End Sequence Diagram](#10-end-to-end-sequence-diagram)
11. [Agent Output Schemas](#11-agent-output-schemas)

---

## 1. Pipeline Overview

```
                        ┌─────────────────────────────────────────┐
                        │            ORCHESTRATOR                  │
                        │        agents/orchestrator.py            │
                        └────────────┬───────────────┬────────────┘
                                     │               │
                 ┌───────────────────▼───────────────▼──────────────────┐
                 │          PHASE 1  —  Foundation  (Parallel)           │
                 │                                                        │
                 │  ┌──────────────┐  ┌──────────────┐                  │
                 │  │ bug_analysis  │  │static_analysis│                  │
                 │  └──────────────┘  └──────────────┘                  │
                 │  ┌──────────────┐  ┌──────────────┐                  │
                 │  │  code_flow   │  │  requirement  │                  │
                 │  └──────────────┘  └──────────────┘                  │
                 └───────────────┬────────────────────────────────────┘
                   bug_results   │   static_results   code_flow_ctx
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │        PHASE 2  —  Context-Aware (Sequential)     │
                 │                                                    │
                 │  ┌───────────────────────┐  ┌──────────────────┐ │
                 │  │  code_design           │  │  mermaid         │ │
                 │  │  (receives P1 context) │  │  (reuses flow)   │ │
                 │  └───────────────────────┘  └──────────────────┘ │
                 └───────────────────────────────────────────────────┘
                   bug_results + static_results
                                 ▼
                 ┌───────────────────────────────────────────────────┐
                 │        PHASE 3  —  Synthesis                      │
                 │                                                    │
                 │  ┌─────────────────────────────────────────────┐  │
                 │  │  comment_generator  (aggregates P1 findings) │  │
                 │  └─────────────────────────────────────────────┘  │
                 └───────────────────────────────────────────────────┘
```

**Why three phases?**

- Phase 1 agents are **independent** — they only need raw file content. Running them in parallel maximises throughput and minimises total latency.
- Phase 2 agents are **context-enriched** — `code_design` produces higher-quality reviews when it knows which bugs and static issues already exist (it can frame them as design symptoms rather than isolated mistakes).
- Phase 3 agent **synthesises** Phase 1 outputs — `comment_generator` produces better PR comments by combining both bug and static perspectives into a unified voice.

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

## 7. Special Agent — Commit Analysis

**File:** `agents/commit_analysis.py`  
**Model role:** Engineering lead reviewing commit history for release readiness

This agent operates on **git commit history** rather than file content. It is invoked from `3_Commits.py` directly, not through the standard orchestrator pipeline.

```
run_commit_analysis(commits, repo_id, custom_prompt, job_id, conn)
│
  commits = [{sha, message, author}, ...]
│
├─ Batch commits (max 20 per Bedrock call):
│    batches = [commits[0:20], commits[20:40], ...]
│
├─ For each batch:
│    ├─ Build prompt:
│    │    system: "Engineering lead reviewing commits for release readiness"
│    │    user:   commit list as formatted text
│    │            "Produce: Commit Quality, Changelog, Risk Assessment, Recommendations"
│    ├─ Bedrock call
│    └─ batch_result = markdown response
│
├─ If single batch: final_result = batch_result
├─ If multiple batches:
│    └─ Synthesis call:
│         prompt: "Synthesize these batch analyses into one coherent report"
│         input:  all batch_results concatenated
│         output: unified markdown
│
├─ Extract risk_level:
│    search markdown for "high risk" → "high"
│    search markdown for "medium risk" → "medium"
│    default → "low"
│
├─ Build result:
│    {markdown: "...", summary: "N commits analysed",
│     risk_level: "high|medium|low"}
│
└─ return result
```

**Risk Level Extraction:**

```python
if "high risk" in markdown.lower():
    risk_level = "high"
elif "medium risk" in markdown.lower():
    risk_level = "medium"
else:
    risk_level = "low"
```

---

## 8. Shared Infrastructure

### 8.1 Bedrock Model Factory

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

### 8.2 Cache Layer

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

### 8.3 Chunker

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

### 8.4 Linter Runner

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

## 9. Inter-Agent Data Flow

```
                     file_hash, content, language
                              │
                    ┌─────────▼──────────┐
                    │   PHASE 1 OUTPUT   │
                    │                    │
    bug_results ────┤  {bugs, narrative} ├──── static_results
    (from bug_      │                    │     (from static_
     analysis)      │  {linter_findings, │      analysis)
                    │   semantic_findings}│
                    │                    │
    flow_ctx ───────┤  {markdown,        │
    (from code_     │   entry_points,    │
     flow)          │   steps}           │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────────────┐
              │               │                       │
     ┌────────▼────────┐      │              ┌────────▼────────┐
     │  code_design    │      │              │    mermaid       │
     │                 │      │              │                  │
     │ receives:       │      │              │ receives:        │
     │ - bug_results   │      │              │ - flow_ctx       │
     │ - static_results│      │              │ - mermaid_type   │
     │                 │      │              │                  │
     │ T1: understand  │      │              │ → {diagram_type, │
     │ T2: JSON        │      │              │    mermaid_src}  │
     │ T3: 9-sec doc   │      │              └─────────────────┘
     └────────┬────────┘      │
              │               │
              └───────────────▼───────────────────────┐
                              │                       │
                     ┌────────▼────────┐              │
                     │ comment_gen     │              │
                     │                │              │
                     │ receives:       │              │
                     │ - bug_results  │              │
                     │ - static_      │              │
                     │   results      │              │
                     │                │              │
                     │ → {comments,   │              │
                     │    summary}    │              │
                     └────────────────┘              │
```

---

## 10. End-to-End Sequence Diagram

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

## 11. Agent Output Schemas

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

### Commit Analysis

```json
{
  "markdown": "string — full report with Commit Quality, Changelog, Risk Assessment, Recommendations",
  "summary": "string — e.g. '12 commits analysed'",
  "risk_level": "high | medium | low"
}
```

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
