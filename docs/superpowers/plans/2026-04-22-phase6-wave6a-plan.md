# Phase 6 Wave 6A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three new AI Code Maniac agents — F5 (API Test Generator from OpenAPI), F6 (Performance/Load Test Generator), F10 (Traceability Matrix + Coverage Gap Finder) — plus three new deterministic pipeline tools that support them, without modifying any existing tool.

**Architecture:** Each feature is a separate agent in `agents/<name>.py` that follows the established `run_<name>(conn, job_id, file_path, content, file_hash, language, custom_prompt, **kwargs)` contract (mirrors `agents/unit_test_generator.py`). Each agent delegates to deterministic pipeline-tool subagents in `tools/<name>.py` for non-LLM work (spec-to-Postman conversion, load-profile constants, test-file scanning). Wiring touches only `agents/orchestrator.py` and `app/components/feature_selector.py`, purely additively. All intake uses the existing F24/F37 prefix convention over `custom_prompt`; no DB schema changes.

**Tech Stack:** Python 3.11, DuckDB, Strands (AWS Bedrock Claude), Streamlit, pytest, PyYAML, unittest.mock. Existing unchanged helpers reused: `tools/openapi_parser.py`, `tools/spec_fetcher.py`, `tools/cache.py`, `tools/fetch_local.py`, `agents/_bedrock.py`, `db/queries/*`.

**Companion spec:** `docs/superpowers/specs/2026-04-22-phase6-wave6a-design.md` — defer to the spec for rationale; this plan is the executable recipe.

---

## Conventions for every new file

1. **License header** — every new `.py` file under `agents/` or `tools/` starts with the standard 20-line GPLv3 header used across the repo. Use this exact block, substituting the "Developed:" date for today (2026-04-22):

```python
# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 22nd April 2026
```

Tests and fixtures skip the header (existing repo convention varies — add it only if a neighbouring test file has one).

2. **Git commits** — per user memory preference, commit with `-c user.name="B.VigneshKumar" -c user.email="ic19939@gmail.com"`, no Co-Authored-By trailer.

3. **Run tests** — from the project root in the activated virtualenv: `pytest tests/<path> -v`.

---

## File structure

```
NEW FILES
├── agents/api_test_generator.py             # F5 agent
├── agents/perf_test_generator.py            # F6 agent
├── agents/traceability_matrix.py            # F10 agent
├── tools/postman_emitter.py                 # F5 deterministic subagent
├── tools/load_profile_builder.py            # F6 deterministic subagent
├── tools/test_scanner.py                    # F10 deterministic subagent
├── scripts/seed_wave6a_preset.py            # one-off preset seeder (runs after DB exists)
├── Phase6a_HOWTO_Test.txt                   # operator HOWTO doc
├── tests/agents/test_api_test_generator.py  # F5 smoke + unit tests
├── tests/agents/test_perf_test_generator.py # F6 smoke + unit tests
├── tests/agents/test_traceability_matrix.py # F10 smoke + unit tests
├── tests/tools/test_postman_emitter.py      # postman emitter unit tests
├── tests/tools/test_load_profile_builder.py # load-profile builder unit tests
├── tests/tools/test_test_scanner.py         # test scanner unit tests
└── tests/fixtures/wave6a/
    ├── petstore_openapi.yaml                # F5 + F6 spec mode fixture
    ├── order_story.txt                      # F6 story mode fixture
    ├── reset_password_story.txt             # F10 stories fixture
    ├── reset_password_tests/
    │   ├── test_reset.py
    │   └── test_unmapped.py
    └── reset_password_src/
        └── reset_password.py

MODIFIED FILES (additive only)
├── agents/orchestrator.py                   # +3 imports, +3 phase1 keys, +3 dispatch entries
└── app/components/feature_selector.py       # +ALL_FEATURES entries, +FEATURE_GROUPS entries,
                                             #  +FEATURE_HELP entries, +F10 inline helper expander
```

---

# PART A — SCAFFOLD + WIRING (Commit 1)

The goal of Part A is to land a single commit that makes the three new feature keys dispatchable and visible in the UI, with stub agent bodies that return a placeholder. After Part A, every subsequent commit is additive to new files only.

---

### Task 1: Stub `api_test_generator.py`

**Files:**
- Create: `agents/api_test_generator.py`
- Test: `tests/agents/test_api_test_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_api_test_generator.py`:

```python
from agents.api_test_generator import run_api_test_generator


def test_stub_returns_placeholder_markdown(test_db):
    result = run_api_test_generator(
        conn=test_db,
        job_id="test-job-1",
        file_path="openapi.yaml",
        content="openapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n",
        file_hash="fakehash",
        language="python",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "API Test Generator" in result["markdown"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.api_test_generator'`.

- [ ] **Step 3: Create the stub implementation**

Create `agents/api_test_generator.py` with the standard license header followed by:

```python
"""F5 — API Test Generator from OpenAPI/Swagger (stub — filled in Part B)."""

import duckdb


def run_api_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    return {
        "markdown": "## API Test Generator — stub\n\nFilled in Part B of the Wave 6A plan.",
        "summary": "F5 stub (placeholder output)",
        "output_path": None,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: PASS.

- [ ] **Step 5: Do NOT commit yet** — hold all three stubs + wiring into a single Commit 1 after Task 4.

---

### Task 2: Stub `perf_test_generator.py`

**Files:**
- Create: `agents/perf_test_generator.py`
- Test: `tests/agents/test_perf_test_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_perf_test_generator.py`:

```python
from agents.perf_test_generator import run_perf_test_generator


def test_stub_returns_placeholder_markdown(test_db):
    result = run_perf_test_generator(
        conn=test_db,
        job_id="test-job-1",
        file_path="openapi.yaml",
        content="openapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n",
        file_hash="fakehash",
        language="java",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Perf" in result["markdown"] or "Performance" in result["markdown"]
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_perf_test_generator.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the stub**

Create `agents/perf_test_generator.py` with license header followed by:

```python
"""F6 — Performance / Load Test Script Generator (stub — filled in Part C)."""

import duckdb


def run_perf_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    return {
        "markdown": "## Perf/Load Test Generator — stub\n\nFilled in Part C of the Wave 6A plan.",
        "summary": "F6 stub (placeholder output)",
        "output_path": None,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/agents/test_perf_test_generator.py -v`
Expected: PASS.

- [ ] **Step 5: Hold for Commit 1.**

---

### Task 3: Stub `traceability_matrix.py`

**Files:**
- Create: `agents/traceability_matrix.py`
- Test: `tests/agents/test_traceability_matrix.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_traceability_matrix.py`:

```python
from agents.traceability_matrix import run_traceability_matrix


def test_stub_returns_placeholder_markdown(test_db):
    result = run_traceability_matrix(
        conn=test_db,
        job_id="test-job-1",
        file_path="story.txt",
        content="As a user I want to reset my password.",
        file_hash="fakehash",
        language=None,
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Traceability" in result["markdown"]
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the stub**

Create `agents/traceability_matrix.py` with license header followed by:

```python
"""F10 — Traceability Matrix + Coverage Gap Finder (stub — filled in Part D)."""

import duckdb


def run_traceability_matrix(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    return {
        "markdown": "## Traceability Matrix — stub\n\nFilled in Part D of the Wave 6A plan.",
        "summary": "F10 stub (placeholder output)",
        "output_path": None,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: PASS.

- [ ] **Step 5: Hold for Commit 1.**

---

### Task 4: Wire orchestrator

**Files:**
- Modify: `agents/orchestrator.py` (two locations — phase1 tuple near line 180, standalone dict near line 215; three new import lines near line 54)

- [ ] **Step 1: Write the failing integration test**

Append to `tests/agents/test_api_test_generator.py`:

```python
def test_orchestrator_dispatches_api_test_generator(test_db):
    from db.queries.jobs import create_job
    from agents.orchestrator import run_analysis
    job_id = create_job(test_db, source_type="local",
                        source_ref="tests/fixtures/wave6a/petstore_openapi.yaml",
                        language="python",
                        features=["api_test_generator"])
    # Will fail today: key not registered. After wiring it runs the stub and completes.
    run_analysis(test_db, job_id)
```

Similarly append to `tests/agents/test_perf_test_generator.py`:

```python
def test_orchestrator_dispatches_perf_test_generator(test_db):
    from db.queries.jobs import create_job
    from agents.orchestrator import run_analysis
    job_id = create_job(test_db, source_type="local",
                        source_ref="tests/fixtures/wave6a/petstore_openapi.yaml",
                        language="java",
                        features=["perf_test_generator"])
    run_analysis(test_db, job_id)
```

And to `tests/agents/test_traceability_matrix.py`:

```python
def test_orchestrator_dispatches_traceability_matrix(test_db, tmp_path):
    from db.queries.jobs import create_job
    from agents.orchestrator import run_analysis
    story = tmp_path / "story.txt"
    story.write_text("As a user I want to reset my password.", encoding="utf-8")
    job_id = create_job(test_db, source_type="local",
                        source_ref=str(story),
                        language=None,
                        features=["traceability_matrix"])
    run_analysis(test_db, job_id)
```

You will also need a minimal `tests/fixtures/wave6a/petstore_openapi.yaml` stub just so the local fetcher finds a file. Create it now with placeholder content:

```yaml
openapi: 3.0.0
info: { title: petstore, version: "0.1" }
paths:
  /pets:
    get:
      responses: { "200": { description: ok } }
```

(Task 5 later replaces this fixture with the full three-endpoint version.)

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_api_test_generator.py::test_orchestrator_dispatches_api_test_generator tests/agents/test_perf_test_generator.py::test_orchestrator_dispatches_perf_test_generator tests/agents/test_traceability_matrix.py::test_orchestrator_dispatches_traceability_matrix -v`
Expected: FAIL — orchestrator doesn't recognise the new feature keys (they won't appear in `standalone` dict or `phase1` filter; job probably completes without running anything, or raises KeyError).

- [ ] **Step 3: Add the three imports**

In `agents/orchestrator.py`, after the existing Phase 5 imports (near line 54 — after `from agents.openapi_generator import run_openapi_generator`), append:

```python
# Phase 6 — Wave 6A
from agents.api_test_generator import run_api_test_generator
from agents.perf_test_generator import run_perf_test_generator
from agents.traceability_matrix import run_traceability_matrix
```

- [ ] **Step 4: Register keys in the `phase1` tuple**

Find the tuple near line 178 that starts with `phase1 = [f for f in ("bug_analysis",` and ends with `"openapi_generator")`. Immediately before the closing `)` on the line `"openapi_generator")`, append:

```python
                          # Phase 6 — Wave 6A
                          "api_test_generator", "perf_test_generator",
                          "traceability_matrix",
```

So the closing of the tuple becomes:

```python
                          "unit_test_generator", "story_test_generator",
                          "gherkin_generator", "test_data_generator",
                          "dead_code_detector", "api_contract_checker",
                          "openapi_generator",
                          # Phase 6 — Wave 6A
                          "api_test_generator", "perf_test_generator",
                          "traceability_matrix")
              if f in feat_set]
```

- [ ] **Step 5: Register in the `standalone` dispatch dict**

Find the `standalone = {` block near line 193. After the last existing entry (`"openapi_generator":     run_openapi_generator,`), append before the closing `}`:

```python
        # Phase 6 — Wave 6A
        "api_test_generator":    run_api_test_generator,
        "perf_test_generator":   run_perf_test_generator,
        "traceability_matrix":   run_traceability_matrix,
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest tests/agents/test_api_test_generator.py tests/agents/test_perf_test_generator.py tests/agents/test_traceability_matrix.py -v`
Expected: all PASS.

- [ ] **Step 7: Hold for Commit 1.**

---

### Task 5: Wire feature_selector (UI registration + F10 helper)

**Files:**
- Modify: `app/components/feature_selector.py` — `ALL_FEATURES`, `FEATURE_GROUPS`, `FEATURE_HELP`, and add an F10-only expander inside `render_feature_selector`.

Feature-selector doesn't have direct unit tests, so this task doesn't use TDD — it's a pure UI wiring change verified by launching the app.

- [ ] **Step 1: Add to `ALL_FEATURES`**

Find the `# ── Phase 5 ────` block in `ALL_FEATURES` and append immediately after the last Phase 5 entry (`"openapi_generator":     "OpenAPI Generator",`):

```python
    # ── Phase 6 — Wave 6A ──────────────────────────────────────────────
    "api_test_generator":    "API Test Generator (OpenAPI)",
    "perf_test_generator":   "Perf/Load Test Generator",
    "traceability_matrix":   "Traceability Matrix + Gaps",
```

- [ ] **Step 2: Add to `FEATURE_GROUPS`**

In the `"Testing & Maintenance"` group tuple, after `("dead_code_detector", "Dead Code Detector"),`, append:

```python
        ("api_test_generator",   "API Test Generator (OpenAPI)"),
        ("perf_test_generator",  "Perf/Load Test Generator"),
```

In the `"Documentation & Review"` group tuple, after `("api_contract_checker", "API Contract Checker"),`, append:

```python
        ("traceability_matrix",  "Traceability Matrix + Gaps"),
```

- [ ] **Step 3: Add to `FEATURE_HELP`**

After the last existing help entry (`"openapi_generator": "F37 — ..."`), append:

```python
    "api_test_generator":    "F5 — Generates API tests from an OpenAPI/Swagger spec. Framework picked by sidebar language (pytest+requests / REST Assured / xUnit / supertest). Always emits a Postman collection as a second artifact.",
    "perf_test_generator":   "F6 — Generates a JMeter .jmx or Gatling Simulation.scala from an OpenAPI spec or user story. Framework picked by sidebar language (java/scala → Gatling, else JMeter).",
    "traceability_matrix":   "F10 — Cross-references acceptance criteria ↔ tests ↔ code coverage. Emits CSV matrix + gap report. Auto-includes F5/F6 outputs from the same run.",
```

- [ ] **Step 4: Add F10 inline helper inside `render_feature_selector`**

Find the line `mermaid_type = "flowchart"` inside `render_feature_selector`. Immediately **before** that line (after the `with st.expander("Features", expanded=True):` block closes), insert:

```python
    # F10 — prefix-convention intake helper (only when Traceability Matrix is selected)
    if "traceability_matrix" in selected:
        with st.expander("Traceability Matrix — inputs", expanded=True):
            f10_stories = st.text_area(
                "Stories file path OR pasted text OR Jira/ADO/Qase URL",
                key="f10_stories", height=80,
                help="Leave blank to fall back to the source file.",
            )
            f10_tests_dir = st.text_input(
                "Tests folder path", key="f10_tests_dir",
                placeholder="e.g. tests/",
            )
            f10_src_dir = st.text_input(
                "Code folder path (optional — enables coverage)",
                key="f10_src_dir", placeholder="e.g. src/",
            )
            f10_prefixes = []
            if f10_stories:   f10_prefixes.append(f"__stories__\n{f10_stories}")
            if f10_tests_dir: f10_prefixes.append(f"__tests_dir__={f10_tests_dir}")
            if f10_src_dir:   f10_prefixes.append(f"__src_dir__={f10_src_dir}")
            if f10_prefixes:
                st.session_state["f10_prefix_block"] = "\n".join(f10_prefixes)
            else:
                st.session_state.pop("f10_prefix_block", None)
```

Then, find the `return {` block at the end of `render_feature_selector`. Immediately **before** the `return {`, insert:

```python
    # Merge F10 prefix block into custom_prompt if present
    f10_block = st.session_state.get("f10_prefix_block", "")
    if f10_block:
        custom_prompt = f"{f10_block}\n\n{custom_prompt}" if custom_prompt else f10_block
```

