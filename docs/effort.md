# AI Code Maniac — Effort Estimation

## Project Stats Summary

| Metric | Value |
|--------|-------|
| Total Python files | 170 |
| Total lines of Python code | ~30,500 |
| Agents + tools Python files | 77 (~12,953 lines) |
| Total test files | 45 |
| Total documentation lines | ~18,800 |
| Total commits | 124 |
| Git insertions | 89,118 |
| Config/infra files | 7+ |

---

## Assumptions

- **Developer profile:** Intermediate Python programmer
- **Daily schedule:** 4 hrs learning + 4 hrs implementation = 8 hrs/day max
- **Work week:** 5 days

---

## Breakdown by Work Area

| # | Work Area | Learning Topics | Learning (hrs) | Implementation (hrs) | Total (hrs) |
|---|-----------|-----------------|:-:|:-:|:-:|
| **1** | **Project Setup & Environment** | Python venv, `.env`, pip, project structure | 2 | 3 | **5** |
| **2** | **Streamlit Frontend — Core** | Streamlit framework, session state, multi-page apps | 8 | 12 | **20** |
| | *Home.py (217 lines)* | Dashboard layout, navigation | — | 3 | — |
| | *Analysis page (197 lines)* | Forms, source selection, job triggers | — | 3 | — |
| | *History page (376 lines)* | Search, filtering, data display | — | 4 | — |
| | *Commits page (171 lines)* | Git integration UI | — | 2 | — |
| **3** | **Streamlit Components** | Component patterns, Mermaid rendering, reusable widgets | 4 | 10 | **14** |
| | *result_tabs.py (604 lines)* | Tabs, expanders, complex layouts | — | 5 | — |
| | *source_selector.py (324 lines)* | Dynamic forms, file pickers | — | 3 | — |
| | *feature_selector.py, sidebar_profile, mermaid_renderer* | State management | — | 2 | — |
| **4** | **AWS Bedrock + Strands Agents** | AWS SDK (boto3), Bedrock API, Strands Agents framework, IAM | 12 | 8 | **20** |
| | *_bedrock.py (101 lines)* | Model invocation, credentials | — | 3 | — |
| | *Agent tool registration & prompt patterns* | Strands tool decorator, system prompts | — | 5 | — |
| **5** | **Agent: Orchestrator** | Concurrent execution, 3-phase pipeline, ThreadPoolExecutor | 8 | 12 | **20** |
| | *orchestrator.py (365 lines)* | Parallel agent dispatch, result aggregation, error handling | — | 12 | — |
| **6** | **Phase 1 Code-Analysis Agents (20 agents)** | Prompt engineering, structured output, domain knowledge across 20 analysis concerns | 8 | 12 | **20** |
| | *bug_analysis.py (132 lines)* | Severity classification, root cause analysis | — | 4 | — |
| | *static_analysis.py (91 lines)* | Linter integration + LLM semantic layer | — | 3 | — |
| | *code_flow.py (70 lines)* | Execution flow documentation | — | 2 | — |
| | *requirement.py (77 lines)* | Reverse-engineering requirements | — | 3 | — |
| | *+ 16 more: code_design, mermaid, refactoring_advisor, api_doc_generator, comment_generator, dependency_analysis, code_complexity, duplication_detection, type_safety, architecture_mapper, performance_analysis, test_coverage, c_test_generator, change_impact, license_compliance, doxygen* | Hours **not** re-estimated — see caveats | — | — | — |
| **7** | **Phase 2 & 3 Agents — Commit + Security (7 agents)** | Multi-turn prompting, context chaining, git history, STRIDE threat modelling | 8 | 10 | **18** |
| | *commit_analysis / release_notes / developer_activity / commit_hygiene / churn_analysis* | 5 commit-history agents | — | 6 | — |
| | *secret_scan / threat_model* | 2 security agents (phase 0 regex + phase 3 LLM) | — | 4 | — |
| **7a** | **Phase 5 — Quick Wins (7 agents + 2 CLI tools)** | Test generation idioms, OpenAPI spec parsing, dead-code AST analysis, webhook server plumbing | 12 | 110 | **122** |
| | *unit_test_generator.py (F1)* | pytest / JUnit scaffolds from signatures | — | 16 | — |
| | *story_test_generator.py (F2)* | Story-driven integration tests | — | 16 | — |
| | *gherkin_generator.py (F3)* | BDD feature files | — | 14 | — |
| | *test_data_generator.py (F8)* | Fixtures, edge-case payloads | — | 14 | — |
| | *dead_code_detector.py (F17)* | AST-level unreachable code detection | — | 16 | — |
| | *api_contract_checker.py (F24)* | OpenAPI spec vs handlers drift | — | 16 | — |
| | *openapi_generator.py (F37)* | Emit OpenAPI 3.x from annotated source | — | 16 | — |
| | *tools/webhook_server.py (F20)* | FastAPI / Flask webhook endpoint | — | 1 | — |
| | *tools/precommit_reviewer.py (F21)* | Pre-commit hook CLI entry | — | 1 | — |
| | *tools/openapi_parser.py, tools/spec_fetcher.py* | Shared spec parsing + fetching infra | — | included above | — |
| **7b** | **Phase 6 — Wave 6A (3 agents + 3 pipeline tools)** | OpenAPI-driven test design, Locust/k6 load profiles, requirements-to-test traceability scanning | 10 | 70 | **80** |
| | *api_test_generator.py (F5)* | Postman collection emit from OpenAPI | — | 22 | — |
| | *perf_test_generator.py (F6)* | Locust / k6 load profiles with ramp/soak/spike | — | 22 | — |
| | *traceability_matrix.py (F10)* | Requirements &harr; stories &harr; tests matrix + UI helper | — | 22 | — |
| | *tools/postman_emitter.py* | Collection serialiser | — | 1 | — |
| | *tools/load_profile_builder.py* | Ramp/soak/spike profile DSL | — | 1.5 | — |
| | *tools/test_scanner.py* | Repo-wide pytest discovery for F10 | — | 1.5 | — |
| **7c** | **Phase 6 — Wave 6B (4 agents + 3 pipeline tools)** | Unified-diff patch emission, Selenium/Playwright/Cypress DOM rewriting, SonarQube issue ingestion, PostgreSQL RLS-aware SQL generation, DDL parsing | 12 | 88 | **100** |
| | *self_healing_agent.py (F9)* | DOM-aware Selenium/Playwright/Cypress test rewrite | — | 22 | — |
| | *sonar_fix_agent.py (F11)* | SonarQube issue ingestion + PR-ready patches | — | 22 | — |
| | *sql_generator.py (F14)* | NL &rarr; SQL / stored procedure, RLS-aware | — | 22 | — |
| | *auto_fix_agent.py (F15)* | Auto-fix diff from Bug Analysis + Refactoring Advisor findings | — | 22 | — |
| | *tools/patch_emitter.py* | Shared unified-diff emitter (CRLF / empty-base / no-newline edge cases) | — | — | — |
| | *tools/sonar_fetcher.py* | Sonar REST API fetcher + JSON export parser | — | — | — |
| | *tools/ddl_parser.py* | DDL schema parser (incl. NUMERIC(12,2) edge cases) | — | — | — |
| **8** | **Tools Layer** | GitHub API (PyGithub), Gitea API (httpx), file I/O, subprocess | 8 | 12 | **20** |
| | *fetch_github.py (71 lines)* | GitHub REST API, token auth | — | 2 | — |
| | *fetch_gitea.py (80 lines)* | Gitea API integration | — | 2 | — |
| | *clone_repo.py (148 lines)* | Git clone, URL parsing, shallow clones | — | 3 | — |
| | *fetch_local.py (80 lines)* | File system, line range extraction | — | 1 | — |
| | *run_linter.py (69 lines)* | Subprocess, flake8/pylint/semgrep | — | 2 | — |
| | *cache.py, chunk_file.py, language_detect.py* | Caching strategy, chunking | — | 2 | — |
| **9** | **DuckDB Database Layer** | DuckDB, schema design, SQL queries | 6 | 8 | **14** |
| | *Schema (12 files, 476 lines)* | Table design: jobs, cache, chunks, history, presets | — | 4 | — |
| | *CRUD queries (9 modules)* | Parameterized queries, migrations | — | 4 | — |
| **10** | **Config & Prompt Templates** | Prompt engineering, template design, Pydantic settings | 8 | 16 | **24** |
| | *config/ (6,445 lines across 8 files)* | 156 templates across 13 categories | — | 12 | — |
| | *Pydantic settings, language mapping* | Validation, type safety | — | 4 | — |
| **11** | **Report Generation** | Markdown generation, HTML conversion, Pygments | 4 | 8 | **12** |
| | *report_per_file.py (191 lines)* | Per-file markdown reports | — | 3 | — |
| | *report_consolidated.py (359 lines)* | Mother document, 3 synthesis modes | — | 3 | — |
| | *python_html_converter.py (489 lines)* | Syntax highlighting, HTML styling | — | 2 | — |
| **12** | **Comparison Agent** | Diff analysis, side-by-side comparison | 2 | 4 | **6** |
| | *comparison.py (119 lines)* | | — | 4 | — |
| **13** | **Testing** | pytest, mocking, fixtures, test design | 6 | 14 | **20** |
| | *24 test files (~2,400 lines)* | Unit tests, integration tests, conftest setup | — | 14 | — |
| **14** | **Docker / Gitea Setup** | Docker Compose, Gitea administration | 4 | 3 | **7** |
| | *docker-compose.yml, app.ini* | Container config, health checks | — | 2 | — |
| | *Gitea API token setup* | Integration testing | — | 1 | — |
| **15** | **Documentation** | Technical writing, Mermaid diagrams, architecture docs | 4 | 16 | **20** |
| | *README.md (~15KB)* | Full project docs with diagrams | — | 6 | — |
| | *Architecture/design docs (9,314 lines)* | Design specs, plans, templates guide | — | 8 | — |
| | *CLAUDE.md, use case, presentation.html* | Context docs, slides | — | 2 | — |
| **16** | **Scripts & Polish** | Batch scripting, Streamlit deployment, edge cases | 2 | 4 | **6** |
| | *startup.bat, .env.example, pytest.ini* | Startup automation, config templates | — | 4 | — |

