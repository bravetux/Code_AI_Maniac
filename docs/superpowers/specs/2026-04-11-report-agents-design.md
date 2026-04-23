# Report Agents & Progress Bar Fix — Design Spec

**Date:** 2026-04-11
**Status:** Approved

## Problem

1. Multi-file analysis produces individual feature results but no cohesive per-file or cross-file reports.
2. Reports are saved as separate markdown files per (file x feature) — no unified view.
3. No HTML output option for professional, polished reports.
4. Progress bar counts only the number of features (e.g., 4), ignoring that each feature runs once per file. With 3 files and 4 features, the bar should track 12 agents, not 4.

## Solution

Two new agents, a standalone HTML converter, new `.env` controls, and a two-phase progress bar.

---

## 1. Per-File Report Agent (`agents/report_per_file.py`)

**Purpose:** Assemble all selected feature results for a single source file into one structured markdown document.

**Input:**
- `file_path`: The source file being reported on
- `feature_results`: Dict of `{feature_name: result_dict}` for the features the user selected
- `language`: Detected language of the source file

**Output:** A single markdown string containing:
- Title with file name and analysis timestamp
- File metadata (path, language, size)
- One section per selected feature, in a logical reading order:
  1. Requirements (if selected)
  2. Code Flow (if selected)
  3. Code Design (if selected)
  4. Bug Analysis (if selected)
  5. Static Analysis (if selected)
  6. Mermaid Diagrams (if selected)
  7. PR Comments (if selected)
- Each section is rendered from the agent's result using structured formatting

**No LLM calls.** This agent is pure assembly and formatting — the analysis agents already produced the content.

**Execution:** Runs once per source file, after all analysis agents have completed for that file.

---

## 2. Consolidated Report Agent (`agents/report_consolidated.py`)

**Purpose:** Produce a single "mother document" that reads as a cohesive narrative about the entire codebase. Not a concatenation of per-file reports — a synthesized document with continuity between sections, explaining the bigger picture of why the code exists, how it works, and how modules relate.

**Input:**
- `per_file_reports`: List of per-file report markdown strings
- `all_results`: Full dict of `{file_path: {feature: result}}` for all files and features
- `file_paths`: Ordered list of analyzed files
- `features`: List of selected features
- `language`: Primary language

**Output:** A single markdown string structured as:
- Executive Summary / Overview
- Architecture & Module Relationships
- Per-module deep dives (ordered by dependency/logical flow, not alphabetically)
- Cross-cutting concerns (shared bugs, design patterns, security themes)
- Conclusion & Recommendations

**Three modes** controlled by `CONSOLIDATED_MODE` env var:

### `template` mode
- No LLM calls
- Structured assembly: TOC, per-file sections pulled from per-file reports, basic summary stats (total bugs, top severities, etc.)
- Sections are organized but not narratively connected

### `llm` mode
- Sends all feature results to Bedrock Claude as context
- Single prompt asking for a fully synthesized narrative document
- Prompt instructs the LLM to: explain why the code exists, trace data/control flow across files, identify architectural patterns, and produce a document that reads as a complete design document
- Uses `make_bedrock_model()` from `_bedrock.py`

### `hybrid` mode (default)
- Template skeleton provides the structure (TOC, section headings, per-file data)
- LLM calls generate:
  - Executive summary (synthesizing all results)
  - Cross-file narrative threads (how modules connect)
  - Architecture overview (high-level design from the code)
  - Conclusion tying everything together
- Balances cost/speed (fewer tokens than full LLM) with narrative quality

**Execution:** Runs once after all per-file reports are generated.

---

## 3. HTML Converter (`tools/python_html_converter.py`)

**Purpose:** Convert markdown reports to polished, professional HTML.

**Dual usage:**
1. **Standalone CLI:** `python tools/python_html_converter.py input.md output.html`
2. **Importable module:** Called by agents/orchestrator to auto-convert reports

