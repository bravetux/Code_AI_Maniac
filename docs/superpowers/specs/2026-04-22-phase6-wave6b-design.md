# Phase 6 — Wave 6B Design

**Scope:** F9 (Self-Healing Test Agent), F11 (SonarQube Fix Automation), F14 (NL → SQL / Stored-Procedure Generator), F15 (Auto-Fix / Patch Generator). F13 (Code-from-Prompt Generator) is deferred to a dedicated future wave.

**Dated:** 2026-04-22
**Author:** B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
**Companion Wave 6A spec:** `docs/superpowers/specs/2026-04-22-phase6-wave6a-design.md`

---

## 0. Constraints

Carried from user brief — non-negotiable:

1. Each feature is a **separate agent** (new module in `agents/`).
2. Each agent **may have subagents** — loose definition (LLM call, deterministic pipeline-tool helper, or call to another existing agent's `run_*`).
3. **Do not modify existing tools.** If an existing tool is insufficient, extend via a **new pipeline tool** alongside.
4. The only pre-existing files edited are `agents/orchestrator.py`, `app/components/feature_selector.py`, `config/settings.py::ALL_AGENTS`, and the three Wave 6A agents (for the one-line `JOB_REPORT_TS` rename — backward-compat preserved).
5. The user maintains a separate code-browser (symbol navigation + architecture viewer). Wave 6B delivers **code-generation / patching** features that are orthogonal to that work — no overlap.

---

## 1. Phase 6 decomposition (where 6B sits)

Phase 6 per `1128_FEATURES.md` contains 11 features. Delivered in three waves:

| Wave | Features | Status |
|---|---|---|
| **6A** | F5, F6, F10 | ✅ Shipped (PR #1) |
| **6B (this spec)** | F9, F11, F14, F15 | Design approved |
| **6B-deferred** | F13 (Code-from-Prompt, 6 frameworks) | Deferred — its own future spec |
| **6C** | F22, F23, F4 | Future wave |

---

## 2. Architecture overview

Wave 6B adds **4 agents** + **3 new pipeline tools**. Existing files edited: 4 (`orchestrator.py`, `feature_selector.py`, `settings.py`, plus a minor rename in the 3 Wave 6A agent files). All other changes are additive.

```
agents/                              tools/
├── self_healing_agent.py   (F9)     ├── patch_emitter.py         (shared — all 4 agents)
├── sonar_fix_agent.py      (F11)    ├── sonar_fetcher.py         (F11 subagent)
├── sql_generator.py        (F14)    └── ddl_parser.py            (F14 subagent)
└── auto_fix_agent.py       (F15)
```

### Agent pattern (unchanged from 6A)

Every new agent mirrors `agents/unit_test_generator.py`:

```python
def run_<name>(conn, job_id, file_path, content, file_hash,
               language, custom_prompt, **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached: return cached
    # 1. Resolve intake (prefix → sibling → auto-scan Reports/<ts>/)
    # 2. Call pipeline-tool subagents as needed
    # 3. Call strands.Agent LLM subagent(s)
    # 4. Emit via shared tools.patch_emitter
    # 5. write_cache + add_history
    return {"markdown": ..., "summary": ..., "output_path": ..., ...}
```

### Intake convention (prefix-based, extends 6A)

Wave 6A prefixes remain untouched. Wave 6B adds:

| Prefix | Meaning | Consumed by |
|---|---|---|
| `__findings__\n<md or JSON>` | Bug/refactoring findings (inline override) | F15 |
| `__sonar_issues__\n<JSON>` | Sonar issues (inline override) | F11 |
| `__sonar_top_n__=<int>` | Issue count cap fed to LLM (default 50) | F11 |
| `__db_schema__\n<DDL or YAML>` | Schema body (inline override) | F14 |
| `__prompt__\n<description>` | NL description of SQL to generate | F14 |
| `__page_html__\n<html>` | Current page DOM for selector healing | F9 |
| `__page_url__=<url>` | URL to fetch DOM *(deferred — reserved prefix)* | F9 |

Sibling-file fallbacks: F14 → `schema.sql` / `schema.ddl`; F11 → `sonar_issues.json`; F9 → `dom.html`.

F9's `__page_url__` prefix is reserved but not implemented this wave (requires a headless browser — Phase 7 scope). F9 requires inline or sibling HTML at launch.

### Reports layout

```
Reports/<JOB_REPORT_TS>/
├── api_tests/            (F5 — from 6A)
├── perf_tests/           (F6 — from 6A)
├── traceability/         (F10 — from 6A)
├── self_healing/         (F9 — new)
├── sonar_fix/            (F11 — new)
├── sql_generator/        (F14 — new)
└── auto_fix/             (F15 — new)
```

Every 6B agent folder contains the uniform shape emitted by `tools.patch_emitter`:

```
<feature>/
├── patches/
│   ├── <filename>              (new content OR fully-patched file)
│   └── <filename>.diff         (unified diff)
├── pr_comment.md               (PR-ready Markdown summary)
└── summary.json                (structured result)
```

### Shared timestamp — `JOB_REPORT_TS`

Orchestrator sets `JOB_REPORT_TS` once per `run_analysis(conn, job_id)` call. Every 6A + 6B agent's `_report_ts()` helper prefers `JOB_REPORT_TS`, falls back to `WAVE6A_REPORT_TS` (back-compat alias — maintained for one release), then `datetime.now()`. All features in a multi-agent job land in the same `Reports/<ts>/` folder.

### LLM, caching, no DB schema change

`agents/_bedrock.make_bedrock_model()` unchanged. `tools/cache.py` reused. Zero schema changes to `data/arena.db`. Same Claude model as Wave 6A.

---

## 3. Subagent definition (unchanged from 6A)

Loose: a subagent is any callable invoked from a parent agent's `run_*` — LLM call, deterministic pipeline-tool, or another agent's `run_*`. Per-feature inventory:

| Agent | LLM subagents | Pipeline-tool subagents | Existing-agent subagents |
|---|---|---|---|
| F9 `self_healing_agent` | 1 (selector rewrite) | `tools.patch_emitter` | — |
| F11 `sonar_fix_agent` | 1 per source file (bounded by `top_n`) | `tools.sonar_fetcher`, `tools.patch_emitter` | — |
| F14 `sql_generator` | 1 (SQL gen) | `tools.ddl_parser`, `tools.patch_emitter` | — |
| F15 `auto_fix_agent` | 1 (diff gen) | `tools.patch_emitter` | — (auto-scans Reports/ for Bug Analysis + Refactoring Advisor output) |

---

## 4. F9 — `self_healing_agent`

### 4.1 Purpose

Rewrite UI test scripts (Selenium / Playwright / Cypress) when selectors break due to DOM changes. Framework detected from test content. User supplies current DOM as inline HTML or sibling file.

### 4.2 Inputs

- **Source** — the old test file (`.py` / `.ts` / `.js` / `.cy.js`).
- **DOM snapshot** — `__page_html__\n<html>` prefix, OR sibling `dom.html` file.
- `language` optional — used to disambiguate if framework detection is unsure.

Framework detection (regex on first 4 KB of source):
- `from selenium` / `webdriver.By` → Selenium
- `from playwright` / `page.locator(` → Playwright
- `cy.get(` / file ends `.cy.js` / `.cy.ts` → Cypress
- None matched → falls back to generic "update whatever selector syntax is here" prompt

### 4.3 Pipeline

1. Resolve old test (`content`) + DOM (`__page_html__` or sibling).
2. Detect framework.
3. Extract current selectors from test (regex per framework: `By.id("x")`, `By.xpath("...")`, `page.locator("x")`, `cy.get("x")`).
4. LLM subagent (single call): system prompt names the detected framework, user prompt pastes `<OLD TEST>`, `<CURRENT DOM>`, `<OLD SELECTORS>`, asks for a unified diff rewriting the selectors to match the DOM.
5. Validate the diff is non-empty and addresses only selector lines (no wholesale rewrites).
6. `patch_emitter.emit(agent_key="self_healing", file_path=<source>, diff=llm_output, description=...)`.

### 4.4 Outputs

```
Reports/<ts>/self_healing/
├── patches/<test_filename>         (patched test)
├── patches/<test_filename>.diff    (unified diff)
├── pr_comment.md                   (framework, selector diff highlights)
└── summary.json                    {framework, old_selectors[], new_selectors[], confidence}
```

### 4.5 Fixture

`tests/fixtures/wave6b/login_selectors/`:
- `old_test.py` — Selenium test using `By.id("login-btn")`, `By.xpath("//input[@name='email']")`
- `dom.html` — current page with `data-testid="login"`, `id="email-field"` (old IDs removed)
- `canned_llm.txt` — canned unified diff for CI tests

### 4.6 Pass criteria

- [ ] Patched test file in `patches/`
- [ ] `.diff` is a valid unified diff (applies cleanly via `patch` / `git apply --check`)
- [ ] `pr_comment.md` shows the selector mapping (old → new)
- [ ] Framework detected correctly for Selenium / Playwright / Cypress fixtures

### 4.7 Failure modes

- No DOM resolvable → error markdown, no artifact
- Unknown framework → generic fallback prompt, confidence marked "low" in summary
- LLM returns empty/non-diff → error markdown with raw output attached

---

## 5. F11 — `sonar_fix_agent`

### 5.1 Purpose

Ingest SonarQube issues for a project and emit PR-ready patches that address as many as the LLM can confidently resolve. Three-channel intake (API / file / prefix). Issues are sorted by severity and capped at `top_n` (default 50) before the LLM sees them.

### 5.2 Inputs

Resolution order:
1. `__sonar_issues__\n<JSON body>` prefix
2. Source file is `.json` and sniffs as Sonar format (has `issues` array with `rule`, `severity`, `component`)
3. API fetch via `tools.sonar_fetcher.fetch_issues(...)` — requires `SONAR_URL`, `SONAR_TOKEN`, `SONAR_PROJECT_KEY` env vars
4. Else: error markdown

`__sonar_top_n__=<int>` caps issue count (default 50).

### 5.3 `tools/sonar_fetcher.py` signature

```python
def fetch_issues(sonar_url: str, project_key: str, token: str,
                 statuses: tuple[str, ...] = ("OPEN", "CONFIRMED"),
                 page_size: int = 100,
                 max_total: int = 500) -> list[dict]:
    """GET /api/issues/search?projectKeys=<key>&statuses=<csv>&ps=<n> with
    'Authorization: Bearer <token>'. Paginates up to max_total. Returns
    normalised records: {rule, severity, component, line, message, effort,
    textRange}. Respects Retry-After on 429.
    
    Raises SonarFetchError on auth failure, network error, or invalid response.
    """
```

Dependency-light: uses stdlib `urllib.request` + `json` — no new pip dependency.

### 5.4 Pipeline

1. Resolve issues (prefix → file → API)
2. Sort by severity: BLOCKER > CRITICAL > MAJOR > MINOR > INFO
3. Truncate to `top_n`
4. Group by `component` (source file path)
5. **Per source file**, one LLM call: system prompt explains Sonar + asks for a diff; user prompt includes the file's content and the issues targeting it; LLM returns a unified diff OR refusal per issue
6. `patch_emitter.emit()` per file
7. Aggregate summary across all files: `issues_total`, `issues_fixed[]`, `issues_deferred[{id, reason}]`

### 5.5 Outputs

```
Reports/<ts>/sonar_fix/
├── patches/
│   ├── <file_1>              + <file_1>.diff
│   └── <file_2>              + <file_2>.diff
├── pr_comment.md             (aggregate — all files, all issues resolved vs. deferred)
└── summary.json              {issues_total, issues_fixed[], issues_deferred[]}
```

### 5.6 Fixture

`tests/fixtures/wave6b/sonar/`:
- `issues.json` — 5 Sonar issues spanning 2 source files (1 CRITICAL bug, 2 MAJOR code smells, 2 MINOR)
- `src/app.py`, `src/utils.py` — the 2 source files with the flagged issues
- `canned_llm.txt` — canned responses per file

### 5.7 Pass criteria

- [ ] Issues sorted and truncated to `top_n`
- [ ] One diff per source file (not one global diff)
- [ ] `summary.json` lists every issue as either fixed or deferred with a reason
- [ ] API-mode: 429 response triggers a retry with `Retry-After` backoff

### 5.8 Failure modes

- No issues resolvable → error markdown
- API auth fail → fall through to file / prefix with warning in markdown (do NOT crash)
- Diff doesn't apply → mark file's issues as `deferred: diff_rejected`, continue with other files

---

## 6. F14 — `sql_generator`

### 6.1 Purpose

Generate SQL (SELECT / INSERT / UPDATE / DELETE / stored procedure) from a natural-language description, using schema information to ensure correctness and RLS awareness.

### 6.2 Inputs

- `__prompt__\n<NL description>` — **required** (the "what to generate" input)
- Schema resolution:
  1. `__db_schema__\n<DDL or YAML>` prefix
  2. Source file ending `.sql` / `.ddl` (is the schema)
  3. Sibling `schema.sql` / `schema.ddl`
- `language` drives dialect:
  - `postgres` / `pgsql` / `postgresql` → PostgreSQL-specific (jsonb, arrays, RLS via `current_setting`)
  - Anything else → ANSI-generic with a caveat note in the output

### 6.3 `tools/ddl_parser.py` signature

```python
def parse_ddl(text: str) -> dict:
    """Regex-based DDL parser — not a full SQL AST.
    
    Returns:
      {
        "tables": [{
            "name": str,
            "columns": [{"name": str, "type": str, "nullable": bool,
                         "default": str|None, "pk": bool, "fk": {ref_table, ref_col}|None}],
        }],
        "views": [{"name": str, "definition": str}],
        "policies": [{"table": str, "name": str, "command": str,
                      "using": str, "check": str}],   # PG RLS only
      }
    
    Supports: CREATE TABLE, ALTER TABLE ADD COLUMN, CREATE VIEW,
              CREATE POLICY (PG). Unsupported statements are skipped silently.
    Returns partial result on parse errors.
    """
```

Light-weight; not a full SQL parser. Enough to produce a compact schema summary for the LLM prompt.

### 6.4 Pipeline

1. Resolve prompt (required) + schema
2. Parse schema via `ddl_parser.parse_ddl(...)`
3. Build compact summary: `users(id int PK, email varchar UNIQUE, tenant_id int FK→tenants.id)` one line per table, plus RLS policies block
4. LLM subagent (single call): prompt includes dialect name + schema summary + NL request; asks for one fenced SQL block
5. Validate LLM output: non-empty, contains at least one of `SELECT`/`INSERT`/`UPDATE`/`DELETE`/`CREATE`/`CALL`
6. `patch_emitter.emit(agent_key="sql_generator", file_path="query.sql", new_content=sql, description=...)`

### 6.5 Outputs

```
Reports/<ts>/sql_generator/
├── patches/query.sql
├── patches/query.sql.diff      (empty diff — new file)
├── pr_comment.md
└── summary.json                {dialect, tables_referenced[], rls_policies_applied[]}
```

### 6.6 Fixture

`tests/fixtures/wave6b/sql/`:
- `multi_tenant_schema.sql` — 3 tables (users, tenants, orders) + 1 RLS policy on orders
- `order_report_prompt.txt` — "Total revenue per tenant in Q1 2026, ordered by revenue descending"
- `canned_llm.txt` — canned SQL with proper `WHERE tenant_id = current_setting('app.tenant_id')::int` filter

### 6.7 Pass criteria

- [ ] SQL file written to `patches/query.sql`
- [ ] SQL references only tables present in the schema (no hallucinated names)
- [ ] PG mode: RLS policies mentioned in the schema are honoured (policy's column in WHERE clause or session setting referenced)
- [ ] Non-PG mode: markdown notes "dialect: ANSI (generic) — review before use"

### 6.8 Failure modes

- No prompt → error markdown
- No schema → error markdown
- LLM emits non-SQL → error markdown with raw output

---

## 7. F15 — `auto_fix_agent`

### 7.1 Purpose

Take a code file plus issue findings (from Bug Analysis + Refactoring Advisor, or inline prefix) and emit a unified diff that addresses as many findings as possible.

### 7.2 Inputs

- **Source** — the code file to patch (required — via standard `content` parameter)
- **Findings** — resolution order:
  1. `__findings__\n<md or JSON body>` prefix
  2. Auto-scan `Reports/<JOB_REPORT_TS>/bug_analysis/` and `Reports/<JOB_REPORT_TS>/refactoring_advisor/` for files whose names match the source's basename
- If neither resolvable → error markdown

### 7.3 Pipeline

1. Resolve findings (prefix wins; else auto-scan)
2. Filter findings to those targeting the current source file
3. If empty → error markdown
4. LLM subagent: prompt includes source content + findings (structured); asks for a unified diff
5. Validate diff non-empty and applies cleanly via `difflib.restore` reverse-check
6. `patch_emitter.emit(agent_key="auto_fix", file_path=<source>, base_content=<source content>, diff=<llm diff>, description=...)`

### 7.4 Outputs

```
Reports/<ts>/auto_fix/
├── patches/<source_filename>       (patched file)
├── patches/<source_filename>.diff
├── pr_comment.md                   (per-finding: addressed vs. skipped)
└── summary.json                    {findings_addressed[], findings_skipped[{id, reason}]}
```

### 7.5 Fixture

`tests/fixtures/wave6b/auto_fix/`:
- `buggy.py` — contains `return a / b` (no zero-check) and `password = "hunter2"` (hardcoded secret)
- `bug_analysis_findings.json` — pre-canned findings pointing to both issues
- `canned_llm.txt` — canned diff addressing both issues

### 7.6 Pass criteria

- [ ] Diff applies cleanly (validated via `difflib` reverse-check before write)
- [ ] `summary.json` lists every finding as addressed or skipped
- [ ] Auto-scan path: when `Reports/<ts>/bug_analysis/buggy.md` exists in the same run, F15 picks it up without `__findings__` prefix

### 7.7 Failure modes

- No findings → error markdown
- Diff rejected by reverse-apply → writes the raw diff + rejected hunks, summary marks `applied: false`

---

## 8. Shared `tools/patch_emitter.py`

### 8.1 Signature

```python
def emit(agent_key: str, reports_root: str, file_path: str,
         new_content: str | None = None,
         diff: str | None = None,
         base_content: str | None = None,
         description: str = "",
         summary_extras: dict | None = None) -> dict:
    """Write a PR-ready patch set for a single file.
    
    Required: exactly one of
      - new_content (new file or full replacement)
      - diff (unified diff — base_content must also be supplied for reverse-apply validation)
      - base_content + new_content (emitter computes diff via difflib.unified_diff)
    
    Writes:
      <reports_root>/<agent_key>/patches/<basename(file_path)>
      <reports_root>/<agent_key>/patches/<basename(file_path)>.diff
      <reports_root>/<agent_key>/pr_comment.md   (created or appended)
      <reports_root>/<agent_key>/summary.json    (created or merged — for multi-file runs)
    
    Returns:
      {
        "markdown": <str — short human-readable summary for agent's return value>,
        "paths": {"content": ..., "diff": ..., "pr_comment": ..., "summary_json": ...},
        "applied": bool,   # True if diff was reverse-apply-validated
      }
    """
```

### 8.2 Behaviour

- Diff format: `difflib.unified_diff` with headers `--- a/<file_path>` / `+++ b/<file_path>`. 3-line context.
- `pr_comment.md` for multi-file runs: each call appends a `## <filename>` block with the description + fenced diff preview.
- `summary.json` merging: reads existing, merges new `files` array entries + updates aggregate counters, writes back.
- Diff reverse-apply validation when `diff` is supplied with `base_content`: uses `difflib.restore` on the diff's minus-side hunks against base_content; fails cleanly with `applied: false` in the return if mismatched.

### 8.3 No LLM, dependency-light

Pure Python standard library (`difflib`, `json`, `os`). Tested in isolation.

### 8.4 Fixture / test

`tests/tools/test_patch_emitter.py` covers: new-file mode, diff mode, base+new mode, multi-call merging, invalid-diff rejection.

---

## 9. Timestamp generalization

### 9.1 Change in `agents/orchestrator.py::run_analysis`

**Before:**
```python
os.environ["WAVE6A_REPORT_TS"] = datetime.now().strftime("%Y%m%d_%H%M%S")
```

**After:**
```python
_job_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
os.environ["JOB_REPORT_TS"] = _job_ts
os.environ["WAVE6A_REPORT_TS"] = _job_ts   # back-compat alias — deprecate in next wave
```

### 9.2 Change in `_report_ts()` helper (3 Wave 6A agents + all 4 Wave 6B agents)

```python
def _report_ts() -> str:
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")   # back-compat
            or datetime.now().strftime("%Y%m%d_%H%M%S"))
```

### 9.3 Change in `agents/traceability_matrix._auto_scan_same_run`

Update env-var lookup with the same fallback chain.

### 9.4 Test update

`tests/agents/test_wave6a_chain.py::test_report_ts_helper_uses_env_var_when_set`: extend to also assert `JOB_REPORT_TS` is read correctly when set alone.

### 9.5 Back-compat window

`WAVE6A_REPORT_TS` remains functional for one release beyond this wave. Deprecation comment in orchestrator notes removal target.

---

## 10. Orchestrator + feature_selector wiring

### 10.1 `agents/orchestrator.py`

Three imports (additive):
```python
# Phase 6 — Wave 6B
from agents.self_healing_agent import run_self_healing_agent
from agents.sonar_fix_agent import run_sonar_fix_agent
from agents.sql_generator import run_sql_generator
from agents.auto_fix_agent import run_auto_fix_agent
```

Four new keys in `phase1` tuple and `standalone` dispatch, immediately after the Wave 6A block.

Plus the `JOB_REPORT_TS` rename from §9.1.

### 10.2 `app/components/feature_selector.py`

`ALL_FEATURES` additions:
```python
# ── Phase 6 — Wave 6B ──────────────────────────────────────────────
"self_healing_agent":   "Self-Healing Test Agent (F9)",
"sonar_fix_agent":      "SonarQube Fix Automation (F11)",
"sql_generator":        "NL → SQL Generator (F14)",
"auto_fix_agent":       "Auto-Fix Patch Generator (F15)",
```

`FEATURE_GROUPS`: insert a NEW group **"Code Generation & Fixes"** between "Testing & Maintenance" and "Documentation & Review", containing all 4 new features.

`FEATURE_HELP`: tooltip per feature, mirroring Wave 6A's F-number prefix style.

No new inline helper expander needed — all 6B intake is prefix-only.

### 10.3 `config/settings.py::ALL_AGENTS`

Four new keys with `# Phase 6 — Wave 6B` comment block.

### 10.4 Files not touched

Not modified: `agents/_bedrock.py`, `db/queries/*`, `tools/cache.py`, `tools/openapi_parser.py`, `tools/spec_fetcher.py`, `tools/fetch_local.py`, `tools/postman_emitter.py`, `tools/load_profile_builder.py`, `tools/test_scanner.py`, the Streamlit entry pages.

---

## 11. Delivery sequence

Scaffold-first, smallest-feature-first (Q9(a)).

| # | Commit | Touches existing files? | Ships working feature? |
|---|---|---|---|
| 1 | Scaffold (4 stubs) + wiring + `JOB_REPORT_TS` rename | Yes — `orchestrator.py`, `feature_selector.py`, `settings.py`, 3 Wave 6A agents (rename), 1 test file | No — stubs |
| 2 | `tools/patch_emitter.py` + unit tests | No | No (tool only) |
| 3 | F9 fill — `self_healing_agent.py` body + fixture | No | Yes — F9 end-to-end |
| 4 | F11 fill — `sonar_fix_agent.py` + `tools/sonar_fetcher.py` + fixture | No | Yes — F11 end-to-end |
| 5 | F14 fill — `sql_generator.py` + `tools/ddl_parser.py` + fixture | No | Yes — F14 end-to-end |
| 6 | F15 fill — `auto_fix_agent.py` + fixture | No | Yes — F15 end-to-end |
| 7 | Wave 6B preset seed + `Phase6b_HOWTO_Test.txt` | No | One-click UX |

Each commit independently reviewable and revertable.

---

## 12. Testing

### 12.1 Fixtures — under `tests/fixtures/wave6b/`

```
login_selectors/
├── old_test.py                        # Selenium old selectors
├── dom.html                           # current DOM (new data-testid)
└── canned_llm.txt                     # canned LLM response

sonar/
├── issues.json                        # 5 issues across 2 files
├── src/app.py
├── src/utils.py
└── canned_llm.txt

sql/
├── multi_tenant_schema.sql            # 3 tables + 1 RLS policy
├── order_report_prompt.txt
└── canned_llm.txt

auto_fix/
├── buggy.py
├── bug_analysis_findings.json
└── canned_llm.txt
```

### 12.2 Smoke tests — under `tests/agents/test_wave6b/` and `tests/tools/`

- `tests/agents/test_self_healing_agent.py` — stub test + dispatch test + integration (framework detection, diff emission, patch_emitter output shape)
- `tests/agents/test_sonar_fix_agent.py` — prefix/file/API intake paths, top_n cap, multi-file per-source diffs
- `tests/agents/test_sql_generator.py` — DDL parse, PG vs generic dialect, RLS awareness check
- `tests/agents/test_auto_fix_agent.py` — prefix path, auto-scan path, diff validation
- `tests/agents/test_wave6b_chain.py` — regression: F15 auto-scans Bug Analysis fixture in the same `Reports/<JOB_REPORT_TS>/`
- `tests/tools/test_patch_emitter.py` — new-file, diff, base+new, multi-call merging, invalid-diff rejection
- `tests/tools/test_ddl_parser.py` — tables, views, policies, partial-parse tolerance
- `tests/tools/test_sonar_fetcher.py` — monkeypatched `urllib.request.urlopen`: auth, pagination, 429 retry, empty response

LLM calls always monkeypatched via `patch("agents.<x>.Agent")` with canned responses from `canned_llm.txt` — no Bedrock tokens in CI.

### 12.3 HOWTO doc

`Phase6b_HOWTO_Test.txt` under project root. Same structure as `Phase5_HOWTO_Test.txt` and `Phase6a_HOWTO_Test.txt`: Prerequisites / F9 / F11 / F14 / F15 / Preset / Troubleshooting. CLI smoke commands + UI test steps + pass criteria per feature.

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| LLM emits diff that doesn't apply to source (F15, F11) | `patch_emitter` validates via `difflib` reverse-check; on failure marks `applied: false` in summary, writes raw diff for manual review |
| F11 Sonar API rate limits | `sonar_fetcher` respects `Retry-After` on 429; paginates at 100/page; `max_total` caps total regardless of pagination |
| F14 LLM emits SQL in wrong dialect | Prompt explicitly names dialect + injects schema summary; summary.json records dialect; pr_comment notes if non-PG mode used |
| F9 can't detect framework | Falls back to generic "rewrite selectors for this DOM" prompt; `summary.json` flags confidence as low |
| `JOB_REPORT_TS` rename breaks external CI hooks | Back-compat alias `WAVE6A_REPORT_TS` maintained for one release; documented in HOWTO |
| Cross-job env-var leak | Orchestrator resets the var at start of each `run_analysis` call (same as 6A) |
| Multi-file F11 run produces huge pr_comment.md | `patch_emitter` appends per-file blocks; limited by `top_n` cap at the issue-source end |
| `ddl_parser` misses exotic DDL (CREATE TRIGGER, domain types) | Parser is regex-based; unsupported statements are silently skipped; test coverage documents the supported subset |
| F9 needs headless browser for URL fetch | `__page_url__` prefix is reserved but NOT implemented this wave; documented as "Phase 7 scope" in HOWTO |

---

## 14. Out of scope for Wave 6B

- **F13 (Code-from-Prompt Generator, 45 UCs, 6 frameworks)** — deferred to its own dedicated spec
- **Live DB introspection** for F14 — schema must come from DDL file or `__db_schema__` prefix
- **Headless-browser DOM fetch** for F9 — user provides HTML snapshot; `__page_url__` reserved
- **Selenium Grid / Playwright session replay** for F9 — just selector rewriting
- **Stored procedure DEBUG / trace mode** for F14 — just SQL emission
- **SonarCloud webhook server** — integration via `__sonar_issues__` prefix from a user-built sidecar; no built-in webhook receiver
- **Cross-wave coordination beyond `JOB_REPORT_TS`** — no new shared state

---

## 15. Appendix — design decisions

| Q | Decision | Rationale |
|---|---|---|
| Q1 | Code-browser scope: symbol nav + architecture viewer | No overlap with 6B |
| Q2 | All 5 features in one 6B wave, then dropped to 4 (user choice — skip F13) | Tighter wave; F13 deferred to dedicated spec |
| Q3 | F13 framework tiers (moot — F13 deferred) | — |
| Q4 | F15 intake: auto-scan + `__findings__` prefix hybrid | Wave 6A-style implicit coupling; no cross-agent API dependency |
| Q5 | F11 intake: API + file + prefix + `top_n` cap | Matches F5/F6 intake pattern; cap keeps prompt size bounded |
| Q6 | F9 scope: UI selector drift only | Narrow scope matches 4 backlog UCs; API drift overlaps with F5 |
| Q7 | F14 schema: DDL file + `__db_schema__` prefix, no live DB | Security and simplicity; DDL lives in version control anyway |
| Q8 | Shared `tools/patch_emitter.py` | DRY — all 4 agents produce PR-ready diffs identically |
| Q9 | Build order: smallest first (F9 → F11 → F14 → F15) | De-risks shared infrastructure on smallest-scope agent first |
| Q10 | Rename `WAVE6A_REPORT_TS` → `JOB_REPORT_TS` with back-compat alias | Clears the deferred nit from Wave 6A code review; generalises for future waves |