---

## Grand Total

| Category | Hours |
|----------|------:|
| **Learning** | **128** |
| **Implementation** | **420** |
| **Total effort** | **548 hrs** |

> Baseline rows (1–16) retained from the original estimate; Phase 5 Quick Wins (row 7a) adds **122 hrs**, Wave 6A (row 7b) adds **80 hrs**, and Wave 6B (row 7c) adds **100 hrs** on top of the **246 hr** baseline.

---

## Calendar Days Calculation

| Constraint | Value |
|------------|-------|
| Hours per day | 8 (4 learning + 4 implementation) |
| Total hours | 548 |
| **Working days required** | **~69 days** |
| Working weeks (5-day) | **~13.7 weeks** |
| Calendar weeks (with weekends) | **~16.5 weeks** |

---

## Phased Timeline (Recommended Order)

| Phase | Days | What's Built |
|-------|------|-------------|
| **Phase 1: Foundation** (Days 1-5) | 5 | Setup, DuckDB schema, config/settings, `.env` |
| **Phase 2: Tools Layer** (Days 6-9) | 4 | GitHub/Gitea/local fetch, clone, linter, cache, chunking |
| **Phase 3: Bedrock + Base Agents** (Days 10-15) | 6 | AWS Bedrock integration, 4 Phase-1 agents |
| **Phase 4: Advanced Agents** (Days 16-19) | 4 | Phase-2/3 agents (design, mermaid, PR comments, commits) |
| **Phase 5: Orchestrator** (Days 20-22) | 3 | 3-phase pipeline, parallel execution, result aggregation |
| **Phase 6: Streamlit UI** (Days 23-27) | 5 | All pages, components, state management |
| **Phase 7: Reports + Templates** (Days 28-30) | 3 | Report agents, HTML converter, 156 prompt templates |
| **Phase 8: Testing + Docs + Polish** (Days 31-31) | 1 | Test suite, README, startup scripts |
| **Phase 5 Quick Wins: Test-gen + CI hooks** (Days 32-47) | ~16 | 7 agents (unit/story/gherkin/test-data/dead-code/api-contract/openapi) + webhook server + pre-commit reviewer |
| **Phase 6 Wave 6A: API+Perf+Traceability** (Days 48-56) | ~9 | 3 agents (api_test_generator F5, perf_test_generator F6, traceability_matrix F10) + postman_emitter / load_profile_builder / test_scanner tools |
| **Phase 6 Wave 6B: Self-Heal+Sonar+SQL+Auto-Fix** (Days 57-69) | ~13 | 4 agents (self_healing_agent F9, sonar_fix_agent F11, sql_generator F14, auto_fix_agent F15) + patch_emitter / sonar_fetcher / ddl_parser tools. F13 deferred. |

