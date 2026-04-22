# 1128 — Feature Backlog

Backlog of features to add to the AI Code Maniac platform (agent 1128) so it can serve as the base for the **294** code/test/modernization use cases marked `1128` in `PulseBacklog for OpenAIrena2.xlsx` (column H).

Feature IDs match column I of that sheet — every tagged row points to one or more `F#` below.

## Current capabilities (27 agents, for context)

**Phase 1 — Code Analysis:** Bug Analysis · Static Analysis · Code Flow · Requirements · Dependency Analysis · Code Complexity · Test Coverage · Duplication Detection · Performance Analysis · Type Safety · Architecture Mapper · License Compliance · Change Impact · Doxygen Docs · C Test Generator
**Phase 2:** Code Design · Mermaid · Refactoring Advisor · API Doc Generator · PR Comments
**Phase 3–4 — Security:** Secret Scan · Threat Model
**Commit Analysis:** Commit Analysis · Release Notes · Developer Activity · Commit Hygiene · Churn Analysis

The existing stack is strong on **analysis & reporting**. The gap is in **generation, modernization, and test authoring**, plus **pipeline-triggered execution**.

---

## A. Test Generation & QA

| ID | Feature | UCs | Notes |
|---|---|---:|---|
| F1 | **Multi-language Unit Test Generator** — extend `c_test_generator` to Java / Python / JS / TS / .NET / Kotlin / Swift / ABAP; mocks, parameterized, edge cases | 17 | Reuses `chunk_file` and AST tools; per-language framework adapters (pytest, JUnit, xUnit, Jest, …) |
| F2 | **Test Case Generator from User Stories** — intake from Jira / Azure DevOps / Qase; outputs positive, negative, functional, NFR cases | 77 | Needs Jira/ADO fetcher alongside existing GitHub/Gitea |
| F3 | **BDD / Gherkin Feature File Generator** — Given-When-Then; Cucumber / Robot Framework output | 4 | Shares spec-ingestion with F2 |
| F4 | **UI Automation Script Generator** — Selenium, Playwright, Cypress, Tosca; from spec or recorded session | 57 | Biggest single feature; needs recorder adapter |
| F5 | **API Test Generator from OpenAPI/Swagger** — REST Assured, xUnit, Postman collections | 16 | Fits neatly beside existing API Doc Generator |
| F6 | **Performance / Load Test Script Generator** — JMeter / Gatling; LoadRunner→JMeter migrator | 7 |   |
| F7 | **Cross-Browser & Visual Regression Agent** — DOM/screenshot diff across browsers | 5 | Needs headless browser tool |
| F8 | **Test Data Generator** — synthetic, rule-based, boundary, negative, PII-safe | 17 |   |
| F9 | **Test Maintenance / Self-Healing Agent** — rewrites scripts when selectors/mapping docs change | 4 |   |
| F10 | **Traceability Matrix + Coverage Gap Finder** — stories ↔ tests ↔ defects | 8 | Builds on `test_coverage` |
| F11 | **SonarQube Fix Automation** — ingest Sonar issues → PR with patches | 5 | Pairs with F15 |
| F12 | **Defect Analytics & Triage** — cluster defects, RCA, trend reports | 7 |   |

## B. Code Generation from Intent

| ID | Feature | UCs | Notes |
|---|---|---:|---|
| F13 | **Code-from-Prompt Generator** — multi-language, framework-aware (React / Spring / PEGA / PySpark / ABAP / RAML) | 45 | Catch-all for "generate X from prompt" UCs |
| F14 | **NL → SQL / Stored-Procedure Generator** — schema-aware, RLS-aware | 6 | Aligns with AWS QuickSight Q direction |
| F15 | **Auto-Fix / Patch Generator** — produce the actual PR diff, not just "suggestions" | 19 | Natural extension of existing Bug Analysis + Refactoring Advisor |
| F16 | **Green-Code / Sustainability Advisor** — energy / resource hotspots + rewrites | 2 |   |
| F17 | **Dead-Code / Unused-Symbol Detector** — cross-repo, multi-language | 3 | Complements existing `duplication_detection` |
| F18 | **Code Optimizer Agent** — perf + readability rewrites (e.g., Java response-time) | 15 | Beyond Refactoring Advisor — outputs full rewritten files |
| F19 | **IDE / Copilot Bridge** — VS Code + IntelliJ inline suggestion adapter | 42 | Many UCs assume Copilot-style IDE loop |