- [ ] **Step 5: Manual smoke of the UI**

Run: `startup.bat` (or `streamlit run app/Home.py`). Navigate to "Code Analysis" page. Confirm:
1. In the sidebar → Features → Testing & Maintenance, the two new checkboxes appear: "API Test Generator (OpenAPI)", "Perf/Load Test Generator".
2. In Features → Documentation & Review, "Traceability Matrix + Gaps" appears.
3. Tick "Traceability Matrix + Gaps" — the "Traceability Matrix — inputs" expander appears below the Features expander with three inputs (stories / tests_dir / src_dir).
4. Untick it — the expander disappears.
5. Hover tooltips show the F5/F6/F10 help text.

- [ ] **Step 6: Hold for Commit 1.**

---

### Task 6: Commit 1 — Scaffold + wiring

- [ ] **Step 1: Review the diff**

Run: `git status` and `git diff --stat` to confirm changed files:
- New: `agents/api_test_generator.py`, `agents/perf_test_generator.py`, `agents/traceability_matrix.py`
- New: `tests/agents/test_api_test_generator.py`, `tests/agents/test_perf_test_generator.py`, `tests/agents/test_traceability_matrix.py`
- New: `tests/fixtures/wave6a/petstore_openapi.yaml` (placeholder version — replaced in Task 7)
- Modified: `agents/orchestrator.py`, `app/components/feature_selector.py`

No other files should appear in the diff.

- [ ] **Step 2: Run the full wave6a test suite**

Run: `pytest tests/agents/test_api_test_generator.py tests/agents/test_perf_test_generator.py tests/agents/test_traceability_matrix.py -v`
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add agents/api_test_generator.py agents/perf_test_generator.py agents/traceability_matrix.py \
        agents/orchestrator.py app/components/feature_selector.py \
        tests/agents/test_api_test_generator.py tests/agents/test_perf_test_generator.py \
        tests/agents/test_traceability_matrix.py tests/fixtures/wave6a/petstore_openapi.yaml
git -c user.name="B.VigneshKumar" -c user.email="ic19939@gmail.com" commit -m "feat(phase6): scaffold Wave 6A agents and wire orchestrator + UI

Adds stub agents for F5 (api_test_generator), F6 (perf_test_generator),
F10 (traceability_matrix). Registers the three keys in the orchestrator
phase1 tuple and standalone dispatch dict. Registers the three features
in the Streamlit sidebar with help text and a conditional F10 input
helper. Stubs return placeholder markdown; real implementations land
in subsequent commits."
```

- [ ] **Step 4: Run full test suite to confirm no regressions**

Run: `pytest -x`
Expected: all tests PASS. If anything unrelated breaks, investigate before moving on — the scaffold commit must not regress Phase 1-5 behaviour.

---

# PART B — F5 FILL (Commit 2)

After Part B, F5 is end-to-end functional. F6 and F10 remain stubs until Part C and D.

---

### Task 7: Petstore OpenAPI fixture (final version)

**Files:**
- Modify: `tests/fixtures/wave6a/petstore_openapi.yaml` (replace the Task 4 placeholder)

- [ ] **Step 1: Replace the fixture file**

Overwrite `tests/fixtures/wave6a/petstore_openapi.yaml` with:

```yaml
openapi: 3.0.0
info:
  title: Petstore
  version: "0.1.0"
servers:
  - url: https://api.example.test
paths:
  /pets:
    get:
      summary: List pets
      operationId: listPets
      parameters:
        - name: limit
          in: query
          schema: { type: integer }
      responses:
        "200": { description: ok }
    post:
      summary: Create a pet
      operationId: createPet
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/Pet" }
            example:
              name: Rex
              tag: dog
      responses:
        "201": { description: created }
        "400": { description: bad request }
  /pets/{petId}:
    get:
      summary: Get a pet by id
      operationId: getPet
      parameters:
        - name: petId
          in: path
          required: true
          schema: { type: integer }
      responses:
        "200": { description: ok }
        "404": { description: not found }
components:
  schemas:
    Pet:
      type: object
      required: [name]
      properties:
        id:   { type: integer }
        name: { type: string }
        tag:  { type: string }
```

- [ ] **Step 2: Verify parser accepts it**

Run: `python -c "from tools.openapi_parser import parse, summarise; d=parse(open('tests/fixtures/wave6a/petstore_openapi.yaml').read()); print(summarise(d)['endpoint_count'])"`
Expected output: `3`.

- [ ] **Step 3: Hold for Commit 2.**

---

### Task 8: `tools/postman_emitter.py` — deterministic Postman 2.1 collection builder

**Files:**
- Create: `tools/postman_emitter.py`
- Test: `tests/tools/test_postman_emitter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_postman_emitter.py`:

```python
import json
from tools.openapi_parser import parse
from tools.postman_emitter import build_collection


def _load_petstore():
    with open("tests/fixtures/wave6a/petstore_openapi.yaml", "r", encoding="utf-8") as fh:
        return parse(fh.read())


def test_collection_has_postman_schema():
    spec = _load_petstore()
    col = build_collection(spec)
    assert col["info"]["schema"].startswith("https://schema.getpostman.com/json/collection/v2.1")
    assert col["info"]["name"] == "Petstore"


def test_one_item_per_operation():
    spec = _load_petstore()
    col = build_collection(spec)
    # petstore has 3 operations: GET /pets, POST /pets, GET /pets/{petId}
    assert len(col["item"]) == 3


def test_path_params_use_postman_variable_syntax():
    spec = _load_petstore()
    col = build_collection(spec)
    get_by_id = next(i for i in col["item"] if i["name"] == "GET /pets/{petId}")
    # Postman path param variable: :petId OR {{petId}} — we use the :petId convention
    assert ":petId" in get_by_id["request"]["url"]["raw"]
    # Variable registered with description
    names = [v["key"] for v in get_by_id["request"]["url"].get("variable", [])]
    assert "petId" in names


def test_request_body_uses_example_from_spec():
    spec = _load_petstore()
    col = build_collection(spec)
    post = next(i for i in col["item"] if i["name"] == "POST /pets")
    body_raw = post["request"]["body"]["raw"]
    parsed = json.loads(body_raw)
    assert parsed.get("name") == "Rex"
    assert parsed.get("tag") == "dog"


def test_every_item_has_status_2xx_assertion():
    spec = _load_petstore()
    col = build_collection(spec)
    for item in col["item"]:
        scripts = [e for e in item.get("event", []) if e.get("listen") == "test"]
        assert scripts, f"no test script on {item['name']}"
        exec_body = "\n".join(scripts[0]["script"]["exec"])
        assert "pm.test" in exec_body
        assert "2" in exec_body  # any status 2xx check is fine


def test_base_url_overrides_spec_server():
    spec = _load_petstore()
    col = build_collection(spec, base_url="https://override.test")
    variables = {v["key"]: v["value"] for v in col.get("variable", [])}
    assert variables["baseUrl"] == "https://override.test"


def test_empty_spec_returns_empty_collection():
    col = build_collection({"openapi": "3.0.0", "info": {"title": "empty", "version": "0"}, "paths": {}})
    assert col["item"] == []
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/tools/test_postman_emitter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.postman_emitter'`.

- [ ] **Step 3: Implement `tools/postman_emitter.py`**

Create `tools/postman_emitter.py` with the standard license header followed by:

```python
"""Deterministic Postman 2.1 collection builder.

Subagent for F5 (api_test_generator). Consumes a parsed OpenAPI dict (as
returned by ``tools.openapi_parser.parse``) and emits a Postman v2.1
collection with one request per operation. No LLM involvement — the
generation is pure spec-to-structure translation, so output is stable
and cache-friendly.
"""

from __future__ import annotations

import json
from typing import Any

_POSTMAN_SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"

_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


def build_collection(spec: dict, base_url: str | None = None) -> dict:
    """Build a Postman 2.1 collection from a parsed OpenAPI spec dict.

    Args:
        spec: Parsed OpenAPI dict (output of ``tools.openapi_parser.parse``).
        base_url: Optional override for the collection-level ``{{baseUrl}}``.
            If ``None``, falls back to ``spec['servers'][0]['url']``, or
            ``https://api.example.test`` when no server is declared.

    Returns:
        A Postman v2.1 collection dict. Serialise with ``json.dumps`` to write.
    """
    info = spec.get("info") or {}
    title = info.get("title") or "API"
    version = str(info.get("version") or "0.1.0")

    resolved_base = base_url or _first_server_url(spec) or "https://api.example.test"

    collection: dict = {
        "info": {
            "name": title,
            "_postman_id": f"wave6a-{_slug(title)}-{version}",
            "description": info.get("description") or f"Generated from OpenAPI spec: {title} v{version}",
            "schema": _POSTMAN_SCHEMA,
        },
        "variable": [
            {"key": "baseUrl", "value": resolved_base, "type": "string"},
        ],
        "item": [],
    }

    paths = spec.get("paths") or {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.lower() not in _METHODS or not isinstance(op, dict):
                continue
            collection["item"].append(
                _build_item(path, method.upper(), op, spec)
            )

    return collection


def _first_server_url(spec: dict) -> str | None:
    servers = spec.get("servers") or []
    if servers and isinstance(servers[0], dict):
        return servers[0].get("url")
    return None


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-") or "api"


def _build_item(path: str, method: str, op: dict, spec: dict) -> dict:
    # Postman path-param convention: /pets/{petId} → /pets/:petId
    postman_path = path
    path_vars: list[dict] = []
    for p in (op.get("parameters") or []):
        if not isinstance(p, dict):
            continue
        if p.get("in") == "path":
            name = p.get("name")
            if name:
                postman_path = postman_path.replace("{" + name + "}", ":" + name)
                path_vars.append({
                    "key": name,
                    "value": "",
                    "description": p.get("description") or f"path parameter `{name}`",
                })

    # Query params
    query = []
    for p in (op.get("parameters") or []):
        if not isinstance(p, dict):
            continue
        if p.get("in") == "query":
            query.append({
                "key": p.get("name"),
                "value": "",
                "description": p.get("description") or "",
                "disabled": not p.get("required", False),
            })

    # Headers (skip 'Content-Type' for body-less methods — requestBody adds its own)
    headers = []
    for p in (op.get("parameters") or []):
        if not isinstance(p, dict):
            continue
        if p.get("in") == "header":
            headers.append({
                "key": p.get("name"),
                "value": "",
                "description": p.get("description") or "",
            })

    body = _build_body(op, spec)
    if body:
        headers.insert(0, {"key": "Content-Type",
                           "value": body.get("content_type", "application/json")})

    raw_path = postman_path.lstrip("/")
    segments = [s for s in raw_path.split("/") if s]

    request: dict = {
        "method": method,
        "header": [{"key": h["key"], "value": h["value"],
                    "description": h.get("description", "")} for h in headers],
        "url": {
            "raw": "{{baseUrl}}/" + raw_path,
            "host": ["{{baseUrl}}"],
            "path": segments,
        },
    }
    if path_vars:
        request["url"]["variable"] = path_vars
    if query:
        request["url"]["query"] = query
    if body and "raw" in body:
        request["body"] = {"mode": "raw", "raw": body["raw"], "options":
                           {"raw": {"language": "json"}}}

    return {
        "name": f"{method} {path}",
        "request": request,
        "event": [_status_2xx_assertion()],
    }


def _build_body(op: dict, spec: dict) -> dict:
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return {}
    content = rb.get("content") or {}
    for ctype, meta in content.items():
        if not isinstance(meta, dict):
            continue
        # 1. Explicit example wins
        if "example" in meta:
            example = meta["example"]
            return {"content_type": ctype, "raw": json.dumps(example, indent=2)}
        # 2. examples.*.value (OpenAPI 3.1 shape)
        examples = meta.get("examples") or {}
        for ex_val in examples.values():
            if isinstance(ex_val, dict) and "value" in ex_val:
                return {"content_type": ctype,
                        "raw": json.dumps(ex_val["value"], indent=2)}
        # 3. Fallback: stub from schema properties
        schema = meta.get("schema") or {}
        stub = _stub_from_schema(schema, spec)
        return {"content_type": ctype, "raw": json.dumps(stub, indent=2)}
    return {}


def _stub_from_schema(schema: dict, spec: dict, _depth: int = 0) -> Any:
    if _depth > 4:
        return None
    if not isinstance(schema, dict):
        return None
    # Resolve $ref
    if "$ref" in schema:
        ref = schema["$ref"]
        resolved = _resolve_ref(ref, spec)
        return _stub_from_schema(resolved or {}, spec, _depth + 1)
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        obj: dict = {}
        for name, child in (schema.get("properties") or {}).items():
            obj[name] = _stub_from_schema(child, spec, _depth + 1)
        return obj
    if t == "array":
        items = schema.get("items") or {}
        return [_stub_from_schema(items, spec, _depth + 1)]
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False
    if t == "string":
        fmt = schema.get("format") or ""
        if fmt == "date-time":
            return "1970-01-01T00:00:00Z"
        if fmt == "date":
            return "1970-01-01"
        if fmt == "email":
            return "user@example.test"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        return ""
    return None


def _resolve_ref(ref: str, spec: dict) -> dict | None:
    # Only local refs (#/components/schemas/Foo)
    if not ref.startswith("#/"):
        return None
    parts = ref[2:].split("/")
    node: Any = spec
    for p in parts:
        if isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return None
    return node if isinstance(node, dict) else None


def _status_2xx_assertion() -> dict:
    return {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": [
                "pm.test(\"status is 2xx\", function () {",
                "    pm.expect(pm.response.code).to.be.within(200, 299);",
                "});",
            ],
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_postman_emitter.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Hold for Commit 2.**

---

### Task 9: `api_test_generator.py` — spec resolution helpers

The F5 agent fill is large; split across three tasks (9, 10, 11). Task 9 handles spec resolution. Task 10 handles the framework auto-pick. Task 11 handles the full `run_api_test_generator` integration.

**Files:**
- Modify: `agents/api_test_generator.py` (replace stub)
- Test: `tests/agents/test_api_test_generator.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_api_test_generator.py`:

```python
import pytest
from agents.api_test_generator import _resolve_spec, _SpecResolution


def test_resolve_spec_from_prefix():
    prefix = "__openapi_spec__\nopenapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n"
    res = _resolve_spec(file_path="ignored.py", content="print('hi')", custom_prompt=prefix)
    assert res.source == "prefix"
    assert res.spec["info"]["title"] == "t"


def test_resolve_spec_from_source_file_when_yaml():
    content = "openapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n"
    res = _resolve_spec(file_path="openapi.yaml", content=content, custom_prompt=None)
    assert res.source == "source"
    assert res.spec["openapi"] == "3.0.0"


def test_resolve_spec_from_source_file_when_json():
    content = '{"openapi":"3.0.0","info":{"title":"t","version":"0.1"},"paths":{}}'
    res = _resolve_spec(file_path="openapi.json", content=content, custom_prompt=None)
    assert res.source == "source"


def test_resolve_spec_from_sibling(tmp_path):
    code_file = tmp_path / "api_app.py"
    code_file.write_text("# pretend code\n", encoding="utf-8")
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text("openapi: 3.0.0\ninfo: {title: sib, version: '0.1'}\npaths: {}\n",
                         encoding="utf-8")
    res = _resolve_spec(file_path=str(code_file), content="# pretend code\n",
                        custom_prompt=None)
    assert res.source == "sibling"
    assert res.spec["info"]["title"] == "sib"


def test_resolve_spec_raises_on_malformed():
    with pytest.raises(Exception):
        _resolve_spec(file_path="openapi.yaml",
                      content="not: : : valid :: yaml ::",
                      custom_prompt="__openapi_spec__\nnot: : : valid :: yaml ::")


