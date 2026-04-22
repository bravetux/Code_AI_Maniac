# Phase 6 — Wave 6A Design

**Scope:** F5 (API Test Generator from OpenAPI/Swagger), F6 (Performance / Load Test Script Generator), F10 (Traceability Matrix + Coverage Gap Finder).

**Dated:** 2026-04-22
**Author:** B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>

---

## 0. Constraints

Carried from user brief — non-negotiable:

1. Each feature is a **separate agent** (new module in `agents/`).
2. Each agent **may have subagents** — loose definition (see §3): LLM calls, deterministic pipeline-tool helpers, or calls to other existing agents' `run_*`.
3. **Do not modify existing tools.** If an existing tool is insufficient, wrap it with a **new pipeline tool** alongside.
4. The only existing files edited in this wave are `agents/orchestrator.py` and `app/components/feature_selector.py`, and only to **add** lines — never to modify pre-existing behaviour.

---

## 1. Phase 6 decomposition

Phase 6 as defined in `1128_FEATURES.md` is 11 features (F4, F5, F6, F9, F10, F11, F13, F14, F15, F22, F23). Delivering all 11 in a single spec produces an unreviewable plan and drifts during build. Phase 6 is decomposed into three delivery waves, each with its own spec and plan:

| Wave | Features | Theme |
|---|---|---|
| **6A (this spec)** | F5, F6, F10 | Spec-driven test generation (reuses Phase 5 intake plumbing) |
| **6B** | F13, F14, F15, F11, F9 | Code generation and patching (shares a patch-emitter pipeline tool) |
| **6C** | F22, F23, F4 | Review expansion and UI automation (F4 = Selenium/Playwright/Cypress/Tosca) |

This document defines **Wave 6A** only.

---

## 2. Architecture overview

Wave 6A adds **3 agents** and **3 deterministic pipeline tools**. Existing files edited: exactly two (`orchestrator.py`, `feature_selector.py`). Both are additive.

```
agents/                              tools/
├── api_test_generator.py   (F5)     ├── postman_emitter.py       (F5 subagent)
├── perf_test_generator.py  (F6)     ├── load_profile_builder.py  (F6 subagent)
└── traceability_matrix.py  (F10)    └── test_scanner.py          (F10 subagent)

agents/orchestrator.py                ← +3 imports, +3 dispatch entries (~6 lines)
app/components/feature_selector.py    ← +3 entries in ALL_FEATURES / FEATURE_GROUPS / FEATURE_HELP,
                                         plus F10-only inline helper expander (~30 lines)
```

### Agent pattern

Every new agent mirrors `agents/unit_test_generator.py`:

```python
def run_<name>(conn, job_id, file_path, content, file_hash,
               language, custom_prompt, **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached
    # 1. Resolve inputs (prefix → sibling file → source itself)
    # 2. Call deterministic pipeline-tool subagents
    # 3. Call strands.Agent LLM subagent(s) as needed
    # 4. Write artifacts under Reports/<ts>/<feature_folder>/
    # 5. write_cache + add_history
    return {"markdown": ..., "summary": ..., "output_path": ..., ...}
```

### Intake convention

Wave 6A uses the same prefix-over-`custom_prompt` idiom as F24 / F37:

| Prefix | Meaning | Consumed by |
|---|---|---|
| `__openapi_spec__\n<YAML>` | Inline OpenAPI body | F5, F6 |
| `__mode__requirements\n<story>` | Treat source as story, not code/spec | F6 |
| `__stories__\n<text>` | Inline stories for the matrix | F10 |
| `__tests_dir__=<path>` | Test folder path (single line) | F10 |
| `__src_dir__=<path>` | Code folder path, triggers `test_coverage` subagent | F10 |

Fallback when no prefix is present:
- F5/F6 — look for sibling `openapi.yaml` / `.yml` / `.json`, else treat source file as the spec (YAML/JSON sniff on first 1 KB).
- F10 — parse `"::"`-joined source_ref as `stories::tests_dir::src_dir`.

