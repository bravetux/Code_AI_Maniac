# AI Code Maniac — Effort Estimation

## Project Stats Summary

| Metric | Value |
|--------|-------|
| Total Python files | 83 |
| Total lines of Python code | ~13,659 |
| Total test files | 24 |
| Total documentation lines | ~9,314 |
| Total commits | 61 |
| Git insertions | 21,313 |
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
| **6** | **Phase 1 Agents (4 agents)** | Prompt engineering, structured output, domain knowledge | 8 | 12 | **20** |
| | *bug_analysis.py (132 lines)* | Severity classification, root cause analysis | — | 4 | — |
| | *static_analysis.py (91 lines)* | Linter integration + LLM semantic layer | — | 3 | — |
| | *code_flow.py (70 lines)* | Execution flow documentation | — | 2 | — |
| | *requirement.py (77 lines)* | Reverse-engineering requirements | — | 3 | — |
| **7** | **Phase 2 & 3 Agents (4 agents)** | Multi-turn prompting, context chaining, Mermaid syntax | 8 | 10 | **18** |
| | *code_design.py (192 lines)* | 3-turn design review conversation | — | 4 | — |
| | *mermaid.py (62 lines)* | Diagram generation, Mermaid syntax | — | 2 | — |
| | *comment_generator.py (85 lines)* | PR comment format, synthesis | — | 2 | — |
| | *commit_analysis.py (85 lines)* | Git history analysis | — | 2 | — |
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
| **Learning** | **94** |
| **Implementation** | **152** |
| **Total effort** | **246 hrs** |

---

## Calendar Days Calculation

| Constraint | Value |
|------------|-------|
| Hours per day | 8 (4 learning + 4 implementation) |
| Total hours | 246 |
| **Working days required** | **~31 days** |
| Working weeks (5-day) | **~6.2 weeks** |
| Calendar weeks (with weekends) | **~7.5 weeks** |

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

> **Note:** Phase 8 is compressed — realistically testing & docs would bleed into 2-3 extra days of buffer, making a practical estimate of ~33-35 working days.

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
| **Optimistic** (no blockers) | **31 days** | ~6 weeks |
| **Realistic** (some learning friction) | **35 days** | ~7 weeks |
| **Pessimistic** (AWS + Strands issues) | **42 days** | ~8.5 weeks |

For an intermediate Python programmer at **8 hrs/day (4 learning + 4 coding)**, this project would take approximately **7 weeks** to build from scratch, including all documentation and scripts.