def test_resolve_spec_raises_when_nothing_found(tmp_path):
    # Plain code file, no prefix, no sibling
    code_file = tmp_path / "foo.py"
    code_file.write_text("print('hi')\n", encoding="utf-8")
    with pytest.raises(Exception):
        _resolve_spec(file_path=str(code_file), content="print('hi')\n", custom_prompt=None)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: new tests FAIL with `ImportError: cannot import name '_resolve_spec'`.

- [ ] **Step 3: Implement `_resolve_spec` in the agent**

Replace the body of `agents/api_test_generator.py` (keep the license header) with:

```python
"""F5 — API Test Generator from OpenAPI/Swagger.

Spec resolution is the first step — inline prefix wins, else the source file
when it sniffs as a spec, else a sibling openapi.yaml/yml/json next to the
source. Framework auto-pick drives a single Strands LLM call for the code
tests, and tools.postman_emitter produces a deterministic Postman 2.1
collection as the second artifact.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.openapi_parser import parse, extract_endpoints, OpenAPIParseError
from tools.postman_emitter import build_collection
from db.queries.history import add_history

_CACHE_KEY = "api_test_generator"

_SIBLING_NAMES = ("openapi.yaml", "openapi.yml", "openapi.json",
                  "swagger.yaml", "swagger.yml", "swagger.json")

_YAML_SNIFF = re.compile(r"^\s*(openapi|swagger)\s*:", re.IGNORECASE | re.MULTILINE)


@dataclass
class _SpecResolution:
    spec: dict
    raw: str
    source: str  # one of: prefix, source, sibling


def _resolve_spec(file_path: str, content: str, custom_prompt: str | None) -> _SpecResolution:
    """Resolve the OpenAPI spec body using the intake precedence:

    1. ``__openapi_spec__\\n<body>`` prefix in ``custom_prompt``.
    2. Source file itself when its extension is yaml/yml/json and the first
       1 KB sniffs as an OpenAPI document.
    3. Sibling file next to the source — openapi.{yaml,yml,json} or
       swagger.{yaml,yml,json}.

    Raises:
        RuntimeError: nothing resolvable.
        OpenAPIParseError: a spec body was found but failed to parse.
    """
    # 1. Prefix
    if custom_prompt:
        marker = "__openapi_spec__\n"
        if marker in custom_prompt:
            body = custom_prompt.split(marker, 1)[1]
            spec = parse(body)
            return _SpecResolution(spec=spec, raw=body, source="prefix")

    # 2. Source-is-spec
    ext = os.path.splitext(file_path)[1].lower()
    head = (content or "")[:1024]
    if ext in (".yaml", ".yml") and _YAML_SNIFF.search(head):
        spec = parse(content)
        return _SpecResolution(spec=spec, raw=content, source="source")
    if ext == ".json" and ('"openapi"' in head or '"swagger"' in head):
        spec = parse(content)
        return _SpecResolution(spec=spec, raw=content, source="source")

    # 3. Sibling
    parent = os.path.dirname(os.path.abspath(file_path))
    for name in _SIBLING_NAMES:
        cand = os.path.join(parent, name)
        if os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as fh:
                body = fh.read()
            spec = parse(body)
            return _SpecResolution(spec=spec, raw=body, source="sibling")

    raise RuntimeError(
        f"No OpenAPI spec resolvable for {file_path}. "
        f"Provide an inline __openapi_spec__ prefix, pass a yaml/json source, "
        f"or place openapi.yaml next to the source."
    )


def run_api_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    # Full implementation arrives in Task 11. Temporarily preserve stub for
    # orchestrator dispatch test.
    return {
        "markdown": "## API Test Generator — partial (Task 9 scaffold)",
        "summary": "F5 Task 9 scaffold",
        "output_path": None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: all tests PASS (including the six new `_resolve_spec` tests and the stub tests from Tasks 1+4).

- [ ] **Step 5: Hold for Commit 2.**

---

### Task 10: F5 framework auto-pick helper

**Files:**
- Modify: `agents/api_test_generator.py` (add `_pick_framework`)
- Test: `tests/agents/test_api_test_generator.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_api_test_generator.py`:

```python
from agents.api_test_generator import _pick_framework


def test_pick_framework_python():
    meta = _pick_framework("python")
    assert meta["framework"] == "pytest + requests"
    assert meta["suffix"] == "test_api.py"
    assert meta["fence"] == "python"
    assert meta["mock"]


def test_pick_framework_java():
    meta = _pick_framework("java")
    assert "REST Assured" in meta["framework"]
    assert meta["suffix"] == "ApiTests.java"


def test_pick_framework_kotlin_uses_java_stack():
    assert _pick_framework("kotlin")["framework"] == _pick_framework("java")["framework"]


def test_pick_framework_csharp_aliases():
    for lang in ("csharp", "c#", ".net"):
        meta = _pick_framework(lang)
        assert "xUnit" in meta["framework"]
        assert meta["suffix"] == "ApiTests.cs"


def test_pick_framework_typescript():
    meta = _pick_framework("typescript")
    assert "supertest" in meta["framework"].lower()
    assert meta["suffix"] == "api.test.ts"


def test_pick_framework_javascript_uses_typescript_stack():
    assert _pick_framework("javascript")["framework"] == _pick_framework("typescript")["framework"]


def test_pick_framework_blank_returns_none():
    assert _pick_framework("") is None
    assert _pick_framework(None) is None


def test_pick_framework_unknown_returns_none():
    assert _pick_framework("cobol") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: new tests FAIL with `ImportError: cannot import name '_pick_framework'`.

- [ ] **Step 3: Add `_pick_framework` to the agent**

In `agents/api_test_generator.py`, immediately before `def run_api_test_generator`, add:

```python
_FRAMEWORK_MAP: dict[str, dict] = {
    "python":     {"framework": "pytest + requests",
                   "suffix": "test_api.py", "fence": "python",
                   "mock": "responses / httpx_mock"},
    "java":       {"framework": "REST Assured + JUnit 5",
                   "suffix": "ApiTests.java", "fence": "java",
                   "mock": "WireMock"},
    "kotlin":     {"framework": "REST Assured + JUnit 5",
                   "suffix": "ApiTests.java", "fence": "java",
                   "mock": "WireMock"},
    "csharp":     {"framework": "xUnit + HttpClient",
                   "suffix": "ApiTests.cs", "fence": "csharp",
                   "mock": "WireMock.Net"},
    "c#":         {"framework": "xUnit + HttpClient",
                   "suffix": "ApiTests.cs", "fence": "csharp",
                   "mock": "WireMock.Net"},
    ".net":       {"framework": "xUnit + HttpClient",
                   "suffix": "ApiTests.cs", "fence": "csharp",
                   "mock": "WireMock.Net"},
    "typescript": {"framework": "supertest + Jest",
                   "suffix": "api.test.ts", "fence": "typescript",
                   "mock": "nock"},
    "javascript": {"framework": "supertest + Jest",
                   "suffix": "api.test.ts", "fence": "typescript",
                   "mock": "nock"},
}


def _pick_framework(language: str | None) -> dict | None:
    """Return the framework meta dict for ``language``, or None if blank/unknown."""
    if not language:
        return None
    return _FRAMEWORK_MAP.get(language.strip().lower())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Hold for Commit 2.**

---

### Task 11: F5 full `run_api_test_generator` integration

**Files:**
- Modify: `agents/api_test_generator.py` (replace stub `run_api_test_generator` with full version)
- Test: `tests/agents/test_api_test_generator.py` (append integration tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_api_test_generator.py`:

```python
import json
import os
from unittest.mock import patch, MagicMock


_CANNED_PYTEST = '''```python
import pytest
import requests

BASE = "https://api.example.test"

def test_list_pets():
    r = requests.get(f"{BASE}/pets")
    assert r.status_code == 200

def test_create_pet():
    r = requests.post(f"{BASE}/pets", json={"name": "Rex"})
    assert r.status_code == 201

def test_create_pet_rejects_bad_body():
    r = requests.post(f"{BASE}/pets", json={})
    assert r.status_code == 400

def test_get_pet():
    r = requests.get(f"{BASE}/pets/1")
    assert r.status_code == 200

def test_get_pet_missing():
    r = requests.get(f"{BASE}/pets/99999")
    assert r.status_code == 404
```'''


def test_run_api_test_generator_writes_both_artifacts(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # isolate Reports/ output
    spec_content = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/petstore_openapi.yaml",
                        "r", encoding="utf-8").read()
    with patch("agents.api_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_PYTEST
        mock_cls.return_value = mock_agent
        result = run_api_test_generator(
            conn=test_db, job_id="j1",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h1", language="python", custom_prompt=None,
        )
    # Outputs present
    assert "output_path" in result
    assert os.path.isfile(result["output_path"])
    # Postman collection always written
    postman = os.path.join(os.path.dirname(result["output_path"]), "api_collection.json")
    assert os.path.isfile(postman)
    collection = json.loads(open(postman, "r", encoding="utf-8").read())
    assert len(collection["item"]) == 3
    # Report mentions framework
    assert "pytest" in result["markdown"].lower()


def test_run_api_test_generator_blank_language_still_writes_postman(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/petstore_openapi.yaml",
                        "r", encoding="utf-8").read()
    # No LLM call expected — Agent must not be invoked.
    with patch("agents.api_test_generator.Agent") as mock_cls:
        result = run_api_test_generator(
            conn=test_db, job_id="j2",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h2", language=None, custom_prompt=None,
        )
        mock_cls.assert_not_called()
    # Postman still written
    postman = result["postman_path"]
    assert os.path.isfile(postman)
    collection = json.loads(open(postman, "r", encoding="utf-8").read())
    assert len(collection["item"]) == 3


def test_run_api_test_generator_bad_spec_returns_error(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.api_test_generator.Agent") as mock_cls:
        result = run_api_test_generator(
            conn=test_db, job_id="j3",
            file_path="openapi.yaml", content="not: : : valid :: yaml",
            file_hash="h3", language="python", custom_prompt=None,
        )
        mock_cls.assert_not_called()
    assert "error" in result["summary"].lower() or "failed" in result["summary"].lower()
    assert result.get("output_path") is None


def test_run_api_test_generator_uses_cache(test_db):
    from tools.cache import write_cache
    cached = {"markdown": "CACHED", "summary": "cached", "output_path": "/tmp/cached.py"}
    write_cache(test_db, job_id="j4", feature="api_test_generator",
                file_hash="cachehash", language="python", custom_prompt=None,
                result=cached)
    result = run_api_test_generator(
        conn=test_db, job_id="j4",
        file_path="openapi.yaml", content="openapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}",
        file_hash="cachehash", language="python", custom_prompt=None,
    )
    assert result["markdown"] == "CACHED"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_api_test_generator.py -v`