The F10 inline UI helper in `feature_selector.py` writes the three prefixes into `custom_prompt` on the user's behalf — no schema change, no new dict keys.

### Reports layout

```
Reports/<YYYYMMDD_HHMMSS>/
├── api_tests/         (F5 — language-native test file + api_collection.json)
├── perf_tests/        (F6 — plan.jmx OR Simulation.scala)
└── traceability/      (F10 — matrix.csv, matrix.md, gaps.md)
```

F10 auto-scans the parent `Reports/<ts>/` directory: anything under `api_tests/` or `perf_tests/` from the same run is automatically included as tests in the matrix without needing `__tests_dir__`. This is the implicit coupling that lets a single multi-agent run chain F5 → F6 → F10.

### Caching

`tools/cache.py` is reused **unchanged**. Cache key remains `(file_hash, feature_key, language, custom_prompt)`. F10's multi-input case is handled by folding a cheap `mtime` digest of the tests folder into the resolved `custom_prompt` before the cache lookup — same key, different value when the tests folder changes.

### LLM

`agents/_bedrock.make_bedrock_model()` unchanged. Same Claude model as every other agent. No new credentials, no new env vars.

---

## 3. Subagent definition

**Loose definition (adopted):** a subagent is any callable invoked from a parent agent's `run_*`. Includes:

- a second `strands.Agent` LLM call inside the parent,
- a deterministic function in a new `tools/*.py` module (pipeline-tool subagent),
- a call to another existing agent's `run_*` (e.g., F10 calling `run_test_coverage`).

The LLM-cost axis is what matters — not the module shape. Pipeline-tool subagents are the primary mechanism for satisfying the constraint "extend via new pipelines, never modify existing tools." Concrete per-feature subagent inventory:

| Agent | LLM subagents | Pipeline-tool subagents | Existing-agent subagents |
|---|---|---|---|
| F5 `api_test_generator` | 1 (framework-aware test generation) | `tools/postman_emitter.py` (deterministic) | — |
| F6 `perf_test_generator` | 1 (framework-aware plan generation) | `tools/load_profile_builder.py` (deterministic) | — |
| F10 `traceability_matrix` | 1 (AC-extraction) + 1 (ambiguous-match batch) | `tools/test_scanner.py` (deterministic) + `tools/spec_fetcher.py` (existing, unchanged) | `run_test_coverage` (optional) |

---

## 4. F5 — `api_test_generator`

### 4.1 Inputs

- **OpenAPI spec** — via `__openapi_spec__\n<YAML>` prefix, sibling `openapi.yaml`/`.yml`/`.json`, or source-file-is-the-spec (detected by extension + YAML/JSON sniff on first 1 KB).
- **Sidebar `language`** — picks the code-level framework.

### 4.2 Framework auto-pick

| `language` input | Primary framework | File suffix | Fence |
|---|---|---|---|
| `python` | pytest + requests | `test_api.py` | python |
| `java` / `kotlin` | REST Assured + JUnit 5 | `ApiTests.java` | java |
| `csharp` / `.net` | xUnit + HttpClient | `ApiTests.cs` | csharp |
| `typescript` / `javascript` | supertest + Jest | `api.test.ts` | typescript |
| anything else (including blank) | *(no code file — Postman only)* | — | — |

If language is blank or maps to nothing idiomatic, the agent emits only the Postman collection — no broken code file. The Postman collection is always produced regardless of language.

### 4.3 Pipeline