## C. Code Review Enhancements

| ID | Feature | UCs | Notes |
|---|---|---:|---|
| F20 | **CI/CD-Triggered Review Webhook** — Jenkins, GitHub Actions, Bitbucket, GitLab, Azure DevOps | 31 | Today reviews are user-invoked in Streamlit — this adds server mode |
| F21 | **Pre-Commit / Staged-Change Reviewer** — git hook; reviews only the diff | 2 |   |
| F22 | **Custom Rule-Book Reviewer** — ingest org-specific guideline docs; enforce per-stack | 37 | Heavy RAG overlap — candidate for joint work with 887 |
| F23 | **Multi-Language/Stack Expansion Pack** — extend reviewers to ABAP/SAP, Informatica, PEGA, RPG, 4GL, PySpark, Tibco, COBOL | 18 |   |
| F24 | **API-Contract Conformance Checker** — code ↔ declared Swagger/OpenAPI | 2 |   |
| F25 | **Accessibility / A11y Validator** — WCAG rule engine | (0)* | Listed for completeness; UC-0109 slotted under F-review fallback |

\* F25 currently shows 0 tagged rows because A11y UCs didn't hit the keyword; add UC-0109 manually if desired.

## D. Legacy Modernization

| ID | Feature | UCs | Notes |
|---|---|---:|---|
| F26 | **Legacy-to-Modern Translator** — COBOL / RPG / Smalltalk / VB / 4GL / Tibco → Java / Python / .NET Core / Spring Boot | 10 | Business-logic-preserving; consider pairing with AWS Transform |
| F27 | **Mainframe Business-Rule Extractor** — JCL / COBOL → NL rule summaries + docs | 2 |   |
| F28 | **Microservice Decomposition Advisor** — monolith → service boundaries + scaffold | 2 |   |
| F29 | **Schema / Data-Element Mapper** — NLU-based source↔target field alignment | 4 |   |
| F30 | **DB Migration Translator** — Oracle ↔ PostgreSQL, PL/SQL → PL/pgSQL, data-copy scripts | 1 |   |
| F31 | **ETL / Workflow Migrator** — NiFi → Airflow DAG; batch → cloud ETL; K2/Polymer → React | 3 |   |
| F32 | **Legacy Deployment Script Generator** — IIS, env vars, Windows Services | 1 |   |
| F33 | **Parity Test Generator** — functional equivalence between legacy and new system | 1 |   |
| F34 | **Reverse-Engineering Documentation Pack** — bundled Doxygen + Mermaid + Architecture Mapper tuned for undocumented legacy | 7 | Mostly orchestration over existing agents |

## E. Spec & Design Documents

| ID | Feature | UCs | Notes |
|---|---|---:|---|
| F35 | **Software Design Doc / HLD-LLD Generator** — BRD / SOP → SDD | 2 |   |
| F36 | **Tech-Spec Generator from Recorded SME Sessions** — transcript ingestion → spec + tests | 8 | Needs Transcribe or equivalent upstream |
| F37 | **Swagger/OpenAPI Generator from Code OR Requirements** — bidirectional | 2 | Extends existing API Doc Generator |

---

## Proposed phasing

**Phase 5 — Quick wins (reuse existing infra):** F1, F2, F3, F8, F17, F20, F21, F24, F37
**Phase 6 — Medium lift:** F4, F5, F6, F9, F10, F11, F13, F14, F15, F22, F23
**Phase 7 — Heavy lift (net-new tools):** F7, F12, F25
**Phase 8 — Modernization pack:** F26 – F34 *(separate orchestrator profile — different inputs/outputs from daily code review)*
**Phase 9 — Design-doc pack:** F35, F36 *(RAG-heavy — candidate for joint work with agent 887)*

---

## Coverage summary

- **294** use cases tagged to 1128 (column H in `PulseBacklog for OpenAIrena2.xlsx`)
- **Top-pressure features:** F2 (77), F4 (57), F13 (45), F19 (42), F22 (37), F20 (31)
- These six features alone unlock **~288** of the 294 UCs (with overlap)