Expected: the four new integration tests FAIL (stub doesn't write files, doesn't parse the spec, doesn't cache).

- [ ] **Step 3: Implement the full `run_api_test_generator`**

In `agents/api_test_generator.py`, replace the stub `run_api_test_generator` with:

```python
_SYSTEM_PROMPT_TEMPLATE = """You are a senior API test engineer specialising in {framework}.

Generate a COMPLETE, runnable {framework} test file that exercises every endpoint listed below. Rules:

1. One test per endpoint for the happy path (2xx).
2. For endpoints that declare a 4xx response, add a negative test that triggers it (e.g. missing required body, invalid path parameter type).
3. For endpoints that declare a 5xx response, add a resilience test asserting the client handles the error cleanly.
4. Use a base URL variable so the suite runs against any environment — default it to ``https://api.example.test``.
5. Mock HTTP with {mock_lib} so tests are hermetic (no real network).
6. If the spec declares components.securitySchemes, include one test that exercises a valid auth header and one that exercises a missing/invalid header.
7. Return ONLY the complete test file wrapped in a single fenced code block:

```{fence}
<complete test file>
```

Endpoints:
{endpoint_table}

Title: {title}
Version: {version}
"""


def _format_endpoint_table(endpoints: list[dict]) -> str:
    lines = []
    for ep in endpoints:
        params = ", ".join(
            f"{p['name']}({p['in']}:{p.get('type') or 'string'})" for p in ep.get("parameters", [])
        ) or "-"
        statuses = ", ".join(r["status"] for r in ep.get("responses", [])) or "-"
        lines.append(f"- {ep['method']} {ep['path']} — params: {params}; responses: {statuses}")
    return "\n".join(lines) or "(no endpoints)"


def _extract_code_block(text: str, fence: str) -> str:
    pat = rf"```{re.escape(fence)}\s*\n(.*?)```"
    m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_api_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    # 1. Resolve spec
    try:
        res = _resolve_spec(file_path, content, custom_prompt)
    except (RuntimeError, OpenAPIParseError) as exc:
        error_md = f"## API Test Generator — error\n\n{exc}"
        return {"markdown": error_md,
                "summary": f"F5 error: {exc}",
                "output_path": None}

    endpoints = extract_endpoints(res.spec)
    title = (res.spec.get("info") or {}).get("title") or "API"
    version = str((res.spec.get("info") or {}).get("version") or "0.1.0")

    # 2. Output directory (single Reports/<ts>/ shared per run)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "api_tests")
    os.makedirs(out_dir, exist_ok=True)

    # 3. Deterministic Postman subagent (always runs)
    collection = build_collection(res.spec)
    postman_path = os.path.join(out_dir, "api_collection.json")
    with open(postman_path, "w", encoding="utf-8") as fh:
        import json as _json
        fh.write(_json.dumps(collection, indent=2))

    # 4. LLM framework-aware test generation (only if language maps to a framework)
    meta = _pick_framework(language)
    output_path: str | None = None
    framework_label = "Postman only (language blank or unmapped)"
    code_body = ""
    if meta is not None:
        prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            framework=meta["framework"],
            mock_lib=meta["mock"],
            fence=meta["fence"],
            endpoint_table=_format_endpoint_table(endpoints),
            title=title,
            version=version,
        )
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, prompt))
        raw = str(agent(f"Generate the complete {meta['framework']} test file now."))
        code_body = _extract_code_block(raw, meta["fence"])

        if code_body:
            output_path = os.path.join(out_dir, meta["suffix"])
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(code_body)
            framework_label = meta["framework"]

    # 5. Report
    md_parts = [
        f"## API Test Generator — `{title}` v{version}",
        f"- **Spec source:** {res.source}",
        f"- **Endpoints:** {len(endpoints)}",
        f"- **Framework:** {framework_label}",
        f"- **Postman collection:** `{postman_path}` ({len(collection['item'])} requests)",
    ]
    if output_path:
        md_parts.append(f"- **Code file:** `{output_path}`")
        md_parts.append(f"\n### Generated code\n\n```{meta['fence']}\n{code_body}\n```")
    markdown = "\n".join(md_parts)
    summary = (f"Generated {len(endpoints)} API tests "
               f"({framework_label}) + Postman collection.")

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": output_path,
        "postman_path": postman_path,
        "framework": framework_label,
        "endpoint_count": len(endpoints),
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
```

- [ ] **Step 4: Run all F5 tests**

Run: `pytest tests/agents/test_api_test_generator.py tests/tools/test_postman_emitter.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Also run the full suite to check no regressions**

Run: `pytest -x`
Expected: all PASS.

- [ ] **Step 6: Hold for Commit 2.**

---

### Task 12: Commit 2 — F5 fill

- [ ] **Step 1: Verify diff**

Run: `git status` and confirm only these files appear:
- New: `tools/postman_emitter.py`, `tests/tools/test_postman_emitter.py`
- Modified: `agents/api_test_generator.py`, `tests/agents/test_api_test_generator.py`, `tests/fixtures/wave6a/petstore_openapi.yaml`

No other files.

- [ ] **Step 2: Commit**

```bash
git add agents/api_test_generator.py tools/postman_emitter.py \
        tests/agents/test_api_test_generator.py tests/tools/test_postman_emitter.py \
        tests/fixtures/wave6a/petstore_openapi.yaml
git -c user.name="B.VigneshKumar" -c user.email="ic19939@gmail.com" commit -m "feat(phase6): implement F5 api_test_generator

Auto-picks code framework from sidebar language (pytest+requests,
REST Assured, xUnit+HttpClient, supertest+Jest) and always emits a
deterministic Postman 2.1 collection via tools/postman_emitter.py.
Spec resolution honours the __openapi_spec__ prefix, YAML/JSON source
files, and sibling openapi.{yaml,yml,json}. Existing tools.openapi_parser
is reused unchanged."
```

---

# PART C — F6 FILL (Commit 3)

---

### Task 13: `tools/load_profile_builder.py`

**Files:**
- Create: `tools/load_profile_builder.py`
- Test: `tests/tools/test_load_profile_builder.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_load_profile_builder.py`:

```python
import pytest
from tools.load_profile_builder import build_profile


def test_profile_returns_required_fields():
    p = build_profile(num_endpoints=5)
    for key in ("virtual_users", "ramp_up_seconds", "steady_state_seconds",
                "think_time_ms", "target_rps"):
        assert key in p, key
        assert isinstance(p[key], (int, float))


def test_medium_profile_defaults():
    p = build_profile(num_endpoints=5, target="medium")
    assert p["virtual_users"] == 50
    assert p["ramp_up_seconds"] == 60
    assert p["steady_state_seconds"] == 300
    assert p["think_time_ms"] == 500


def test_small_profile_has_fewer_vus_than_medium():
    assert build_profile(3, "small")["virtual_users"] < build_profile(3, "medium")["virtual_users"]


def test_large_profile_has_more_vus_than_medium():
    assert build_profile(3, "large")["virtual_users"] > build_profile(3, "medium")["virtual_users"]


def test_unknown_target_falls_back_to_medium():
    assert build_profile(3, target="ludicrous") == build_profile(3, target="medium")


def test_rps_scales_with_endpoint_count():
    assert build_profile(10)["target_rps"] > build_profile(2)["target_rps"]


def test_zero_endpoints_still_returns_safe_defaults():
    p = build_profile(0)
    assert p["target_rps"] >= 1
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/tools/test_load_profile_builder.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `tools/load_profile_builder.py` with license header followed by:

```python
"""Deterministic load-profile builder.

Subagent for F6 (perf_test_generator). Produces the fixed numeric constants
(virtual users, ramp-up, steady state, think time, target rps) so the LLM
only composes framework syntax around them instead of hallucinating timings.

Three targets: ``small`` (smoke), ``medium`` (default), ``large`` (stress).
"""

from __future__ import annotations

_TARGETS = {
    "small":  {"vus": 10,  "ramp": 30,  "steady": 120, "think_ms": 500},
    "medium": {"vus": 50,  "ramp": 60,  "steady": 300, "think_ms": 500},
    "large":  {"vus": 200, "ramp": 120, "steady": 600, "think_ms": 300},
}


def build_profile(num_endpoints: int, target: str = "medium") -> dict:
    """Return the fixed load-profile block for the named target."""
    t = _TARGETS.get(target) or _TARGETS["medium"]
    # RPS heuristic: vus / (think_time_s) * endpoint-count adjustment.
    # Keep deterministic and at least 1 rps.
    think_s = max(t["think_ms"] / 1000.0, 0.001)
    base_rps = t["vus"] / think_s
    scale = max(num_endpoints, 1) / 5.0
    target_rps = max(int(round(base_rps * scale)), 1)
    return {
        "virtual_users":        t["vus"],
        "ramp_up_seconds":      t["ramp"],
        "steady_state_seconds": t["steady"],
        "think_time_ms":        t["think_ms"],
        "target_rps":           target_rps,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/tools/test_load_profile_builder.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Hold for Commit 3.**

---

### Task 14: Order story fixture

**Files:**
- Create: `tests/fixtures/wave6a/order_story.txt`

- [ ] **Step 1: Create the fixture**

Create `tests/fixtures/wave6a/order_story.txt`:

```
Build an order-management API supporting create, list, get-by-id, and cancel.

Acceptance Criteria:
 - Orders have: id, customer_email, total, status (one of pending, paid, cancelled).
 - POST /orders creates a new order; returns 201 with the created resource.
 - GET /orders lists all orders, supports pagination via ?page and ?size.
 - GET /orders/{id} returns 200 with the order, or 404 if unknown.
 - POST /orders/{id}/cancel transitions a pending/paid order to cancelled; returns 409 if already cancelled.
 - Expected steady-state traffic: 500 requests/second during business hours.
```

- [ ] **Step 2: Hold for Commit 3.**

---

### Task 15: F6 mode + framework detectors

**Files:**
- Modify: `agents/perf_test_generator.py` (replace stub)
- Test: `tests/agents/test_perf_test_generator.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_perf_test_generator.py`:

```python
from agents.perf_test_generator import _detect_mode, _pick_framework


def test_detect_mode_prefix_wins():
    m = _detect_mode(file_path="anything.yaml",
                     content="openapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}",
                     custom_prompt="__mode__requirements\nthe story text")
    assert m == "requirements"


def test_detect_mode_yaml_source_is_spec():
    m = _detect_mode(file_path="openapi.yaml",
                     content="openapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}",
                     custom_prompt=None)
    assert m == "spec"


def test_detect_mode_plain_txt_is_requirements():
    m = _detect_mode(file_path="story.txt",
                     content="as a user I want to x",
                     custom_prompt=None)
    assert m == "requirements"


def test_detect_mode_openapi_prefix_is_spec():
    m = _detect_mode(file_path="story.txt",
                     content="",
                     custom_prompt="__openapi_spec__\nopenapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}")
    assert m == "spec"


def test_pick_framework_gatling_triggers():
    for lang in ("java", "scala", "gatling", "JAVA", " Scala "):
        assert _pick_framework(lang) == "gatling"


def test_pick_framework_default_is_jmeter():
    for lang in (None, "", "python", "typescript", "anything"):
        assert _pick_framework(lang) == "jmeter"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_perf_test_generator.py -v`
Expected: new tests FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Replace `agents/perf_test_generator.py` body (preserve license header) with:

```python
"""F6 — Performance / Load Test Script Generator.

Mode detection (spec vs. requirements) runs first, framework auto-pick
drives one Strands LLM call with framework-specific prompt, and
tools.load_profile_builder supplies the deterministic load constants
so the LLM does not hallucinate timings.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.openapi_parser import parse, extract_endpoints, OpenAPIParseError
from tools.load_profile_builder import build_profile
from db.queries.history import add_history

_CACHE_KEY = "perf_test_generator"

_METADATA_PATHS = {"/health", "/healthz", "/metrics", "/livez", "/readyz",
                   "/ready", "/live", "/status"}

_YAML_SNIFF = re.compile(r"^\s*(openapi|swagger)\s*:", re.IGNORECASE | re.MULTILINE)


def _detect_mode(file_path: str, content: str, custom_prompt: str | None) -> str:
    """Return 'spec' or 'requirements'."""
    if custom_prompt:
        if "__mode__requirements\n" in custom_prompt:
            return "requirements"
        if "__openapi_spec__\n" in custom_prompt:
            return "spec"
    ext = os.path.splitext(file_path)[1].lower()
    head = (content or "")[:1024]
    if ext in (".yaml", ".yml") and _YAML_SNIFF.search(head):
        return "spec"
    if ext == ".json" and ('"openapi"' in head or '"swagger"' in head):
        return "spec"
    return "requirements"


_GATLING_LANGS = {"java", "scala", "gatling"}


def _pick_framework(language: str | None) -> str:
    """Return 'gatling' or 'jmeter'."""
    if language and language.strip().lower() in _GATLING_LANGS:
        return "gatling"
    return "jmeter"


_JMETER_SYSTEM = """You are a performance engineer. Produce a COMPLETE, runnable Apache JMeter 5.x test plan (.jmx XML) for the API below.

Mandatory structure:
- <jmeterTestPlan version="1.2" properties="5.0"> root with <hashTree> children
- Exactly one TestPlan
- Exactly one ThreadGroup with:
    * num_threads      = {virtual_users}
    * ramp_time        = {ramp_up_seconds}
    * duration         = {steady_state_seconds}
    * scheduler        = true
- One TransactionController per endpoint
- One HTTPSamplerProxy per endpoint inside its TransactionController, using ${{baseUrl}} via a User Defined Variables block
- One ResponseAssertion per sampler checking response code starts with "2"
- One ConstantTimer with delay = {think_time_ms}
- SummaryReport and ViewResultsTree listeners attached at TestPlan level

Do not include any endpoint whose path is in: {metadata_paths}.

Return ONLY the complete plan wrapped in a single ```xml fenced block.

Endpoints:
{endpoint_table}

Title: {title}
"""

_GATLING_SYSTEM = """You are a performance engineer. Produce a COMPLETE, runnable Gatling 3.x Simulation.scala for the API below.

Mandatory structure:
- package-less file, class `LoadTest extends Simulation`
- `val httpProtocol = http.baseUrl("${{baseUrl}}")` — do NOT inline a real URL
- One `scenario("LoadTest")` chaining exec(http(...)) for every endpoint
- `.check(status.is(200))` or `.check(status.in(200 to 299))` per call
- `setUp(scn.inject(rampUsersPerSec(1) to ({target_rps}) during ({ramp_up_seconds} seconds)).protocols(httpProtocol))`
- `.maxDuration({steady_state_seconds} seconds)` on the setUp
- Insert `pause({think_time_ms} milliseconds)` between calls

Do not include any endpoint whose path is in: {metadata_paths}.

Return ONLY the complete Scala file wrapped in a single ```scala fenced block.

Endpoints:
{endpoint_table}

Title: {title}
"""

_STORY_NOTE = "\n\n(Requirements mode — no formal OpenAPI spec provided. Invent plausible REST paths consistent with the story.)"


def _endpoint_table(endpoints: list[dict]) -> str:
    lines = []
    for ep in endpoints:
        lines.append(f"- {ep['method']} {ep['path']}")
    return "\n".join(lines) or "(no endpoints — derive from narrative)"


def _filter_metadata(endpoints: list[dict]) -> list[dict]:
    return [ep for ep in endpoints if ep["path"] not in _METADATA_PATHS]


def _extract_code_block(text: str, fence: str) -> str:
    pat = rf"```{re.escape(fence)}\s*\n(.*?)```"
    m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_perf_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    # Full integration arrives in Task 16. Temporarily preserve a placeholder
    # that respects mode detection so the Task 15 tests pass.
    return {
        "markdown": "## Perf/Load Test Generator — scaffold (Task 15)",
        "summary": "F6 Task 15 scaffold",
        "output_path": None,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/agents/test_perf_test_generator.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Hold for Commit 3.**

---

### Task 16: F6 full `run_perf_test_generator` integration

**Files:**
- Modify: `agents/perf_test_generator.py` (replace stub with full integration)
- Test: `tests/agents/test_perf_test_generator.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_perf_test_generator.py`:

```python
import os
from unittest.mock import patch, MagicMock


_CANNED_JMETER = '''```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan testname="petstore"/>
    <hashTree>
      <Arguments testname="User Defined Variables">
        <elementProp name="baseUrl" elementType="Argument"><stringProp name="Argument.name">baseUrl</stringProp><stringProp name="Argument.value">https://api.example.test</stringProp></elementProp>
      </Arguments>
      <hashTree/>
      <ThreadGroup testname="Load" enabled="true">
        <stringProp name="ThreadGroup.num_threads">50</stringProp>
        <stringProp name="ThreadGroup.ramp_time">60</stringProp>
        <stringProp name="ThreadGroup.duration">300</stringProp>
      </ThreadGroup>
      <hashTree>
        <TransactionController testname="list pets"/>
        <hashTree>
          <HTTPSamplerProxy testname="GET /pets"/>
          <hashTree>
            <ResponseAssertion testname="2xx"/>
            <ConstantTimer><stringProp name="ConstantTimer.delay">500</stringProp></ConstantTimer>
          </hashTree>
        </hashTree>
        <TransactionController testname="create pet"/>
        <hashTree>
          <HTTPSamplerProxy testname="POST /pets"/>
          <hashTree/>
        </hashTree>
        <TransactionController testname="get pet"/>
        <hashTree>
          <HTTPSamplerProxy testname="GET /pets/${petId}"/>
          <hashTree/>
        </hashTree>
      </hashTree>
      <SummaryReport testname="Summary"/>
      <hashTree/>
      <ViewResultsTree testname="View Results Tree"/>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```'''


_CANNED_GATLING = '''```scala
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class LoadTest extends Simulation {
  val httpProtocol = http.baseUrl("${baseUrl}")
  val scn = scenario("LoadTest")
    .exec(http("list pets").get("/pets").check(status.in(200 to 299))).pause(500.milliseconds)
    .exec(http("create pet").post("/pets").body(StringBody("""{"name":"Rex"}""")).asJson.check(status.in(200 to 299))).pause(500.milliseconds)
    .exec(http("get pet").get("/pets/1").check(status.in(200 to 299))).pause(500.milliseconds)
  setUp(
    scn.inject(rampUsersPerSec(1) to (50) during (60 seconds))
       .protocols(httpProtocol)
  ).maxDuration(300 seconds)
}
```'''


def test_spec_mode_jmeter_writes_jmx(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/petstore_openapi.yaml",
                        "r", encoding="utf-8").read()
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_JMETER
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j1",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h1", language="python", custom_prompt=None,
        )
    assert result["output_path"].endswith("plan.jmx")
    assert os.path.isfile(result["output_path"])
    body = open(result["output_path"], "r", encoding="utf-8").read()
    assert "<jmeterTestPlan" in body
    assert "HTTPSamplerProxy" in body


def test_spec_mode_gatling_writes_scala(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/petstore_openapi.yaml",
                        "r", encoding="utf-8").read()
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_GATLING
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j2",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h2", language="scala", custom_prompt=None,
        )
    assert result["output_path"].endswith("Simulation.scala")
    body = open(result["output_path"], "r", encoding="utf-8").read()
    assert "class LoadTest" in body
    assert "setUp" in body


def test_requirements_mode_uses_story_text(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/order_story.txt",
                 "r", encoding="utf-8").read()
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_JMETER
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j3",
            file_path="order_story.txt", content=story,
            file_hash="h3", language=None,
            custom_prompt="__mode__requirements\n" + story,
        )
    assert result["output_path"].endswith("plan.jmx")
    assert "requirements" in result["summary"].lower() or "story" in result["summary"].lower()


def test_empty_llm_response_returns_error(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/petstore_openapi.yaml",
                        "r", encoding="utf-8").read()
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = "I cannot comply."  # no fenced block
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j4",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h4", language="python", custom_prompt=None,
        )
    assert result.get("output_path") is None
    assert "empty" in result["summary"].lower() or "failed" in result["summary"].lower() or "error" in result["summary"].lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_perf_test_generator.py -v`
Expected: the 4 new tests FAIL (scaffold returns placeholder, never writes artifacts).

- [ ] **Step 3: Implement the full `run_perf_test_generator`**

Replace the scaffold `run_perf_test_generator` in `agents/perf_test_generator.py` with:

```python
def run_perf_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    mode = _detect_mode(file_path, content, custom_prompt)
    framework = _pick_framework(language)

    title = "api"
    endpoints: list[dict] = []
    if mode == "spec":
        # Resolve spec body (prefix or source)
        if custom_prompt and "__openapi_spec__\n" in custom_prompt:
            spec_body = custom_prompt.split("__openapi_spec__\n", 1)[1]
        else:
            spec_body = content
        try:
            spec = parse(spec_body)
        except OpenAPIParseError as exc:
            return {
                "markdown": f"## Perf/Load Test Generator — error\n\n{exc}",
                "summary": f"F6 error: {exc}",
                "output_path": None,
            }
        title = (spec.get("info") or {}).get("title") or title
        endpoints = _filter_metadata(extract_endpoints(spec))

    profile = build_profile(num_endpoints=max(len(endpoints), 3), target="medium")

    # Build system prompt
    if framework == "gatling":
        system = _GATLING_SYSTEM.format(
            virtual_users=profile["virtual_users"],
            ramp_up_seconds=profile["ramp_up_seconds"],
            steady_state_seconds=profile["steady_state_seconds"],
            think_time_ms=profile["think_time_ms"],
            target_rps=profile["target_rps"],
            metadata_paths=", ".join(sorted(_METADATA_PATHS)),
            endpoint_table=_endpoint_table(endpoints),
            title=title,
        )
    else:
        system = _JMETER_SYSTEM.format(
            virtual_users=profile["virtual_users"],
            ramp_up_seconds=profile["ramp_up_seconds"],
            steady_state_seconds=profile["steady_state_seconds"],
            think_time_ms=profile["think_time_ms"],
            target_rps=profile["target_rps"],
            metadata_paths=", ".join(sorted(_METADATA_PATHS)),
            endpoint_table=_endpoint_table(endpoints),
            title=title,
        )

    if mode == "requirements":
        system += _STORY_NOTE

    # LLM call
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, system))
    user_prompt = (
        "Generate the performance test plan now using the endpoint list above."
        if mode == "spec"
        else f"Generate the performance test plan for this narrative:\n\n{content}"
    )
    raw = str(agent(user_prompt))

    fence = "scala" if framework == "gatling" else "xml"
    body = _extract_code_block(raw, fence)

    # Validate non-empty and shape-correct
    ok = bool(body.strip())
    if framework == "jmeter" and "<jmeterTestPlan" not in body:
        ok = False
    if framework == "gatling" and "Simulation" not in body:
        ok = False

    if not ok:
        return {
            "markdown": f"## Perf/Load Test Generator — LLM output empty/invalid",
            "summary": f"F6 error: LLM returned empty or invalid {framework} content",
            "output_path": None,
        }

    # Write artifact
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "perf_tests")
    os.makedirs(out_dir, exist_ok=True)
    suffix = "Simulation.scala" if framework == "gatling" else "plan.jmx"
    output_path = os.path.join(out_dir, suffix)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(body)

    # Report
    md_parts = [
        f"## Perf/Load Test Generator — `{title}`",
        f"- **Mode:** {mode}",
        f"- **Framework:** {framework}",
        f"- **Endpoints:** {len(endpoints)}" + (" (from narrative)" if mode == "requirements" else ""),
        f"- **Load profile:** {profile['virtual_users']} VUs, "
        f"{profile['ramp_up_seconds']}s ramp, "
        f"{profile['steady_state_seconds']}s steady, "
        f"{profile['think_time_ms']}ms think, "
        f"~{profile['target_rps']} rps",
        f"- **Output:** `{output_path}`",
        f"\n### Generated plan\n\n```{fence}\n{body}\n```",
    ]
    markdown = "\n".join(md_parts)
    summary = f"Generated {framework} plan ({mode} mode) for {len(endpoints) or 'story-derived'} endpoints."

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": output_path,
        "framework": framework,
        "mode": mode,
        "profile": profile,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
```

- [ ] **Step 4: Run all F6 tests**

Run: `pytest tests/agents/test_perf_test_generator.py tests/tools/test_load_profile_builder.py -v`
Expected: all PASS.

- [ ] **Step 5: Full suite**

Run: `pytest -x`
Expected: all PASS.

- [ ] **Step 6: Hold for Commit 3.**

---

### Task 17: Commit 3 — F6 fill

- [ ] **Step 1: Verify diff**

Run: `git status`. Expected files:
- New: `tools/load_profile_builder.py`, `tests/tools/test_load_profile_builder.py`, `tests/fixtures/wave6a/order_story.txt`
- Modified: `agents/perf_test_generator.py`, `tests/agents/test_perf_test_generator.py`

- [ ] **Step 2: Commit**

```bash
git add agents/perf_test_generator.py tools/load_profile_builder.py \
        tests/agents/test_perf_test_generator.py tests/tools/test_load_profile_builder.py \
        tests/fixtures/wave6a/order_story.txt
git -c user.name="B.VigneshKumar" -c user.email="ic19939@gmail.com" commit -m "feat(phase6): implement F6 perf_test_generator

Auto-picks JMeter or Gatling from sidebar language (java/scala/gatling
→ Gatling, else JMeter). Mode detection supports spec-in (OpenAPI)
and requirements-in (narrative). Deterministic tools/load_profile_builder
supplies virtual-user counts, ramp, steady-state, and think-time
constants so the LLM does not hallucinate load parameters. Filters
standard metadata endpoints out of the steady-state load."
```

---

# PART D — F10 FILL (Commit 4)

---

### Task 18: `tools/test_scanner.py`

**Files:**
- Create: `tools/test_scanner.py`
- Test: `tests/tools/test_test_scanner.py`

- [ ] **Step 1: Create pre-fixtures for the scanner**

Create `tests/fixtures/wave6a/reset_password_tests/test_reset.py`:

```python
import pytest


def test_reset_link_visible_on_login_page():
    """The 'Forgot password' link must be visible on the login page."""
    assert True


def test_known_email_triggers_reset_mail():
    """A reset mail is sent within 30 seconds of submitting a known email."""
    assert True


@pytest.mark.negative
def test_unknown_email_returns_generic_200():
    """Unknown email → generic 200, no user enumeration."""
    assert True
```

Create `tests/fixtures/wave6a/reset_password_tests/test_unmapped.py`:

```python
def test_admin_audit_log_flush():
    """Orphan — unrelated to any acceptance criterion."""
    assert True
```

- [ ] **Step 2: Write failing tests**

Create `tests/tools/test_test_scanner.py`:

```python
from tools.test_scanner import scan_tests


def test_scans_python_pytest_tests():
    tests = scan_tests("tests/fixtures/wave6a/reset_password_tests")
    names = [t["test_name"] for t in tests]
    assert "test_reset_link_visible_on_login_page" in names
    assert "test_known_email_triggers_reset_mail" in names
    assert "test_unknown_email_returns_generic_200" in names
    assert "test_admin_audit_log_flush" in names
    assert len(tests) >= 4


def test_returns_kind_and_path():
    tests = scan_tests("tests/fixtures/wave6a/reset_password_tests")
    for t in tests:
        assert "kind" in t
        assert "file" in t
        assert t["kind"] == "pytest"
        assert t["file"].endswith(".py")


def test_returns_snippet_with_docstring():
    tests = scan_tests("tests/fixtures/wave6a/reset_password_tests")
    link_test = next(t for t in tests if t["test_name"] == "test_reset_link_visible_on_login_page")
    assert "Forgot password" in link_test.get("snippet", "")


def test_picks_up_feature_files(tmp_path):
    (tmp_path / "auth.feature").write_text(
        "Feature: Password reset\n"
        "  Scenario: User resets password\n"
        "    Given I am on the login page\n"
        "    When I click 'Forgot password'\n"
        "    Then I receive a reset email\n"
        "  Scenario Outline: Invalid email handling\n"
        "    Given email <email>\n"
        "    When I submit\n"
        "    Then I see <msg>\n",
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    scenarios = [t for t in tests if t["kind"] == "gherkin"]
    assert len(scenarios) >= 2


def test_picks_up_java_junit(tmp_path):
    (tmp_path / "LoginTests.java").write_text(
        "import org.junit.jupiter.api.Test;\n"
        "class LoginTests {\n"
        "  @Test void testForgotPasswordLinkVisible() {}\n"
        "  @Test void testResetEmailSent() {}\n"
        "}\n",
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "junit"}
    assert "testForgotPasswordLinkVisible" in names
    assert "testResetEmailSent" in names


def test_picks_up_jest_ts(tmp_path):
    (tmp_path / "login.test.ts").write_text(
        'describe("login", () => {\n'
        '  it("shows forgot password link", () => {});\n'
        '  test("sends reset email within 30s", () => {});\n'
        '});\n',
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "jest"}
    assert "shows forgot password link" in names
    assert "sends reset email within 30s" in names


def test_picks_up_jmx_transactions(tmp_path):
    (tmp_path / "plan.jmx").write_text(
        '<jmeterTestPlan><hashTree>'
        '<TransactionController testname="reset password flow"/>'
        '<TransactionController testname="login flow"/>'
        '</hashTree></jmeterTestPlan>',
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "jmeter"}
    assert "reset password flow" in names


def test_picks_up_postman_items(tmp_path):
    import json as _json
    (tmp_path / "api_collection.json").write_text(
        _json.dumps({
            "info": {"name": "x", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": [{"name": "POST /reset"}, {"name": "GET /login"}],
        }),
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "postman"}
    assert "POST /reset" in names


def test_nonexistent_path_returns_empty():
    assert scan_tests("tests/fixtures/wave6a/does_not_exist") == []
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/tools/test_test_scanner.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `tools/test_scanner.py`**

Create `tools/test_scanner.py` with license header followed by:

```python
"""Deterministic test-file scanner.

Subagent for F10 (traceability_matrix). Walks a folder and extracts
test identities by file type — no LLM. Emits a flat list of
``{file, test_name, kind, line, snippet}`` records that the matrix
builder consumes.
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterable

_PYTHON_TEST_RE = re.compile(r"^\s*def\s+(test_\w+)\s*\(", re.MULTILINE)
_PY_DOCSTRING_RE = re.compile(r'^\s*"""(.+?)"""', re.DOTALL | re.MULTILINE)

_JUNIT_TEST_RE = re.compile(
    r"@Test(?:\([^)]*\))?\s*(?:\w+\s+)*(?:void|[A-Z]\w*)\s+(\w+)\s*\(",
)
_XUNIT_FACT_RE = re.compile(r"\[(Fact|Theory)\][^\[]*?(?:public|internal|private)?\s+\w+\s+(\w+)\s*\(")

_JEST_IT_RE = re.compile(r"""(?:^|\s)(?:it|test)\s*\(\s*['"`]([^'"`]+)['"`]""", re.MULTILINE)

_GHERKIN_SCENARIO_RE = re.compile(r"^\s*Scenario(?:\s*Outline)?\s*:\s*(.+)$", re.MULTILINE)
_ROBOT_CASE_RE = re.compile(r"^\*\*\*\s*Test Cases\s*\*\*\*\s*$(.*?)(?:^\*\*\*|\Z)",
                            re.MULTILINE | re.DOTALL)
_ROBOT_NAME_RE = re.compile(r"^([^\s#].+)$", re.MULTILINE)

_JMX_TXN_RE = re.compile(r'<TransactionController[^>]*testname="([^"]+)"')

_POSTMAN_SCHEMA_MARK = "schema.getpostman.com/json/collection/v2.1.0"


def scan_tests(root: str) -> list[dict]:
    """Return test records for every recognised file under ``root``."""
    if not os.path.isdir(root):
        return []
    out: list[dict] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                out.extend(_scan_one(full))
            except (OSError, ValueError):
                continue
    return out


def _scan_one(path: str) -> Iterable[dict]:
    name = os.path.basename(path).lower()
    if name.endswith(".py"):
        if name.startswith("test_") or name.endswith("_test.py") or "/tests/" in path.replace("\\", "/"):
            yield from _scan_pytest(path)
        return
    if name.endswith(".java") and ("test" in name):
        yield from _scan_junit(path)
        return
    if name.endswith(".cs") and ("test" in name):
        yield from _scan_xunit(path)
        return
    if name.endswith(".test.ts") or name.endswith(".test.js") or \
       name.endswith(".spec.ts") or name.endswith(".spec.js"):
        yield from _scan_jest(path)
        return
    if name.endswith(".feature"):
        yield from _scan_gherkin(path)
        return
    if name.endswith(".robot"):
        yield from _scan_robot(path)
        return
    if name.endswith(".jmx"):
        yield from _scan_jmx(path)
        return
    if name.endswith(".json"):
        yield from _scan_postman(path)
        return


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _scan_pytest(path: str) -> Iterable[dict]:
    text = _read(path)
    lines = text.splitlines()
    for m in _PYTHON_TEST_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        # Snippet: the line + next 3 lines (often the docstring)
        snippet = "\n".join(lines[line_no - 1:line_no + 4])
        yield {"file": path, "test_name": name, "kind": "pytest",
               "line": line_no, "snippet": snippet}


def _scan_junit(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _JUNIT_TEST_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "junit",
               "line": line_no, "snippet": name}


def _scan_xunit(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _XUNIT_FACT_RE.finditer(text):
        name = m.group(2)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "xunit",
               "line": line_no, "snippet": name}


def _scan_jest(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _JEST_IT_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "jest",
               "line": line_no, "snippet": name}


def _scan_gherkin(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _GHERKIN_SCENARIO_RE.finditer(text):
        name = m.group(1).strip()
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "gherkin",
               "line": line_no, "snippet": name}


def _scan_robot(path: str) -> Iterable[dict]:
    text = _read(path)
    for block_m in _ROBOT_CASE_RE.finditer(text):
        block = block_m.group(1) or ""
        base_line = text[:block_m.start(1)].count("\n") + 1
        for name_m in _ROBOT_NAME_RE.finditer(block):
            name = name_m.group(1).strip()
            if not name or name.startswith("#"):
                continue
            line_no = base_line + block[:name_m.start()].count("\n")
            yield {"file": path, "test_name": name, "kind": "robot",
                   "line": line_no, "snippet": name}


def _scan_jmx(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _JMX_TXN_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "jmeter",
               "line": line_no, "snippet": name}


def _scan_postman(path: str) -> Iterable[dict]:
    try:
        text = _read(path)
        if _POSTMAN_SCHEMA_MARK not in text:
            return
        doc = json.loads(text)
    except (ValueError, OSError):
        return
    for idx, item in enumerate(doc.get("item") or []):
        if isinstance(item, dict) and item.get("name"):
            yield {"file": path, "test_name": item["name"], "kind": "postman",
                   "line": idx + 1, "snippet": item["name"]}
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/tools/test_test_scanner.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 6: Hold for Commit 4.**

---

### Task 19: F10 remaining fixtures

**Files:**
- Create: `tests/fixtures/wave6a/reset_password_story.txt`
- Create: `tests/fixtures/wave6a/reset_password_src/reset_password.py`

- [ ] **Step 1: Create story fixture**

Create `tests/fixtures/wave6a/reset_password_story.txt`:

```
As a registered user, I want to reset my password so that I can recover access.

Acceptance Criteria:
 AC-1: A "Forgot password" link is visible on the login page.
 AC-2: Submitting a known email sends a reset mail within 30 s.
 AC-3: The reset link expires 24 h after issue.
 AC-4: Submitting an unknown email returns a generic 200 OK message (no user enumeration).
```

- [ ] **Step 2: Create code-folder fixture**

Create `tests/fixtures/wave6a/reset_password_src/reset_password.py`:

```python
def send_reset_mail(email: str) -> bool:
    """Email the password reset link to ``email`` — returns True when queued."""
    return True


def validate_token(token: str, issued_at: float, now: float) -> bool:
    """Return True while the reset token is still within 24h of issue."""
    return (now - issued_at) <= 24 * 3600
```

- [ ] **Step 3: Hold for Commit 4.**

---

### Task 20: F10 AC extraction + Jaccard matcher

**Files:**
- Modify: `agents/traceability_matrix.py` (replace stub body, preserve license header)
- Test: `tests/agents/test_traceability_matrix.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_traceability_matrix.py`:

```python
import json
from unittest.mock import patch, MagicMock
from agents.traceability_matrix import (
    _extract_acs_deterministic, _score_pair, _jaccard_match, _is_ambiguous,
    _STOP_WORDS,
)


def test_extract_acs_from_numbered_block():
    story = (
        "AC-1: Forgot password link is visible on the login page.\n"
        "AC-2: Reset mail within 30s for known emails.\n"
        "AC-3: Reset link expires 24 hours after issue.\n"
    )
    acs = _extract_acs_deterministic(story)
    assert len(acs) == 3
    assert acs[0]["id"] == "AC-1"
    assert "forgot" in acs[0]["text"].lower()


def test_extract_acs_from_bullets():
    story = (
        "Acceptance Criteria:\n"
        " - A 'Forgot password' link is visible on the login page.\n"
        " - Submitting a known email sends a reset mail within 30 s.\n"
    )
    acs = _extract_acs_deterministic(story)
    assert len(acs) == 2


def test_score_pair_high_for_overlapping_words():
    score = _score_pair("forgot password link login page",
                        "test_forgot_password_link_visible")
    assert score >= 0.5


def test_score_pair_low_for_unrelated():
    score = _score_pair("forgot password link login page", "test_audit_log_flush")
    assert score < 0.3


def test_jaccard_match_locks_high_confidence():
    acs = [{"id": "AC-1", "text": "forgot password link visible"}]
    tests = [
        {"test_name": "test_forgot_password_link_visible", "snippet": "", "file": "x"},
        {"test_name": "test_unrelated_audit", "snippet": "", "file": "x"},
    ]
    locks, ambiguous = _jaccard_match(acs, tests)
    assert "AC-1" in locks
    assert locks["AC-1"][0]["test_name"] == "test_forgot_password_link_visible"


def test_jaccard_match_flags_ambiguous_on_close_scores():
    acs = [{"id": "AC-1", "text": "send reset email"}]
    tests = [
        {"test_name": "test_send_reset_email_fast", "snippet": "", "file": "x"},
        {"test_name": "test_send_reset_email_slow", "snippet": "", "file": "x"},
    ]
    locks, ambiguous = _jaccard_match(acs, tests)
    # Two near-identical names should not lock — ambiguous.
    assert "AC-1" not in locks
    assert "AC-1" in ambiguous


def test_stop_words_filtered():
    assert "the" in _STOP_WORDS
    assert "a"   in _STOP_WORDS
    assert "forgot" not in _STOP_WORDS


def test_is_ambiguous_zero_tests():
    assert _is_ambiguous(scores=[], top=0.0) is True


def test_is_ambiguous_mid_score():
    assert _is_ambiguous(scores=[0.55], top=0.55) is True


def test_is_ambiguous_single_high_score():
    assert _is_ambiguous(scores=[0.9], top=0.9) is False
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: new tests FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Replace `agents/traceability_matrix.py` body (preserve license header) with:

```python
"""F10 — Traceability Matrix + Coverage Gap Finder.

Pipeline:
  1. Resolve stories (prefix → source) and extract ACs with a determined
     numbered-block / bullet scanner; fall back to an LLM pass when the
     scanner finds nothing.
  2. Resolve the tests folder (prefix or source_ref split) and scan it
     via tools.test_scanner (no LLM).
  3. Auto-include same-run Reports/<ts>/api_tests/ and perf_tests/.
  4. Match AC ↔ test with Jaccard, then a single batched LLM pass over
     ambiguous rows.
  5. Optionally call agents.test_coverage.run_test_coverage as a subagent.
  6. Emit matrix.csv, matrix.md, gaps.md.
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime
from typing import Any

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.cache import check_cache, write_cache
from tools.spec_fetcher import fetch_spec, SpecFetchError
from tools.test_scanner import scan_tests
from db.queries.history import add_history

_CACHE_KEY = "traceability_matrix"

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "by", "as", "is", "are", "be", "been", "being", "at", "that",
    "this", "it", "its", "from", "i", "you", "we", "they", "he", "she",
    "so", "do", "does", "should", "will", "can", "must", "may", "shall",
    "test", "tests", "testing", "case", "cases",
}

_AC_NUMBERED_RE = re.compile(
    r"^\s*(?:AC[-\s]?\d+|[0-9]+(?:\.|\)))\s*[:.\)]?\s*(.+)$",
    re.MULTILINE,
)
_AC_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)


def _normalise_tokens(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-z][A-Za-z0-9]+", text.lower())
    return {t for t in toks if t not in _STOP_WORDS and len(t) > 2}


def _score_pair(ac_text: str, test_blob: str) -> float:
    a = _normalise_tokens(ac_text)
    b = _normalise_tokens(test_blob.replace("_", " "))
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union)


def _extract_acs_deterministic(story: str) -> list[dict]:
    """Return ``[{id, text}]`` or empty list when nothing matched."""
    hits: list[str] = []
    for m in _AC_NUMBERED_RE.finditer(story):
        text = m.group(1).strip()
        if text:
            hits.append(text)
    if not hits:
        for m in _AC_BULLET_RE.finditer(story):
            text = m.group(1).strip()
            if text and len(text) > 10:
                hits.append(text)
    return [{"id": f"AC-{i+1}", "text": t} for i, t in enumerate(hits)]


_AC_EXTRACT_PROMPT = """You are a QA analyst extracting acceptance criteria from a user story.

Return STRICT JSON only (no commentary) matching:
{
  "acs": [
    {"id": "AC-1", "text": "..."},
    {"id": "AC-2", "text": "..."}
  ]
}

Rules:
- One AC per observable outcome (link visible, email sent, etc.).
- IDs are sequential AC-1, AC-2, ...
- Preserve the original phrasing; do not invent new criteria.
- Emit 1-15 ACs. If the story has fewer implied criteria, emit just those.
"""


def _extract_acs_llm(story: str, custom_prompt: str | None) -> list[dict]:
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _AC_EXTRACT_PROMPT))
    raw = str(agent(f"Extract acceptance criteria from this story:\n\n{story}"))
    try:
        payload = parse_json_response(raw)
    except Exception:
        return []
    acs = payload.get("acs") or []
    return [{"id": a.get("id") or f"AC-{i+1}", "text": a.get("text", "")}
            for i, a in enumerate(acs) if a.get("text")]


def _is_ambiguous(scores: list[float], top: float) -> bool:
    """An AC is ambiguous if:
      - no test scores >= 0.5, OR
      - top score is between 0.5 and 0.7 (inclusive-exclusive), OR
      - two or more scores are >= 0.7 and within 0.1 of each other.
    """
    high = [s for s in scores if s >= 0.7]
    if not scores:
        return True
    if top < 0.5:
        return True
    if 0.5 <= top < 0.7:
        return True
    if len(high) >= 2:
        second = sorted(scores, reverse=True)[1]
        if top - second < 0.1:
            return True
    return False


def _jaccard_match(acs: list[dict], tests: list[dict]) -> tuple[dict, dict]:
    """Return (locks, ambiguous).

    - locks:      {ac_id: [test_record, ...]} — confidently matched
    - ambiguous:  {ac_id: [(test_record, score), ...]}  — top 5 candidates
    """
    locks: dict[str, list[dict]] = {}
    ambiguous: dict[str, list[tuple[dict, float]]] = {}
    for ac in acs:
        scored: list[tuple[dict, float]] = []
        for t in tests:
            blob = f"{t.get('test_name', '')} {t.get('snippet', '')}"
            s = _score_pair(ac["text"], blob)
            scored.append((t, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[0][1] if scored else 0.0
        just_scores = [s for _, s in scored]
        if _is_ambiguous(just_scores, top):
            ambiguous[ac["id"]] = scored[:5]
        else:
            # Lock the top test
            locks[ac["id"]] = [scored[0][0]]
    return locks, ambiguous


_BATCH_MATCH_PROMPT = """You are a QA traceability analyst.

For each ambiguous acceptance criterion below, pick the tests (0 or more)
that genuinely verify it. Be conservative — do not guess.

Return STRICT JSON only:
{
  "matches": {
    "AC-1": ["test_name_a", "test_name_b"],
    "AC-2": []
  }
}

Rules:
- test ids are the exact test_name strings shown below.
- Emit an entry for every ambiguous AC even if the list is empty.
- Do not invent test names.
"""


def _llm_match_ambiguous(ambiguous: dict, custom_prompt: str | None) -> dict[str, list[str]]:
    if not ambiguous:
        return {}
    payload_lines = []
    for ac_id, cands in ambiguous.items():
        ac_text = cands[0][0].get("__ac_text__") if cands else ""
        # We need AC text — pass it in separately below.
        payload_lines.append(f"\n### {ac_id}")
        for idx, (t, score) in enumerate(cands, start=1):
            payload_lines.append(f"{idx}. {t['test_name']} "
                                 f"(kind={t.get('kind')}, score={score:.2f})")
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _BATCH_MATCH_PROMPT))
    raw = str(agent("\n".join(payload_lines)))
    try:
        payload = parse_json_response(raw)
    except Exception:
        return {}
    matches = payload.get("matches") or {}
    return {k: list(v) for k, v in matches.items() if isinstance(v, list)}


def run_traceability_matrix(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    # Full integration arrives in Task 22 (matrix builder + orchestration).
    # Preserve a placeholder that keeps Task 1 dispatch test passing.
    return {
        "markdown": "## Traceability Matrix — scaffold (Task 20)",
        "summary": "F10 Task 20 scaffold",
        "output_path": None,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Hold for Commit 4.**

---

### Task 21: F10 matrix builder helper

**Files:**
- Modify: `agents/traceability_matrix.py` (add `_build_matrix_rows`, `_write_artifacts`, `_resolve_inputs`)
- Test: `tests/agents/test_traceability_matrix.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_traceability_matrix.py`:

```python
import csv as _csv
from agents.traceability_matrix import _build_matrix_rows, _write_artifacts, _resolve_inputs


def test_build_matrix_rows_status_rules():
    acs = [{"id": "AC-1", "text": "reset link visible"},
           {"id": "AC-2", "text": "reset email sent fast"},
           {"id": "AC-3", "text": "token expires in 24h"}]
    mapping = {
        "AC-1": [{"test_name": "test_reset_visible", "kind": "pytest", "file": "a"}],
        "AC-2": [{"test_name": "test_reset_email", "kind": "pytest", "file": "a"}],
        "AC-3": [],
    }
    coverage = {"test_reset_visible": 90.0, "test_reset_email": 40.0}
    rows = _build_matrix_rows(acs, mapping, coverage)
    by_id = {r["AC_ID"]: r for r in rows}
    assert by_id["AC-1"]["Status"] == "green"
    assert by_id["AC-2"]["Status"] == "amber"  # coverage < 70%
    assert by_id["AC-3"]["Status"] == "red"    # no tests


def test_build_matrix_rows_no_coverage_column_is_na():
    acs = [{"id": "AC-1", "text": "x"}]
    mapping = {"AC-1": [{"test_name": "test_x", "kind": "pytest", "file": "a"}]}
    rows = _build_matrix_rows(acs, mapping, coverage=None)
    assert rows[0]["Coverage_%"] == "n/a"
    assert rows[0]["Status"] == "green"


def test_write_artifacts_produces_csv_md_gaps(tmp_path):
    acs = [{"id": "AC-1", "text": "x"}, {"id": "AC-2", "text": "y"}]
    mapping = {"AC-1": [{"test_name": "test_x", "kind": "pytest", "file": "a"}],
               "AC-2": []}
    orphans = [{"test_name": "test_orphan", "kind": "pytest", "file": "b"}]
    _write_artifacts(out_dir=str(tmp_path), acs=acs, mapping=mapping,
                     orphans=orphans, coverage=None)
    csv_path = tmp_path / "matrix.csv"
    md_path = tmp_path / "matrix.md"
    gaps_path = tmp_path / "gaps.md"
    assert csv_path.exists()
    assert md_path.exists()
    assert gaps_path.exists()
    # CSV parses and has two rows
    rows = list(_csv.DictReader(open(csv_path, "r", encoding="utf-8")))
    assert len(rows) == 2
    # Gaps mentions orphan + red AC
    gaps_body = gaps_path.read_text(encoding="utf-8")
    assert "test_orphan" in gaps_body
    assert "AC-2" in gaps_body


def test_resolve_inputs_from_prefixes(tmp_path):
    tests_dir = tmp_path / "t"
    tests_dir.mkdir()
    src_dir = tmp_path / "s"
    src_dir.mkdir()
    prompt = (
        "__stories__\nAC-1: foo.\n"
        f"__tests_dir__={tests_dir}\n"
        f"__src_dir__={src_dir}\n"
    )
    res = _resolve_inputs(file_path="ignored", content="",
                          custom_prompt=prompt)
    assert "AC-1" in res["stories"]
    assert res["tests_dir"] == str(tests_dir)
    assert res["src_dir"]   == str(src_dir)


def test_resolve_inputs_from_triple_colon_source_ref(tmp_path):
    t = tmp_path / "t"; t.mkdir()
    s = tmp_path / "s"; s.mkdir()
    story_file = tmp_path / "story.txt"
    story_file.write_text("AC-1: foo.\n", encoding="utf-8")
    joined = f"{story_file}::{t}::{s}"
    res = _resolve_inputs(file_path=joined, content="AC-1: foo.\n",
                          custom_prompt=None)
    assert res["tests_dir"] == str(t)
    assert res["src_dir"]   == str(s)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: new tests FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Append to `agents/traceability_matrix.py` (before `run_traceability_matrix`):

```python
def _build_matrix_rows(acs: list[dict], mapping: dict[str, list[dict]],
                       coverage: dict[str, float] | None) -> list[dict]:
    rows: list[dict] = []
    for ac in acs:
        tests = mapping.get(ac["id"]) or []
        test_names = ", ".join(t["test_name"] for t in tests) or ""
        kinds = ", ".join(sorted({t["kind"] for t in tests})) or ""
        cov_str = "n/a"
        status = "red" if not tests else "green"
        if coverage is not None and tests:
            covs = [coverage.get(t["test_name"], 0.0) for t in tests]
            avg = sum(covs) / len(covs) if covs else 0.0
            cov_str = f"{avg:.0f}"
            if avg < 70.0:
                status = "amber"
        rows.append({
            "AC_ID":       ac["id"],
            "AC_Text":     ac["text"],
            "Tests":       test_names,
            "Kinds":       kinds,
            "Coverage_%":  cov_str,
            "Status":      status,
        })
    return rows


def _write_artifacts(out_dir: str, acs: list[dict],
                     mapping: dict[str, list[dict]],
                     orphans: list[dict],
                     coverage: dict[str, float] | None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rows = _build_matrix_rows(acs, mapping, coverage)

    csv_path = os.path.join(out_dir, "matrix.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["AC_ID", "AC_Text", "Tests",
                                                "Kinds", "Coverage_%", "Status"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    md_lines = [
        "| AC | Text | Tests | Kinds | Coverage % | Status |",
        "|----|------|-------|-------|------------|--------|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['AC_ID']} | {r['AC_Text']} | {r['Tests'] or '-'} | "
            f"{r['Kinds'] or '-'} | {r['Coverage_%']} | {r['Status']} |"
        )
    md_path = os.path.join(out_dir, "matrix.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")

    gaps_lines = ["## Traceability Gaps\n"]
    red = [r for r in rows if r["Status"] == "red"]
    amber = [r for r in rows if r["Status"] == "amber"]
    if red:
        gaps_lines.append("### Red — ACs with no tests")
        for r in red:
            gaps_lines.append(f"- **{r['AC_ID']}** — {r['AC_Text']}")
    if amber:
        gaps_lines.append("\n### Amber — ACs covered under 70%")
        for r in amber:
            gaps_lines.append(f"- **{r['AC_ID']}** — {r['AC_Text']} (coverage {r['Coverage_%']}%)")
    if orphans:
        gaps_lines.append("\n### Orphan tests — match no AC")
        for o in orphans:
            gaps_lines.append(f"- `{o['test_name']}` ({o['kind']}) — `{o['file']}`")
    gaps_path = os.path.join(out_dir, "gaps.md")
    with open(gaps_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(gaps_lines) + "\n")

    return {"csv": csv_path, "md": md_path, "gaps": gaps_path, "rows": rows}


def _resolve_inputs(file_path: str, content: str, custom_prompt: str | None) -> dict:
    stories = ""
    tests_dir: str | None = None
    src_dir: str | None = None

    # Prefix wins
    if custom_prompt:
        if "__stories__\n" in custom_prompt:
            # body is everything between the prefix and the next __*__ prefix or end
            body = custom_prompt.split("__stories__\n", 1)[1]
            body = re.split(r"^__\w+__", body, flags=re.MULTILINE)[0].strip()
            stories = body
        m = re.search(r"^__tests_dir__=(.+)$", custom_prompt, re.MULTILINE)
        if m:
            tests_dir = m.group(1).strip()
        m = re.search(r"^__src_dir__=(.+)$", custom_prompt, re.MULTILINE)
        if m:
            src_dir = m.group(1).strip()

    # Source-ref fallback: "stories::tests_dir::src_dir" join
    if "::" in file_path and not stories:
        parts = file_path.split("::")
        if len(parts) >= 1 and os.path.isfile(parts[0]):
            with open(parts[0], "r", encoding="utf-8") as fh:
                stories = fh.read()
        if tests_dir is None and len(parts) >= 2:
            tests_dir = parts[1]
        if src_dir is None and len(parts) >= 3:
            src_dir = parts[2]

    # Source content fallback
    if not stories and content:
        # Treat content as stories only if source looks like text/md
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".txt", ".md", "") or "::" not in file_path:
            stories = content

    # Jira/ADO/Qase URL support through spec_fetcher
    if stories and re.match(r"^https?://", stories.strip().splitlines()[0] or ""):
        url = stories.strip().splitlines()[0]
        try:
            spec = fetch_spec(url)
            stories = spec.get("body") or spec.get("description") or stories
        except SpecFetchError:
            pass

    return {"stories": stories, "tests_dir": tests_dir, "src_dir": src_dir}
```

Also add, near the other imports in `agents/traceability_matrix.py`:

```python
import csv
```

(it's referenced by `_write_artifacts`).

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: all PASS.

- [ ] **Step 5: Hold for Commit 4.**

---

### Task 22: F10 full `run_traceability_matrix` orchestration

**Files:**
- Modify: `agents/traceability_matrix.py` (replace placeholder `run_traceability_matrix`)
- Test: `tests/agents/test_traceability_matrix.py` (append integration tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_traceability_matrix.py`:

```python
import os
from unittest.mock import patch, MagicMock


_CANNED_AC_EXTRACT = json.dumps({
    "acs": [
        {"id": "AC-1", "text": "A 'Forgot password' link is visible on the login page."},
        {"id": "AC-2", "text": "Submitting a known email sends a reset mail within 30 s."},
        {"id": "AC-3", "text": "The reset link expires 24 h after issue."},
        {"id": "AC-4", "text": "Submitting an unknown email returns a generic 200 OK message."},
    ]
})

_CANNED_MATCH_BATCH = json.dumps({
    "matches": {
        "AC-3": [],              # uncovered
        "AC-4": ["test_unknown_email_returns_generic_200"],
    }
})


def test_full_run_writes_three_artifacts(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/reset_password_story.txt",
                 "r", encoding="utf-8").read()
    tests_dir = "D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/reset_password_tests"
    prefix = f"__stories__\n{story}\n__tests_dir__={tests_dir}"

    # Two sequential LLM calls are possible: AC extract (fallback), match batch.
    # The deterministic extractor should succeed on this story, so only the
    # match-batch call should run — but mock both to be safe.
    with patch("agents.traceability_matrix.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.side_effect = [_CANNED_AC_EXTRACT, _CANNED_MATCH_BATCH,
                                  _CANNED_MATCH_BATCH, _CANNED_MATCH_BATCH]
        mock_cls.return_value = mock_agent
        result = run_traceability_matrix(
            conn=test_db, job_id="j1",
            file_path="story.txt", content=story,
            file_hash="h1", language=None,
            custom_prompt=prefix,
        )

    out_dir = os.path.dirname(result["output_path"])
    assert os.path.isfile(os.path.join(out_dir, "matrix.csv"))
    assert os.path.isfile(os.path.join(out_dir, "matrix.md"))
    assert os.path.isfile(os.path.join(out_dir, "gaps.md"))

    # 4 ACs, 1 orphan (test_admin_audit_log_flush)
    import csv as _csv
    rows = list(_csv.DictReader(open(os.path.join(out_dir, "matrix.csv"),
                                     "r", encoding="utf-8")))
    assert len(rows) == 4
    assert any(r["Status"] == "red" for r in rows)

    gaps = open(os.path.join(out_dir, "gaps.md"), "r", encoding="utf-8").read()
    assert "test_admin_audit_log_flush" in gaps


def test_auto_scans_same_run_reports(test_db, tmp_path, monkeypatch):
    """When Reports/<ts>/api_tests/ exists in the cwd, F10 auto-includes it."""
    monkeypatch.chdir(tmp_path)
    ts_dir = tmp_path / "Reports" / "20260422_120000" / "api_tests"
    ts_dir.mkdir(parents=True)
    # Drop a Postman collection into the same-run api_tests folder
    (ts_dir / "api_collection.json").write_text(
        '{"info":{"name":"x","schema":"https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},'
        '"item":[{"name":"POST /reset-password"}]}',
        encoding="utf-8",
    )
    # Force the agent to resolve this Reports folder by writing the ts into env
    monkeypatch.setenv("WAVE6A_REPORT_TS", "20260422_120000")

    story = open("D:/Downloads/Projects/ai_arena/1128/tests/fixtures/wave6a/reset_password_story.txt",
                 "r", encoding="utf-8").read()
    prefix = f"__stories__\n{story}"

    with patch("agents.traceability_matrix.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.side_effect = [_CANNED_MATCH_BATCH] * 5
        mock_cls.return_value = mock_agent
        result = run_traceability_matrix(
            conn=test_db, job_id="j2",
            file_path="story.txt", content=story,
            file_hash="h2", language=None,
            custom_prompt=prefix,
        )
    md = open(os.path.join(os.path.dirname(result["output_path"]), "matrix.md"),
              "r", encoding="utf-8").read()
    # Postman item name should appear as a test somewhere in the matrix OR gaps
    assert "POST /reset-password" in md or "POST /reset-password" in \
        open(os.path.join(os.path.dirname(result["output_path"]), "gaps.md"),
             "r", encoding="utf-8").read()


def test_empty_tests_folder_yields_all_red(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    story = "AC-1: do thing A.\nAC-2: do thing B.\n"
    prefix = f"__stories__\n{story}\n__tests_dir__={empty}"
    with patch("agents.traceability_matrix.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_AC_EXTRACT  # unused — deterministic extracts
        mock_cls.return_value = mock_agent
        result = run_traceability_matrix(
            conn=test_db, job_id="j3",
            file_path="story.txt", content=story,
            file_hash="h3", language=None, custom_prompt=prefix,
        )
    import csv as _csv
    rows = list(_csv.DictReader(open(os.path.join(os.path.dirname(result["output_path"]),
                                                   "matrix.csv"), "r", encoding="utf-8")))
    assert all(r["Status"] == "red" for r in rows)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/agents/test_traceability_matrix.py -v`
Expected: integration tests FAIL (placeholder doesn't write artifacts).

- [ ] **Step 3: Implement the full `run_traceability_matrix`**

In `agents/traceability_matrix.py`, replace the placeholder `run_traceability_matrix` with:

```python
def _auto_scan_same_run(reports_root: str = "Reports") -> list[dict]:
    """Pick up F5/F6 outputs from the most recent Reports/<ts>/ in cwd.

    Honours the WAVE6A_REPORT_TS environment variable when set (test hook).
    """
    ts = os.environ.get("WAVE6A_REPORT_TS")
    if ts:
        base = os.path.join(reports_root, ts)
        if not os.path.isdir(base):
            return []
    else:
        if not os.path.isdir(reports_root):
            return []
        # Pick the newest subfolder
        subs = sorted([d for d in os.listdir(reports_root)
                       if os.path.isdir(os.path.join(reports_root, d))])
        if not subs:
            return []
        base = os.path.join(reports_root, subs[-1])

    collected: list[dict] = []
    for sub in ("api_tests", "perf_tests"):
        path = os.path.join(base, sub)
        if os.path.isdir(path):
            collected.extend(scan_tests(path))
    return collected


def _run_coverage_subagent(conn, job_id: str, src_dir: str,
                           custom_prompt: str | None) -> dict[str, float] | None:
    """Call run_test_coverage on the src folder. Returns {test_name: pct} or None on failure."""
    try:
        from agents.test_coverage import run_test_coverage
    except Exception:
        return None
    try:
        # The existing agent expects file_path + content. Pass a directory marker;
        # if it cannot process directories, we fall back to None.
        if not os.path.isdir(src_dir):
            return None
        # Concatenate the directory's .py files into one blob (best-effort).
        blob_parts: list[str] = []
        for dirpath, _d, files in os.walk(src_dir):
            for n in files:
                if n.endswith(".py"):
                    p = os.path.join(dirpath, n)
                    try:
                        with open(p, "r", encoding="utf-8") as fh:
                            blob_parts.append(f"# === {p} ===\n{fh.read()}")
                    except OSError:
                        continue
        if not blob_parts:
            return None
        blob = "\n\n".join(blob_parts)
        res = run_test_coverage(
            conn=conn, job_id=job_id,
            file_path=src_dir, content=blob, file_hash="",
            language="python", custom_prompt=custom_prompt,
        )
        # The existing agent returns coverage% per function. We aggregate
        # into a per-test average by bucketing by test_name when the agent
        # exposes it. If it does not, treat the overall score as the ceiling.
        overall = res.get("coverage_percentage") or res.get("coverage_pct") or 0.0
        per_test = res.get("per_test_coverage") or {}
        if per_test:
            return {k: float(v) for k, v in per_test.items()}
        return {"__overall__": float(overall)}
    except Exception:
        return None


def run_traceability_matrix(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    # 1. Resolve inputs
    inputs = _resolve_inputs(file_path, content, custom_prompt)
    if not inputs["stories"]:
        return {"markdown": "## Traceability Matrix — error\n\nNo stories resolvable.",
                "summary": "F10 error: no stories",
                "output_path": None}

    # 2. Extract ACs (deterministic first, LLM fallback)
    acs = _extract_acs_deterministic(inputs["stories"])
    if not acs:
        acs = _extract_acs_llm(inputs["stories"], custom_prompt)
    if not acs:
        return {"markdown": "## Traceability Matrix — error\n\nCould not extract any acceptance criteria.",
                "summary": "F10 error: zero ACs",
                "output_path": None}

    # 3. Scan tests (explicit folder + same-run auto)
    tests: list[dict] = []
    if inputs["tests_dir"]:
        tests.extend(scan_tests(inputs["tests_dir"]))
    tests.extend(_auto_scan_same_run())

    # De-dupe by (file, test_name)
    seen = set()
    unique_tests: list[dict] = []
    for t in tests:
        key = (t["file"], t["test_name"])
        if key in seen:
            continue
        seen.add(key)
        unique_tests.append(t)
    tests = unique_tests

    # 4. Jaccard match
    locks, ambiguous = _jaccard_match(acs, tests)
    # Stash AC text inside ambiguous payload for the LLM prompt builder.
    for ac in acs:
        if ac["id"] in ambiguous:
            for i, (t, s) in enumerate(ambiguous[ac["id"]]):
                t_copy = dict(t)
                t_copy["__ac_text__"] = ac["text"]
                ambiguous[ac["id"]][i] = (t_copy, s)

    # 5. LLM batch match for ambiguous
    llm_matches = _llm_match_ambiguous(ambiguous, custom_prompt)

    # 6. Assemble mapping
    mapping: dict[str, list[dict]] = {}
    for ac in acs:
        if ac["id"] in locks:
            mapping[ac["id"]] = locks[ac["id"]]
            continue
        # LLM returned for this AC
        test_names = llm_matches.get(ac["id"], [])
        matched = [t for t in tests if t["test_name"] in test_names]
        mapping[ac["id"]] = matched

    # 7. Orphans
    matched_keys = {(t["file"], t["test_name"])
                    for ts in mapping.values() for t in ts}
    orphans = [t for t in tests
               if (t["file"], t["test_name"]) not in matched_keys]

    # 8. Coverage (optional)
    coverage: dict[str, float] | None = None
    if inputs["src_dir"]:
        cov = _run_coverage_subagent(conn, job_id, inputs["src_dir"], custom_prompt)
        if cov:
            if "__overall__" in cov:
                # Broadcast the overall pct to every matched test
                overall = cov["__overall__"]
                coverage = {t["test_name"]: overall
                            for ts in mapping.values() for t in ts}
            else:
                coverage = cov

    # 9. Write artifacts
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts_str, "traceability")
    artifacts = _write_artifacts(out_dir, acs, mapping, orphans, coverage)

    # 10. Markdown summary
    rows = artifacts["rows"]
    status_counts = {"green": 0, "amber": 0, "red": 0}
    for r in rows:
        status_counts[r["Status"]] = status_counts.get(r["Status"], 0) + 1
    md_parts = [
        "## Traceability Matrix",
        f"- **ACs:** {len(acs)}",
        f"- **Tests scanned:** {len(tests)}",
        f"- **Orphan tests:** {len(orphans)}",
        f"- **Status breakdown:** "
        f"{status_counts['green']} green, "
        f"{status_counts['amber']} amber, "
        f"{status_counts['red']} red",
        f"- **CSV:** `{artifacts['csv']}`",
        f"- **Markdown matrix:** `{artifacts['md']}`",
        f"- **Gaps report:** `{artifacts['gaps']}`\n",
        "### Preview",
        open(artifacts["md"], "r", encoding="utf-8").read(),
    ]
    markdown = "\n".join(md_parts)
    summary = (f"{len(acs)} ACs, {status_counts['red']} red, "
               f"{status_counts['amber']} amber, "
               f"{len(orphans)} orphan tests.")

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": artifacts["csv"],
        "rows": rows,
        "orphans": orphans,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
```

- [ ] **Step 4: Run all F10 tests**

Run: `pytest tests/agents/test_traceability_matrix.py tests/tools/test_test_scanner.py -v`
Expected: all PASS.

- [ ] **Step 5: Full suite**

Run: `pytest -x`
Expected: all PASS.

- [ ] **Step 6: Hold for Commit 4.**

---

### Task 23: Commit 4 — F10 fill

- [ ] **Step 1: Verify diff**

Run: `git status`. Expected:
- New: `tools/test_scanner.py`, `tests/tools/test_test_scanner.py`
- New: `tests/fixtures/wave6a/reset_password_story.txt`
- New: `tests/fixtures/wave6a/reset_password_tests/test_reset.py`
- New: `tests/fixtures/wave6a/reset_password_tests/test_unmapped.py`
- New: `tests/fixtures/wave6a/reset_password_src/reset_password.py`
- Modified: `agents/traceability_matrix.py`, `tests/agents/test_traceability_matrix.py`

- [ ] **Step 2: Commit**

```bash
git add agents/traceability_matrix.py tools/test_scanner.py \
        tests/agents/test_traceability_matrix.py tests/tools/test_test_scanner.py \
        tests/fixtures/wave6a/reset_password_story.txt \
        tests/fixtures/wave6a/reset_password_tests/ \
        tests/fixtures/wave6a/reset_password_src/
git -c user.name="B.VigneshKumar" -c user.email="ic19939@gmail.com" commit -m "feat(phase6): implement F10 traceability_matrix

Extracts acceptance criteria deterministically (numbered/bullet) with
LLM fallback, scans tests via tools/test_scanner for pytest/JUnit/xUnit/
Jest/Gherkin/Robot/JMeter/Postman, and auto-includes F5/F6 outputs
from the same Reports/<ts>/ run. Hybrid matcher locks confident
Jaccard pairs and batches ambiguous ACs into a single LLM call.
Optional run_test_coverage subagent annotates matrix with coverage%.
Emits matrix.csv + matrix.md + gaps.md."
```

---

# PART E — POLISH (Commit 5)

---

### Task 24: Preset seed script

**Files:**
- Create: `scripts/seed_wave6a_preset.py`

- [ ] **Step 1: Create the script**

Create `scripts/seed_wave6a_preset.py` (no license header — scripts/ has none by convention; mirror existing helper scripts):

```python
"""One-off seed script — inserts the 'Wave 6A: API + Perf + Traceability' preset.

Run: python scripts/seed_wave6a_preset.py
"""

from __future__ import annotations

import sys

from db.connection import get_connection
from db.queries.presets import create_preset, list_presets


_PRESET_NAME = "Wave 6A: API + Perf + Traceability"
_PRESET_FEATURES = ["api_test_generator", "perf_test_generator", "traceability_matrix"]
_PRESET_PROMPT = (
    "Generate API tests, performance plan, and traceability matrix in a single run.\n"
    "Spec resolution honours __openapi_spec__; story resolution honours __mode__requirements.\n"
    "F10 auto-scans F5/F6 outputs from the same Reports/<ts>/ folder."
)


def main() -> int:
    conn = get_connection()
    existing = list_presets(conn)
    if any(p.get("name") == _PRESET_NAME for p in existing):
        print(f"Preset '{_PRESET_NAME}' already exists — skipping.")
        return 0
    # Insert one row per feature (presets are per-feature in the existing schema).
    for feat in _PRESET_FEATURES:
        create_preset(conn, name=_PRESET_NAME, feature=feat,
                      system_prompt=_PRESET_PROMPT,
                      extra_instructions="")
    print(f"Seeded '{_PRESET_NAME}' across {len(_PRESET_FEATURES)} features.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it (end-to-end verification)**

Run: `python scripts/seed_wave6a_preset.py`
Expected output: `Seeded 'Wave 6A: API + Perf + Traceability' across 3 features.`

Re-run to confirm idempotency:
Run: `python scripts/seed_wave6a_preset.py`
Expected output: `Preset 'Wave 6A: API + Perf + Traceability' already exists — skipping.`

- [ ] **Step 3: Manual UI smoke**

Launch Streamlit (`startup.bat`). Tick one of the three new features. Open the "Advanced / Fine-tune" expander → "Load preset" dropdown. Confirm "Wave 6A: API + Perf + Traceability" appears.

- [ ] **Step 4: Hold for Commit 5.**

---

### Task 25: Phase6a HOWTO doc

**Files:**
- Create: `Phase6a_HOWTO_Test.txt`

- [ ] **Step 1: Create the doc**

Create `Phase6a_HOWTO_Test.txt` at the project root. Mirror the structure of `Phase5_HOWTO_Test.txt`. Minimum contents:

```
================================================================================
AI Code Maniac — Phase 6 Wave 6A Feature Test Guide
================================================================================
Project : 1128
Phase   : 6 — Wave 6A
Scope   : F5, F6, F10
Updated : 22nd April 2026
Author  : B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
================================================================================

TABLE OF CONTENTS
--------------------------------------------------------------------------------
 0.  Prerequisites & environment
 1.  F5  — API Test Generator (OpenAPI/Swagger)
 2.  F6  — Performance / Load Test Generator
 3.  F10 — Traceability Matrix + Coverage Gap Finder
 4.  Wave 6A preset — one-click run
 5.  Troubleshooting

================================================================================
 0. PREREQUISITES & ENVIRONMENT
================================================================================
a. Activate the project virtualenv:
      D:\Downloads\Projects\ai_arena\1128\venv\Scripts\activate.bat
b. Install baseline deps (already in requirements.txt):
      pip install -r requirements.txt
c. ENABLED_AGENTS — if .env restricts agents, either set:
      ENABLED_AGENTS=all
   or include the three new keys:
      ENABLED_AGENTS=...,api_test_generator,perf_test_generator,traceability_matrix
d. Optional — seed the one-click preset:
      python scripts\seed_wave6a_preset.py
e. All outputs land under Reports\<YYYYMMDD_HHMMSS>\...

================================================================================
 1. F5 — API TEST GENERATOR
================================================================================
WHAT IT DOES
  Generates runnable API tests from an OpenAPI 3.x / Swagger 2.x spec. Picks
  the code framework from the sidebar language:
      python              → pytest + requests   (test_api.py)
      java / kotlin       → REST Assured        (ApiTests.java)
      csharp / .net / c#  → xUnit + HttpClient  (ApiTests.cs)
      typescript / js     → supertest + Jest    (api.test.ts)
      (blank/other)       → Postman only (no code file)
  ALWAYS emits a Postman 2.1 collection (api_collection.json) deterministically
  — no LLM tokens spent on the collection.

AGENT KEY
  api_test_generator

UI TEST STEPS
  1. Streamlit → Code Analysis. Source type = Local.
  2. Upload tests\fixtures\wave6a\petstore_openapi.yaml as the source.
  3. Sidebar → Language → type "python".
  4. Features → Testing & Maintenance → tick "API Test Generator (OpenAPI)".
  5. Run.

EXPECTED OUTPUTS
  Reports\<ts>\api_tests\test_api.py            (pytest file)
  Reports\<ts>\api_tests\api_collection.json    (Postman v2.1)

CLI SMOKE
  python -c "from db.connection import get_connection; \
             from db.queries.jobs import create_job; \
             from agents.orchestrator import run_analysis; \
             conn=get_connection(); \
             jid=create_job(conn,'local', \
                 r'tests\fixtures\wave6a\petstore_openapi.yaml','python', \
                 ['api_test_generator']); \
             run_analysis(conn,jid); print(jid)"

MANUAL VERIFICATION
  pytest Reports\<ts>\api_tests\test_api.py -v
  newman run Reports\<ts>\api_tests\api_collection.json

PASS CRITERIA
  [ ] Both artifacts exist.
  [ ] All 3 petstore endpoints appear in both.
  [ ] Code file has at least one 4xx negative per endpoint.
  [ ] Postman JSON has valid v2.1 schema URL.

================================================================================
 2. F6 — PERFORMANCE / LOAD TEST GENERATOR
================================================================================
WHAT IT DOES
  Generates a JMeter .jmx plan or a Gatling Simulation.scala from an OpenAPI
  spec OR a user story. Auto-picks by sidebar language:
      java / scala / gatling  → Gatling (Simulation.scala)
      (anything else)         → JMeter (plan.jmx)
  Deterministic tools/load_profile_builder.py supplies fixed VU/ramp/
  steady-state numbers so the LLM only composes syntax, never guesses load.

AGENT KEY
  perf_test_generator

UI TEST STEPS — spec mode
  1. Source: tests\fixtures\wave6a\petstore_openapi.yaml
  2. Language: blank (→ JMeter) or "scala" (→ Gatling).
  3. Tick "Perf/Load Test Generator". Run.

UI TEST STEPS — story mode
  1. Source: tests\fixtures\wave6a\order_story.txt
  2. Advanced / Fine-tune → System Prompt (Overwrite):
        __mode__requirements
        <paste the same story>
  3. Tick "Perf/Load Test Generator". Run.

EXPECTED
  Reports\<ts>\perf_tests\plan.jmx         (JMeter)   -- OR --
  Reports\<ts>\perf_tests\Simulation.scala (Gatling)

MANUAL VERIFICATION
  xmllint --noout Reports\<ts>\perf_tests\plan.jmx
  # or: jmeter -n -t Reports\<ts>\perf_tests\plan.jmx -l results.jtl

PASS CRITERIA
  [ ] Exactly one artifact.
  [ ] JMeter: one ThreadGroup, ≥ 3 HTTPSamplerProxy for petstore.
  [ ] Gatling: `class LoadTest extends Simulation`, one exec() per endpoint.
  [ ] /health, /metrics, /livez, /readyz NOT present in steady-state load.

================================================================================
 3. F10 — TRACEABILITY MATRIX + COVERAGE GAP FINDER
================================================================================
WHAT IT DOES
  Cross-references acceptance criteria (stories) ↔ tests (any framework) ↔
  optional code coverage. Emits matrix.csv, matrix.md, gaps.md. Auto-includes
  anything under the same Reports\<ts>\api_tests\ and perf_tests\ from a
  multi-agent run.

AGENT KEY
  traceability_matrix

UI TEST STEPS
  1. Tick "Traceability Matrix + Gaps" in the sidebar.
  2. In the "Traceability Matrix — inputs" expander that appears:
       Stories:    paste the reset_password_story.txt content (or URL).
       Tests dir:  tests\fixtures\wave6a\reset_password_tests
       Code dir:   tests\fixtures\wave6a\reset_password_src   (optional)
  3. Source type = Local. Upload any .txt placeholder (even a 1-line file).
  4. Run.

EXPECTED
  Reports\<ts>\traceability\matrix.csv
  Reports\<ts>\traceability\matrix.md
  Reports\<ts>\traceability\gaps.md

PASS CRITERIA
  [ ] matrix.csv has 4 AC rows.
  [ ] Status column is one of green/amber/red/orphan per row.
  [ ] test_admin_audit_log_flush appears in gaps.md as an orphan.
  [ ] When a same-run Reports\<ts>\api_tests\api_collection.json exists,
      its requests are included as rows automatically.

================================================================================
 4. WAVE 6A PRESET — ONE-CLICK RUN
================================================================================
After running scripts\seed_wave6a_preset.py:

  1. Tick F5, F6, and F10 in the sidebar.
  2. Advanced / Fine-tune → Load preset → pick "Wave 6A: API + Perf + Traceability".
  3. Run.
  → All three agents fire in the same Reports\<ts>\ folder. F10 picks up
    F5's Postman collection and the F6 plan automatically.

================================================================================
 5. TROUBLESHOOTING
================================================================================
SYMPTOM                              LIKELY CAUSE / FIX
----------------------------------   -------------------------------------------
Feature not visible in sidebar       ENABLED_AGENTS restricts. Set to 'all' or
                                     add the three keys explicitly.
F5 emits Postman only                Sidebar Language is blank/unmapped. Set
                                     "python", "java", "csharp", or "typescript".
F6 artifact has wrong framework      Sidebar Language mismatches expectation —
                                     java/scala/gatling → Gatling, else JMeter.
F10 matrix is all-red with 0 tests   __tests_dir__ path is wrong or points at
                                     an empty folder. Check the path in the
                                     F10 helper expander.
OpenAPI parse error                  pip install pyyaml.
"Spec fetch failed" (Jira/ADO/Qase)  Provider creds missing. Use inline text.

END OF FILE
================================================================================
```

- [ ] **Step 2: Hold for Commit 5.**

---

### Task 26: Commit 5 — polish and close

- [ ] **Step 1: Verify diff**

Run: `git status`. Expected files only:
- New: `scripts/seed_wave6a_preset.py`, `Phase6a_HOWTO_Test.txt`

- [ ] **Step 2: Final full-suite run**

Run: `pytest -x`
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_wave6a_preset.py Phase6a_HOWTO_Test.txt
git -c user.name="B.VigneshKumar" -c user.email="ic19939@gmail.com" commit -m "docs(phase6): Wave 6A preset seed + HOWTO

Adds idempotent scripts/seed_wave6a_preset.py to insert the one-click
'Wave 6A: API + Perf + Traceability' preset, and Phase6a_HOWTO_Test.txt
mirroring the Phase 5 HOWTO layout for F5, F6, F10."
```

- [ ] **Step 4: Summarise delivery**

Print a final summary in your response with:
- Commits delivered (`git log --oneline -n 5`)
- New files count (`git diff --stat HEAD~5 HEAD | tail -1`)
- Test count (`pytest --collect-only -q | tail -1`)

Confirm every task checkbox in this plan is ticked before closing.

---

## Plan self-review

**Spec coverage:**
- §2 Architecture — Tasks 1-5 (scaffold, wiring), consistent file layout.
- §3 Subagent definition — loose subagents realised in Tasks 8 (Postman), 13 (load profile), 18 (test scanner), plus LLM subagent calls in Tasks 11, 16, 22. test_coverage subagent called in Task 22's `_run_coverage_subagent`.
- §4 F5 — Tasks 7-12. Framework auto-pick table (Task 10) matches spec §4.2. Postman "always on" behaviour (Task 8 + Task 11's blank-language test).
- §5 F6 — Tasks 13-17. JMeter/Gatling auto-pick by language (Task 15), mode detection (Task 15), load profile injection (Task 13), metadata endpoint filter (in `_filter_metadata`).
- §6 F10 — Tasks 18-23. AC extraction deterministic + LLM fallback (Task 20), test_scanner 7 kinds (Task 18), ambiguous definition matching spec §6.2 step 4 (`_is_ambiguous` in Task 20), auto-scan same-run outputs (Task 22 `_auto_scan_same_run`), coverage subagent (Task 22 `_run_coverage_subagent`), three artifacts (Task 21 `_write_artifacts`).
- §7 Wiring — Task 4 (orchestrator) + Task 5 (feature_selector + F10 expander).
- §8 Delivery sequence — 5 commits as per spec. Task 6, 12, 17, 23, 26.
- §9 Testing — fixtures distributed across Tasks 7, 14, 18, 19; smoke/unit tests in every TDD task.
- §10 Risks — LLM shape validation in Task 16 step 3 (`ok` check), Postman determinism in Task 8, degrade-gracefully coverage in Task 22, cache in Task 11 test.
- §11 Out of scope — respected; no LoadRunner migrator, no defect axis, no multi-framework F5 fan-out.

**Placeholder scan:** searched for TBD / TODO / "implement later" / "similar to Task" / "add appropriate" — none found. All code blocks complete.

**Type consistency:**
- `_resolve_spec` returns `_SpecResolution` consistently (Task 9 definition, Task 11 usage).
- `build_collection(spec, base_url=None) -> dict` (Task 8 definition, Task 11 usage).
- `build_profile(num_endpoints, target="medium") -> dict` (Task 13, Task 16 call).
- `scan_tests(root) -> list[dict]` (Task 18, Task 22 call).
- `_build_matrix_rows(acs, mapping, coverage) -> list[dict]` (Task 21, Task 22 call).
- `_write_artifacts(out_dir, acs, mapping, orphans, coverage) -> dict` (Task 21, Task 22 call).
- `_resolve_inputs(file_path, content, custom_prompt) -> dict` with keys `stories`, `tests_dir`, `src_dir` (Task 21, Task 22 call).

All signatures and keys are consistent.