**HTML features:**
- Professional typography and layout
- Syntax highlighting for code blocks (using Pygments)
- Collapsible sections for each major heading
- Sidebar table of contents with scroll-spy
- Print-friendly CSS (clean output when printed/PDF'd)
- Responsive design
- Self-contained (all CSS/JS inline, no external dependencies)

**Dependencies:** `markdown` and `pygments` Python packages (add to `requirements.txt`).

**Key functions:**
- `convert_md_to_html(md_content: str, title: str = "") -> str` — returns complete HTML string
- `convert_file(input_path: str, output_path: str) -> None` — file-to-file conversion
- `if __name__ == "__main__"` block for CLI usage

---

## 4. Environment Variables

Add to `.env.example` and `config/settings.py`:

```
REPORT_PER_FILE=true            # Generate per-file report (MD combining all features for one file)
REPORT_CONSOLIDATED=true        # Generate consolidated mother document
REPORT_FORMAT_MD=true           # Output markdown files
REPORT_FORMAT_HTML=true         # Output HTML files (requires MD to also be generated)
CONSOLIDATED_MODE=hybrid        # hybrid | llm | template
```

**Defaults:** All true, hybrid mode.

**Validation rules:**
- `REPORT_FORMAT_HTML=true` requires `REPORT_FORMAT_MD=true` (HTML is converted from MD)
- `REPORT_CONSOLIDATED=true` requires `REPORT_PER_FILE=true` (consolidated builds on per-file)
- `CONSOLIDATED_MODE` only applies when `REPORT_CONSOLIDATED=true`

---

## 5. Progress Bar — Two-Phase Design

### Phase 1: Analysis Progress

**Total:** `selected_features x number_of_files`

Example: 4 features, 3 files = 12 total agents.

Display: `st.progress(pct, text="Analyzing... 7/12 agents done")`

Events counted as done: `"complete"`, `"cached"`, `"error"` (same as current logic, but total is now correct).

### Phase 2: Report Generation Progress

Appears after Phase 1 reaches 100%.

**Total:** Number of per-file reports + (1 if consolidated enabled) + HTML conversion steps.

Example: 3 files, consolidated enabled, HTML enabled:
- 3 per-file MD reports
- 3 per-file HTML conversions
- 1 consolidated MD report
- 1 consolidated HTML conversion
- Total: 8 steps

Display: `st.progress(pct, text="Generating reports... 2/8")`

**New event types** for report tracking:
- `"report_start"` — report agent beginning
- `"report_complete"` — report agent finished
- `"report_error"` — report agent failed

---

## 6. Orchestrator Integration

### Current flow:
```
fetch files -> run features per file -> merge results -> save to DB -> save reports
```

### New flow:
```
fetch files
-> Phase 1: run features per file (analysis progress bar)
-> Phase 2: (report generation progress bar)
   -> generate per-file reports (if REPORT_PER_FILE=true)
   -> generate consolidated report (if REPORT_CONSOLIDATED=true)
   -> convert to HTML (if REPORT_FORMAT_HTML=true)
   -> save all to Reports/
-> save to DB
```

### Changes to `agents/orchestrator.py`:
- Import new agents: `report_per_file`, `report_consolidated`
- Import converter: `tools.python_html_converter`
- After analysis phases complete, check `.env` flags and run report generation
- Emit `"report_start"` / `"report_complete"` events for Phase 2 tracking
- Pass report file paths to `save_reports_to_disk()` (or replace that function)

---

## 7. Report Output Structure

```
Reports/20260411_143022/
  per_file/
    auth_service.md
    auth_service.html
    user_model.md
    user_model.html
    payment_handler.md
    payment_handler.html
  consolidated_report.md
  consolidated_report.html
```

- Directory named with timestamp (existing pattern)
- `per_file/` subdirectory for individual file reports
- Consolidated report at the root of the timestamp directory
- Only files enabled by `.env` flags are generated

---

## 8. Changes to `config/settings.py`

Add new fields to the `Settings` Pydantic model:

```python
report_per_file: bool = True
report_consolidated: bool = True
report_format_md: bool = True
report_format_html: bool = True
consolidated_mode: str = "hybrid"  # hybrid | llm | template
```

Validation: `consolidated_mode` must be one of the three allowed values.

---

## 9. Changes to `app/pages/1_Analysis.py`

- Fix progress total: `total = len(features) * len(files)` (excluding `commit_analysis`)
- Add Phase 2 rendering: after analysis progress hits 100%, show report generation progress
- New event types (`report_start`, `report_complete`, `report_error`) handled in the activity log with appropriate icons

---

## 10. Files to Create

| File | Purpose |
|------|---------|
| `agents/report_per_file.py` | Per-file report assembly agent |
| `agents/report_consolidated.py` | Consolidated mother document agent |
| `tools/python_html_converter.py` | MD-to-HTML converter (standalone + importable) |

## 11. Files to Modify

| File | Change |
|------|--------|
| `agents/orchestrator.py` | Add Phase 2 report generation after analysis |
| `app/pages/1_Analysis.py` | Fix progress total, add Phase 2 progress |
| `app/components/result_tabs.py` | Update save logic to use new report structure |
| `config/settings.py` | Add new env var fields |
| `.env.example` | Add new env variables |
| `requirements.txt` | Add `markdown`, `pygments` if not present |
| `db/queries/job_events.py` | Support new event types (no schema change needed — event_type is a string column) |