1. Resolve spec (prefix → sibling → source-is-spec). Parse once via existing `tools/openapi_parser.py`. On parse failure: short error Markdown, no artifacts, no cache entry.
2. **LLM subagent (framework-aware):** one `strands.Agent` call, framework-specific system prompt, fed the parsed operation list (not raw YAML). Asks for a complete test file with happy / 4xx / 5xx cases per endpoint, parameterised where the framework supports it, auth stubs when `components.securitySchemes` is present. Extract the fenced code block, write to `Reports/<ts>/api_tests/<suffix>`.
3. **Deterministic pipeline-tool subagent — `tools/postman_emitter.py`:**

   ```python
   def build_collection(parsed_spec: dict, base_url: str | None = None) -> dict:
       """Return a Postman 2.1 collection dict from an openapi_parser output."""
   ```

   Walks the parsed spec, emits one Postman request per operation: URL with `{{baseUrl}}` variable, method, headers from `parameters[in=header]`, body from `requestBody.content[*/*].example` or a schema-stub fallback, a `pm.test("status is 2xx", ...)` assertion. Writes `Reports/<ts>/api_tests/api_collection.json`. Zero LLM tokens.
4. Build Markdown report: endpoint count, framework picked, paths, fenced code preview.

### 4.4 Outputs per run

```
Reports/<ts>/api_tests/
├── test_api.py              (or ApiTests.java / ApiTests.cs / api.test.ts — LLM-generated)
└── api_collection.json      (deterministic, always present)
```

### 4.5 Fixture

`tests/fixtures/wave6a/petstore_openapi.yaml` — ~20-line Petstore-lite spec with 3 endpoints (`GET /pets`, `POST /pets`, `GET /pets/{id}`).

### 4.6 Pass criteria

- [ ] One code file + one `api_collection.json` per run.
- [ ] Every operation from the spec appears in both artifacts.
- [ ] Path parameters render as `{id}` in code URLs and `:id` / `{{id}}` in Postman URLs.
- [ ] At least one 4xx negative test per endpoint in the code file.
- [ ] `api_collection.json` parses as valid Postman 2.1.

### 4.7 Failure modes

- Malformed spec → short error Markdown, no artifacts, no cache entry.
- No `language` and spec has no securitySchemes → Postman-only output with an info note.

---

## 5. F6 — `perf_test_generator`

### 5.1 Inputs

- OpenAPI spec — same resolution chain as F5.
- **OR** a user story — via `__mode__requirements\n<story>` prefix, or a `.txt` source with no spec sibling.
- Sidebar `language` — picks JMeter vs Gatling.

### 5.2 Framework auto-pick

| `language` input | Framework | Output file | Fence |
|---|---|---|---|
| `java` / `scala` / `gatling` | Gatling (Scala DSL) | `Simulation.scala` | scala |
| anything else (blank) | JMeter | `plan.jmx` | xml |

Exactly one artifact per run — never both.

### 5.3 Pipeline

1. Detect mode. `__mode__requirements\n` prefix OR no resolvable spec → story mode. Otherwise spec mode.
2. Spec mode: parse via `tools/openapi_parser.py`. Filter idempotent metadata endpoints (`/health`, `/metrics`, `/livez`, `/readyz`) out of the steady-state load.
3. **Deterministic pipeline-tool subagent — `tools/load_profile_builder.py`:**

   ```python
   def build_profile(num_endpoints: int, target: str = "medium") -> dict:
       """Return virtual_users / ramp_up_seconds / steady_state_seconds / think_time_ms / target_rps."""
   ```

   Default `medium` profile: 50 VUs, 60 s ramp, 300 s steady, 500 ms think time, rps scaled to op count. Injected into the LLM prompt so timings are fixed numbers — LLM only composes syntax around them.
4. **LLM subagent (framework-aware):** framework-specific system prompt.
   - **JMeter:** complete `.jmx` XML with `TestPlan`, one `ThreadGroup` using the profile numbers, one `TransactionController` per endpoint, `HTTPSamplerProxy`, `ResponseAssertion` on 2xx, `ConstantTimer` using `think_time_ms`, `SummaryReport` + `ViewResultsTree` listeners.
   - **Gatling:** `Simulation.scala` with imports, one scenario per endpoint chained into `scenario("LoadTest")`, `inject(rampUsersPerSec).to()` using the profile, HTTP config with `baseUrl` placeholder, status checks.