> **Note:** Phase 8 is compressed — realistically testing & docs would bleed into 2-3 extra days of buffer, making a practical estimate of ~33-35 working days for the original baseline. Phase 5 Quick Wins, Wave 6A, and Wave 6B add another ~38 working days on top, bringing the cumulative effort to ~69 working days.

---

## Risk Factors That Could Extend This

| Risk | Impact |
|------|--------|
| AWS IAM/Bedrock permission issues | +1-2 days debugging |
| Strands Agents framework unfamiliarity (sparse docs) | +2-3 days |
| Prompt engineering iteration (getting quality LLM outputs) | +3-5 days |
| Streamlit quirks (session state, reruns, async) | +1-2 days |
| Gitea/Docker networking issues | +1 day |

With risks factored in: **35-42 working days** is a realistic range.

---

## Final Summary

| Scenario | Working Days | Calendar Weeks |
|----------|:-----------:|:--------------:|
| **Baseline — Optimistic** (no blockers) | **31 days** | ~6 weeks |
| **Baseline — Realistic** (some learning friction) | **35 days** | ~7 weeks |
| **Baseline — Pessimistic** (AWS + Strands issues) | **42 days** | ~8.5 weeks |
| **Baseline + Phase 5 Quick Wins** | **~51 days** | ~10 weeks |
| **Baseline + Phase 5 + Wave 6A** | **~56 days** | ~11–13.5 weeks |
| **Baseline + Phase 5 + Wave 6A + Wave 6B (current state)** | **~69 days** | ~13.7–16.5 weeks |

For an intermediate Python programmer at **8 hrs/day (4 learning + 4 coding)**, the original baseline would take approximately **7 weeks** to build from scratch. With Phase 5 Quick Wins (7 agents + webhook/pre-commit tooling), Wave 6A (3 agents + 3 pipeline tools), and Wave 6B (4 agents + patch_emitter / sonar_fetcher / ddl_parser) layered on top, the cumulative effort is approximately **13.7 weeks** (optimistic) to **16.5 weeks** (calendar, including weekends).

---

## Caveats

- **Baseline rows (1–16) were not re-estimated** against the current, enlarged codebase — their hour figures match the original pre-Phase-5 spreadsheet. If you want a fully refreshed estimate, the baseline rows (especially Phase 1 at 20 agents vs the original 4, the Tools layer which has nearly doubled, and Testing which now covers agents that did not exist before) should be re-walked agent by agent.
- **Phase 5 / Wave 6A / Wave 6B estimates are per-agent averages** (~16 hrs, ~22 hrs, and ~22 hrs respectively). Real dev time was spec + plan + code + tests across 2–3 days per Wave 6A/6B agent. The tool-layer line items (postman_emitter, load_profile_builder, test_scanner, webhook_server, precommit_reviewer, openapi_parser, spec_fetcher, patch_emitter, sonar_fetcher, ddl_parser) are bundled with their parent agent(s) for simplicity rather than broken out individually.
- **Learning hours for Phase 5 / Wave 6A / Wave 6B** cover OpenAPI 3.x spec structure, Postman collection schema, Locust / k6 load-profile DSLs, pytest AST scanning, FastAPI webhook patterns, unified-diff emission edge cases (CRLF, empty base, trailing newline, bare empty context), DOM-aware selector rewriting for Selenium/Playwright/Cypress, SonarQube REST API surface, and PostgreSQL RLS-aware SQL generation.
- **F13 was explicitly deferred** from the Wave 6B scope and is not counted toward either the agent total or the hour estimates.
- **Wave 6B introduced the `JOB_REPORT_TS` env var** (renamed from `WAVE6A_REPORT_TS`, with a back-compat alias maintained for one release) so all Wave 6A/6B agents share a single `Reports/<ts>/` folder per job.
- **Commit count (124) and insertions (89,118)** are from `git log` at refresh time; cache / DB files are excluded from the Python line count (`find agents tools -name '*.py' | xargs wc -l` — `venv/` and `Reports/` excluded).