5. Extract fenced block, write to `Reports/<ts>/perf_tests/`.
6. Build Markdown: framework, endpoint count, load profile, artifact path, fenced preview.

### 5.4 Outputs per run

```
Reports/<ts>/perf_tests/
├── plan.jmx                 (JMeter default) — OR —
└── Simulation.scala         (Gatling when language ∈ {java, scala, gatling})
```

### 5.5 Fixtures

- `tests/fixtures/wave6a/petstore_openapi.yaml` (shared with F5) for spec mode.
- `tests/fixtures/wave6a/order_story.txt` for story mode (reuses the order-management narrative from Phase 5 HOWTO).

### 5.6 Pass criteria

- [ ] Exactly one artifact under `Reports/<ts>/perf_tests/`.
- [ ] JMeter: XML parses (`xmllint --noout plan.jmx`), ≥ N `HTTPSamplerProxy` for N endpoints.
- [ ] Gatling: compiles with a standard archetype, `setUp()...inject(...)` present, one `exec()` per endpoint.
- [ ] Load-profile numbers in artifact match `load_profile_builder.py` output (LLM didn't override them).
- [ ] Metadata endpoints excluded from steady-state load.

### 5.7 Failure modes

- Neither spec nor story present → short error Markdown, no artifact.
- LLM emits empty/malformed XML or Scala → extractor returns empty; agent writes error Markdown instead of a broken plan.

---

## 6. F10 — `traceability_matrix`

### 6.1 Inputs (any combination — missing pieces degrade gracefully)

- **Stories** — `__stories__\n<text>` prefix, Jira/ADO/Qase URL via existing `tools/spec_fetcher.py`, or source file when it is `.txt`/`.md`.
- **Tests folder** — `__tests_dir__=<path>` prefix, or 2nd path in `"::"`-joined source_ref.
- **Code folder (optional)** — `__src_dir__=<path>` prefix, or 3rd path. Triggers `run_test_coverage` subagent when present.

F10-only inline UI helper in `feature_selector.py` renders three text inputs when F10 is ticked and writes the prefixes into `custom_prompt` on the user's behalf.

### 6.2 Pipeline

1. **Resolve stories.** Extract acceptance criteria (AC-1, AC-2, …) via a lightweight LLM call with a strict JSON-schema prompt → machine-readable list.
2. **Scan tests folder — `tools/test_scanner.py`.** Pure Python, no LLM. Pattern-matches by file extension:

   | Pattern | Match |
   |---|---|
   | `*.py` | `def test_*`, `@pytest.mark.*`, docstrings |
   | `*Test*.java` / `*Tests.cs` | `@Test` / `[Fact]` / `[Theory]` method names |
   | `*.test.ts` / `*.test.js` | `it("…")` / `test("…")` strings |
   | `*.feature` | `Scenario:` / `Scenario Outline:` |
   | `*.robot` | `*** Test Cases ***` block entries |
   | `*.jmx` | Transaction Controller `testname` attrs (picks up F6 output) |
   | Postman `*.json` | `item.name` entries (picks up F5 output) |

   Returns `[{file, test_name, kind, line, snippet}, ...]`.
3. **Auto-scan same-run outputs.** If the current `Reports/<ts>/api_tests/` or `Reports/<ts>/perf_tests/` folder exists, include them automatically — the Q6(d) glue that makes the F5→F6→F10 chain "just work" without configuration.
4. **Match AC ↔ test — hybrid.**
   - **First pass (deterministic):** token-overlap Jaccard score between AC text and test name + snippet, with stopword removal. For each (AC, test) pair, store the score. An AC is **locked** to a test when exactly one test scores ≥ 0.7 for that AC AND no other test for the same AC scores within 0.1 of the top score. Locked pairs skip the LLM pass.
   - **Ambiguous AC definition.** An AC is **ambiguous** if any of the following hold: (a) zero tests score ≥ 0.5, (b) two or more tests score ≥ 0.7 for the same AC, or (c) the top score is between 0.5 and 0.7. Ambiguous ACs and their top 5 candidate tests (by score) are passed to the LLM.
   - **Second pass (LLM subagent):** single `strands.Agent` call receives the ambiguous ACs + their candidates → JSON `{ac_id: [test_ids]}` with confidences. Batched, one round-trip regardless of AC count.
   - **Orphan tests.** Any test that is neither locked nor returned by the LLM pass for any AC is recorded as an orphan.
5. **Optional `run_test_coverage` subagent.** If `__src_dir__` resolved, call it on the tests + src folders. Annotate matched tests with coverage %.
6. **Build matrix.** CSV columns: `AC_ID | AC_Text | Tests | Kinds | Coverage_% | Status`. Status rules:
   - `green` — AC has ≥ 1 test AND (no src folder OR coverage ≥ 70%)
   - `amber` — AC has ≥ 1 test AND coverage < 70%
   - `red` — AC has 0 tests
   - `orphan` — tests exist that match no AC (separate list in `gaps.md`)
7. **Write artifacts.** Return Markdown summary: counts by status, top 5 red rows, top 5 orphans, CSV path.

### 6.3 Outputs per run

```
Reports/<ts>/traceability/
├── matrix.csv           (Excel-openable grid)
├── matrix.md            (Markdown table)
└── gaps.md              (red rows + orphan tests, sorted by severity)
```

### 6.4 Fixtures

- `tests/fixtures/wave6a/reset_password_story.txt` (reuses Phase 5 F2 story, 4 ACs).
- `tests/fixtures/wave6a/reset_password_tests/test_reset.py` (2 matching, 1 orphan, 1 AC uncovered).
- `tests/fixtures/wave6a/reset_password_src/reset_password.py` (thin module for coverage).

### 6.5 Pass criteria

- [ ] Every AC in the story appears as exactly one row in `matrix.csv`.
- [ ] Every orphan test appears in `gaps.md` with its file path.
- [ ] Status column ∈ `{green, amber, red, orphan}`.
- [ ] With `__src_dir__` set and `test_coverage` succeeding: `Coverage_%` populated. Without: `n/a`.
- [ ] F5/F6 outputs from the same `Reports/<ts>/` appear in the matrix without `__tests_dir__` being set.

### 6.6 Failure modes

- No resolvable story → short error Markdown, no CSV.
- Empty tests folder → all-red matrix, full-AC gaps.md. Not an error.
- `test_coverage` subagent fails → `Coverage_%` = `n/a`, warning appended, matrix still emits.

---

## 7. Orchestrator and feature-selector wiring

The only commit that edits existing files. Purely additive.

### 7.1 `agents/orchestrator.py`

Three imports next to the existing Phase 5 block:

```python
from agents.api_test_generator import run_api_test_generator
from agents.perf_test_generator import run_perf_test_generator
from agents.traceability_matrix import run_traceability_matrix
```

Three entries in the feature dispatch table:

```python
"api_test_generator":    run_api_test_generator,
"perf_test_generator":   run_perf_test_generator,
"traceability_matrix":   run_traceability_matrix,
```

No changes to `_fetch_files`, no new argument plumbing, no schema migration. Multi-file `"::"` handling is already in place.

### 7.2 `app/components/feature_selector.py`

Three additions to `ALL_FEATURES`:

```python
# ── Phase 6 — Wave 6A ──────────────────────────────────────────────
"api_test_generator":    "API Test Generator (OpenAPI)",
"perf_test_generator":   "Perf/Load Test Generator",
"traceability_matrix":   "Traceability Matrix + Gaps",
```

`FEATURE_GROUPS`:
- `api_test_generator` + `perf_test_generator` appended to **"Testing & Maintenance"**.
- `traceability_matrix` appended to **"Documentation & Review"**.

`FEATURE_HELP`:

```python
"api_test_generator":    "F5 — Generates API tests from an OpenAPI/Swagger spec. Framework picked by language (pytest+requests / REST Assured / xUnit / supertest). Always emits a Postman collection as a second artifact.",
"perf_test_generator":   "F6 — Generates a JMeter .jmx or Gatling Simulation.scala from an OpenAPI spec or user story. Framework picked by sidebar language (java/scala → Gatling, else JMeter).",
"traceability_matrix":   "F10 — Cross-references acceptance criteria ↔ tests ↔ code coverage. Emits CSV matrix + gap report. Auto-includes F5/F6 outputs from the same run.",
```

F10 inline helper — inside `render_feature_selector(conn)`, after the feature-group loop:

```python
if "traceability_matrix" in selected:
    with st.expander("Traceability Matrix — inputs", expanded=True):
        stories = st.text_area("Stories file path OR pasted text OR Jira/ADO/Qase URL",
                               key="f10_stories", height=80)
        tests_dir = st.text_input("Tests folder path", key="f10_tests_dir",
                                  placeholder="e.g. tests/")
        src_dir = st.text_input("Code folder path (optional — enables coverage)",
                                key="f10_src_dir", placeholder="e.g. src/")
        f10_extra = []
        if stories:   f10_extra.append(f"__stories__\n{stories}")
        if tests_dir: f10_extra.append(f"__tests_dir__={tests_dir}")
        if src_dir:   f10_extra.append(f"__src_dir__={src_dir}")
        if f10_extra:
            joined = "\n".join(f10_extra)
            custom_prompt = f"{joined}\n\n{custom_prompt}" if custom_prompt else joined
```

### 7.3 Files not touched

`config/settings.py`, `db/queries/*.py`, `tools/cache.py`, `tools/openapi_parser.py`, `tools/spec_fetcher.py`, `tools/fetch_local.py`, the Streamlit entry pages, `data/arena.db` schema.

If `ENABLED_AGENTS` is restrictive, HOWTO documents setting `ENABLED_AGENTS=all` or including the three new keys.

---

## 8. Delivery sequence

Scaffold-first, per Q7(c) decision.

| # | Commit | Edits existing files? | Ships working feature? |
|---|---|---|---|
| 1 | **Scaffold + wiring** — stub agents (placeholder `run_*`), orchestrator + feature_selector edits, F10 helper panel | Yes — `orchestrator.py`, `feature_selector.py` (~36 lines, purely additive) | No — stubs return placeholder Markdown |
| 2 | **F5 fill** — `api_test_generator.py` body + `tools/postman_emitter.py` + petstore fixture | No | Yes — F5 end-to-end |
| 3 | **F6 fill** — `perf_test_generator.py` body + `tools/load_profile_builder.py` + story fixture | No | Yes — F6 end-to-end |
| 4 | **F10 fill** — `traceability_matrix.py` body + `tools/test_scanner.py` + reset-password fixture | No | Yes — F10 end-to-end |
| 5 | **Preset seed** — `scripts/seed_wave6a_preset.py` inserts "Wave 6A: API + Perf + Traceability" preset row | No — row insert only, no schema change | One-click UX |

Each commit is independently reviewable and independently revertable.

---

## 9. Testing

### 9.1 Fixtures — under `tests/fixtures/wave6a/`

```
petstore_openapi.yaml                 # F5 + F6 spec mode (3 endpoints)
order_story.txt                       # F6 requirements mode (3-endpoint narrative)
reset_password_story.txt              # F10 stories (4 ACs)
reset_password_tests/
├── test_reset.py                     # 2 match ACs, 1 orphan
└── test_unmapped.py                  # 1 orphan
reset_password_src/
└── reset_password.py                 # thin module for coverage subagent
canned_llm/
├── f5_pytest.txt                     # canned LLM responses for CI
├── f6_jmeter.xml
├── f10_ac_extract.json
└── f10_match_batch.json
```

### 9.2 Smoke tests — under `tests/test_wave6a/`

- `test_api_test_generator.py` — artifact count = 2, Postman JSON valid, op count matches.
- `test_perf_test_generator.py` — one artifact, XML or Scala parses, op count matches.
- `test_traceability_matrix.py` — CSV has 4 AC rows, ≥ 1 red, orphan appears in `gaps.md`.

All three tests `monkeypatch` `strands.Agent.__call__` to return canned responses from `canned_llm/*`. No Bedrock tokens in CI. Matches the existing LLM-agent test pattern.

### 9.3 HOWTO doc

`Phase6a_HOWTO_Test.txt` under project root, same structure as `Phase5_HOWTO_Test.txt`. Sections: Prerequisites, F5 (UI + CLI + pass criteria), F6, F10, Troubleshooting.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| LLM produces malformed XML for JMeter `.jmx` | Prompt requires ```xml``` fencing; extractor rejects empty/non-XML; `load_profile_builder` guarantees ThreadGroup numbers aren't hallucinated. |
| OpenAPI spec too large for the prompt window | Feed the LLM the **parsed op list**, not raw YAML. Parsing is local via `openapi_parser.py`. |
| F10 token-overlap matching too coarse → false matches | Jaccard 0.7 is conservative; LLM second pass handles ambiguity; orphans always audited in `gaps.md`. |
| `test_coverage` subagent slow or flaky on large code folders | Degrade gracefully — `Coverage_%` = `n/a`, warning appended, matrix still emits. |
| User ticks F5/F6/F10 with no spec and no story | Each agent returns an error Markdown, writes no artifacts, writes no cache entry. Orchestrator run does not crash. |
| Cache collisions across runs with same spec, different tests folder | F10 cache key folds a cheap mtime digest of the tests folder into `custom_prompt`. F5/F6 key off the spec hash only — correct, because identical spec → identical tests is the intent. |
| Schema drift in `data/arena.db` | None — zero schema changes this wave. |
| `ENABLED_AGENTS` restricts the new keys | HOWTO: set `ENABLED_AGENTS=all` or include `api_test_generator,perf_test_generator,traceability_matrix`. |

---

## 11. Out of scope for Wave 6A

- LoadRunner → JMeter migrator (deferred to Phase 8 — legacy-modernization pack).
- Defect axis in the traceability matrix.
- Multi-framework fan-out in F5 (one code framework per run + always-on Postman).
- Dedicated widgets or schema columns for spec/tests/src paths (prefix convention instead).
- A meta-orchestrator agent wrapping F5 + F6 + F10 (implicit coupling via shared `Reports/<ts>/` folder instead).
- Wave 6B and 6C features (F13, F14, F15, F11, F9, F22, F23, F4) — separate specs and plans.

---

## 12. Appendix — design decisions

| Q | Decision | Rationale |
|---|---|---|
| Q1 | F5: auto-picked code framework + deterministic Postman subagent | Main artifact idiomatic to target stack; Postman is near-free via deterministic build from parsed spec; demonstrates agent-plus-pipeline-tool pattern |
| Q2 | F6: JMeter + Gatling, auto-picked by language; LoadRunner deferred | LoadRunner migrator is a legacy-modernization flow, belongs with Phase 8 |
| Q3 | F10: Stories ↔ Tests ↔ Code coverage (no defects) | Coverage axis adds real insight; defects axis too noisy in most Jira instances |
| Q4 | Prefix-convention intake + inline F10 helper | Zero schema/tooling changes; F24/F37 parity; helper adds discoverability without new plumbing |
| Q5 | Loose subagent definition | Pipeline tools are the mechanism for "extend via new pipelines" constraint; LLM-cost axis is what matters |
| Q6 | Implicit coupling via shared Reports folder + Wave 6A preset seed | Keeps agents fully independent; preset gives one-click UX without meta-agent |
| Q7 | Scaffold-first commit sequence | Minimises churn in existing files; each feature-fill commit is independently reviewable and revertable |
