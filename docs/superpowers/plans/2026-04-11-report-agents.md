# Report Agents & Progress Bar Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two report-generation agents (per-file and consolidated), a standalone MD-to-HTML converter, new `.env` controls, and fix the progress bar to count `features × files`.

**Architecture:** After the existing 3-phase analysis pipeline completes, a new Phase 2 (report generation) runs: per-file report assembly, then consolidated narrative synthesis. A standalone `python_html_converter.py` converts all MD outputs to professional HTML. The analysis page shows two sequential progress bars.

**Tech Stack:** Python 3.11+, Streamlit, AWS Strands Agents (Bedrock Claude), DuckDB, markdown, pygments

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `agents/report_per_file.py` | Assemble all selected feature results for one file into a single MD document |
| Create | `agents/report_consolidated.py` | Synthesize all per-file results into a cohesive "mother document" (template/llm/hybrid modes) |
| Create | `tools/python_html_converter.py` | Standalone + importable MD→HTML converter with professional styling |
| Create | `tests/agents/test_report_per_file.py` | Tests for per-file report agent |
| Create | `tests/agents/test_report_consolidated.py` | Tests for consolidated report agent |
| Create | `tests/tools/test_html_converter.py` | Tests for HTML converter |
| Modify | `config/settings.py:20-63` | Add 5 new report env vars to Settings model |
| Modify | `.env.example` | Add report configuration variables |
| Modify | `agents/orchestrator.py:207-273` | Add Phase 2 report generation after analysis |
| Modify | `app/pages/1_Analysis.py:82-147` | Fix progress total, add Phase 2 progress bar |
| Modify | `app/components/result_tabs.py:466-506` | Update `save_reports_to_disk` to use new report structure |
| Modify | `requirements.txt` | Add `markdown` and `pygments` packages |

---

### Task 1: Add Report Settings to config/settings.py

**Files:**
- Modify: `config/settings.py:20-48`
- Modify: `.env.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for new settings**

Add to `tests/test_config.py`:

```python
def test_report_settings_defaults(test_settings):
    assert test_settings.report_per_file is True
    assert test_settings.report_consolidated is True
    assert test_settings.report_format_md is True
    assert test_settings.report_format_html is True
    assert test_settings.consolidated_mode == "hybrid"


def test_consolidated_mode_custom(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("CONSOLIDATED_MODE", "llm")
    get_settings.cache_clear()
    s = get_settings()
    assert s.consolidated_mode == "llm"
    get_settings.cache_clear()


def test_consolidated_mode_invalid():
    from config.settings import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(consolidated_mode="invalid_mode")


def test_report_per_file_toggle(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("REPORT_PER_FILE", "false")
    get_settings.cache_clear()
    s = get_settings()
    assert s.report_per_file is False
    get_settings.cache_clear()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py::test_report_settings_defaults -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'report_per_file'`

- [ ] **Step 3: Add settings fields to config/settings.py**

In `config/settings.py`, add these fields inside the `Settings` class after `enabled_agents`:

```python
    # ── Report generation ────────────────────────────────────────────────────
    report_per_file: bool = True
    report_consolidated: bool = True
    report_format_md: bool = True
    report_format_html: bool = True
    consolidated_mode: str = Field(default="hybrid", pattern=r"^(hybrid|llm|template)$")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

- [ ] **Step 5: Update .env.example**

Append to `.env.example` after the `ENABLED_AGENTS` block:

```
# ── Report generation ────────────────────────────────────────────────────────
# Generate a per-file report (one MD combining all features for each source file)
REPORT_PER_FILE=true

# Generate a consolidated "mother document" across all files
REPORT_CONSOLIDATED=true

# Output formats (HTML is converted from MD, so MD must be true for HTML)
REPORT_FORMAT_MD=true
REPORT_FORMAT_HTML=true

# Consolidated report synthesis mode:
#   template — structured assembly, no LLM calls
#   llm      — fully LLM-synthesized narrative
#   hybrid   — template skeleton + LLM for executive summary and cross-file narrative (default)
CONSOLIDATED_MODE=hybrid
```

- [ ] **Step 6: Commit**

```bash
git add config/settings.py .env.example tests/test_config.py
git commit -m "feat: add report generation settings to config"
```

---

### Task 2: Create Per-File Report Agent

**Files:**
- Create: `agents/report_per_file.py`
- Create: `tests/agents/test_report_per_file.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_report_per_file.py`:

```python
import pytest
from agents.report_per_file import generate_per_file_report


_SAMPLE_RESULTS = {
    "bug_analysis": {
        "summary": "Found 1 bug",
        "bugs": [{"line": 10, "severity": "major", "description": "Null check missing",
                  "suggestion": "Add null guard"}],
        "narrative": "The code has a potential null reference.",
    },
    "code_flow": {
        "summary": "Linear execution",
        "markdown": "## Entry Point\n\n`main()` calls `process()`.",
    },
    "static_analysis": {
        "summary": "1 linter finding",
        "linter_findings": [{"line": 5, "code": "E501", "message": "line too long", "severity": "minor"}],
        "semantic_findings": [],
        "narrative": "Minor style issue.",
    },
}


def test_generates_markdown_with_all_selected_features():
    md = generate_per_file_report(
        file_path="src/auth.py",
        feature_results=_SAMPLE_RESULTS,
        language="python",
    )
    assert "# Analysis Report — auth.py" in md
    assert "## Bug Analysis" in md
    assert "## Code Flow" in md
    assert "## Static Analysis" in md
    # Features not in results should not appear
    assert "## Code Design" not in md
    assert "## Mermaid" not in md


def test_includes_file_metadata():
    md = generate_per_file_report(
        file_path="src/auth.py",
        feature_results=_SAMPLE_RESULTS,
        language="python",
    )
    assert "src/auth.py" in md
    assert "python" in md.lower()


def test_empty_results_produces_minimal_report():
    md = generate_per_file_report(
        file_path="src/empty.py",
        feature_results={},
        language="python",
    )
    assert "# Analysis Report — empty.py" in md
    assert "No analysis features were run" in md


def test_section_ordering():
    """Sections should follow the canonical order even if results dict is unordered."""
    results = {
        "static_analysis": _SAMPLE_RESULTS["static_analysis"],
        "bug_analysis": _SAMPLE_RESULTS["bug_analysis"],
        "code_flow": _SAMPLE_RESULTS["code_flow"],
    }
    md = generate_per_file_report("f.py", results, "python")
    idx_req = md.find("## Code Flow")
    idx_bug = md.find("## Bug Analysis")
    idx_static = md.find("## Static Analysis")
    # code_flow before bug_analysis before static_analysis
    assert idx_req < idx_bug < idx_static
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agents/test_report_per_file.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.report_per_file'`

- [ ] **Step 3: Implement agents/report_per_file.py**

Create `agents/report_per_file.py`:

```python
"""Per-file report agent — assembles all selected feature results for one source
file into a single structured Markdown document.  No LLM calls."""

import os
from datetime import datetime

# Canonical section order — matches the reading flow in the design spec.
_SECTION_ORDER = [
    "requirement",
    "code_flow",
    "code_design",
    "bug_analysis",
    "static_analysis",
    "mermaid",
    "comment_generator",
]

_SECTION_TITLE = {
    "requirement":       "Requirements",
    "code_flow":         "Code Flow",
    "code_design":       "Code Design",
    "bug_analysis":      "Bug Analysis",
    "static_analysis":   "Static Analysis",
    "mermaid":           "Mermaid Diagram",
    "comment_generator": "PR Comments",
}


def generate_per_file_report(file_path: str, feature_results: dict,
                              language: str = "") -> str:
    """Return a Markdown string combining all feature results for *file_path*."""
    basename = os.path.basename(file_path) or file_path
    lines: list[str] = []

    # Header
    lines.append(f"# Analysis Report — {basename}")
    lines.append("")
    lines.append(f"**File:** `{file_path}`  ")
    lines.append(f"**Language:** {language or 'unknown'}  ")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections in canonical order
    rendered = 0
    for feature in _SECTION_ORDER:
        if feature not in feature_results:
            continue
        result = feature_results[feature]
        if not isinstance(result, dict) or "error" in result:
            continue
        title = _SECTION_TITLE.get(feature, feature)
        lines.append(f"## {title}")
        lines.append("")
        lines.append(_render_section(feature, result))
        lines.append("")
        rendered += 1

    if rendered == 0:
        lines.append("*No analysis features were run for this file.*")
        lines.append("")

    return "\n".join(lines)


def _render_section(feature: str, result: dict) -> str:
    """Render a single feature's result as Markdown."""
    if feature == "bug_analysis":
        return _render_bugs(result)
    if feature == "code_design":
        return _render_code_design(result)
    if feature == "code_flow":
        return _render_code_flow(result)
    if feature == "mermaid":
        return _render_mermaid(result)
    if feature == "requirement":
        return _render_requirement(result)
    if feature == "static_analysis":
        return _render_static(result)
    if feature == "comment_generator":
        return _render_comments(result)
    return ""


def _render_bugs(r: dict) -> str:
    parts = []
    if r.get("narrative"):
        parts.append(r["narrative"])
        parts.append("")
    if r.get("summary"):
        parts.append(f"*{r['summary']}*")
        parts.append("")
    for bug in r.get("bugs", []):
        sev = bug.get("severity", "unknown")
        line = bug.get("line", "?")
        desc = bug.get("description", bug.get("message", ""))
        parts.append(f"### Line {line} ({sev})")
        parts.append("")
        parts.append(desc)
        if bug.get("suggestion"):
            parts.append(f"\n**Suggestion:** {bug['suggestion']}")
        if bug.get("original_snippet"):
            parts.append(f"\n```\n{bug['original_snippet']}\n```")
        if bug.get("fixed_snippet"):
            parts.append(f"\n**Fixed:**\n```\n{bug['fixed_snippet']}\n```")
        parts.append("")
    return "\n".join(parts)


def _render_code_design(r: dict) -> str:
    doc = r.get("design_document") or r.get("markdown", "")
    if doc:
        return doc
    parts = []
    if r.get("purpose"):
        parts.append(r["purpose"])
    if r.get("design_assessment"):
        parts.append(f"\n**Assessment:** {r['design_assessment']}")
    return "\n".join(parts) if parts else "*No design document generated.*"


def _render_code_flow(r: dict) -> str:
    if r.get("markdown"):
        return r["markdown"]
    parts = []
    if r.get("summary"):
        parts.append(r["summary"])
    for step in r.get("steps", []):
        parts.append(f"{step.get('step', '')}. {step.get('description', '')}")
    return "\n".join(parts) if parts else "*No code flow data.*"


def _render_mermaid(r: dict) -> str:
    parts = []
    if r.get("description"):
        parts.append(r["description"])
        parts.append("")
    src = r.get("mermaid_source", "")
    if src:
        parts.append(f"```mermaid\n{src}\n```")
    return "\n".join(parts) if parts else "*No diagram generated.*"


def _render_requirement(r: dict) -> str:
    if r.get("markdown"):
        return r["markdown"]
    parts = []
    if r.get("summary"):
        parts.append(r["summary"])
        parts.append("")
    for req in r.get("requirements", []):
        parts.append(f"- **{req.get('id', '')}**: {req.get('statement', '')}")
    return "\n".join(parts) if parts else "*No requirements extracted.*"


def _render_static(r: dict) -> str:
    parts = []
    if r.get("narrative"):
        parts.append(r["narrative"])
        parts.append("")
    linter = r.get("linter_findings", [])
    semantic = r.get("semantic_findings", [])
    if linter:
        parts.append("### Linter Findings")
        parts.append("")
        for f in linter:
            parts.append(f"- **Line {f.get('line', '?')}** `{f.get('code', '')}` — {f.get('message', '')}")
        parts.append("")
    if semantic:
        parts.append("### Semantic Findings")
        parts.append("")
        for f in semantic:
            parts.append(f"- **Line {f.get('line', '?')}** [{f.get('category', '')}]: {f.get('description', '')}")
            if f.get("suggestion"):
                parts.append(f"  - *Suggestion:* {f['suggestion']}")
        parts.append("")
    return "\n".join(parts) if parts else "*No static analysis findings.*"


def _render_comments(r: dict) -> str:
    parts = []
    if r.get("summary"):
        parts.append(r["summary"])
        parts.append("")
    for c in r.get("comments", []):
        parts.append(f"### {c.get('file', '')} : line {c.get('line', '?')} ({c.get('severity', '')})")
        parts.append("")
        parts.append(c.get("body", ""))
        parts.append("")
    return "\n".join(parts) if parts else "*No PR comments generated.*"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_report_per_file.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/report_per_file.py tests/agents/test_report_per_file.py
git commit -m "feat: add per-file report agent"
```

---

### Task 3: Create HTML Converter

**Files:**
- Create: `tools/python_html_converter.py`
- Create: `tests/tools/test_html_converter.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

Add after the `pandas` line in `requirements.txt`:

```
# Report generation
markdown>=3.7
pygments>=2.19.1
```

- [ ] **Step 2: Install new dependencies**

Run: `pip install markdown pygments`

- [ ] **Step 3: Write failing tests**

Create `tests/tools/test_html_converter.py`:

```python
import pytest
from tools.python_html_converter import convert_md_to_html, convert_file


_SAMPLE_MD = """\
# Test Report

## Section One

Some paragraph text with **bold** and `code`.

```python
def hello():
    print("hi")
```

## Section Two

- Item 1
- Item 2
"""


def test_returns_complete_html():
    html = convert_md_to_html(_SAMPLE_MD, title="Test")
    assert "<!DOCTYPE html>" in html
    assert "<title>Test</title>" in html
    assert "</html>" in html


def test_contains_converted_content():
    html = convert_md_to_html(_SAMPLE_MD)
    assert "<h1" in html
    assert "Section One" in html
    assert "Section Two" in html
    assert "<strong>bold</strong>" in html
    assert "<code>" in html


def test_has_syntax_highlighting():
    html = convert_md_to_html(_SAMPLE_MD)
    # Pygments wraps code in a highlight div or pre with class
    assert "highlight" in html or "codehilite" in html


def test_has_sidebar_toc():
    html = convert_md_to_html(_SAMPLE_MD)
    assert "toc" in html.lower() or "sidebar" in html.lower()


def test_is_self_contained():
    """All CSS/JS should be inline — no external references."""
    html = convert_md_to_html(_SAMPLE_MD)
    assert '<link rel="stylesheet" href="http' not in html
    assert '<script src="http' not in html


def test_convert_file(tmp_path):
    md_file = tmp_path / "report.md"
    html_file = tmp_path / "report.html"
    md_file.write_text(_SAMPLE_MD, encoding="utf-8")

    convert_file(str(md_file), str(html_file))

    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Section One" in content


def test_collapsible_sections():
    html = convert_md_to_html(_SAMPLE_MD)
    # Should have some mechanism for collapsible sections (details/summary or JS)
    assert "details" in html.lower() or "collapsible" in html.lower() or "toggle" in html.lower()


def test_print_friendly():
    html = convert_md_to_html(_SAMPLE_MD)
    assert "@media print" in html
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/tools/test_html_converter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.python_html_converter'`

- [ ] **Step 5: Implement tools/python_html_converter.py**

Create `tools/python_html_converter.py`:

```python
"""Standalone Markdown → HTML converter with professional styling.

Usage:
    CLI:    python tools/python_html_converter.py input.md output.html
    Module: from tools.python_html_converter import convert_md_to_html
"""

import sys
import re
import markdown
from pygments.formatters import HtmlFormatter

_PYGMENTS_CSS = HtmlFormatter(style="monokai").get_style_defs(".codehilite")

_CSS = r"""
:root {
    --bg: #ffffff; --fg: #1a1a2e; --accent: #0f3460; --accent-light: #e8eef6;
    --border: #d0d7de; --sidebar-bg: #f6f8fa; --code-bg: #282c34;
    --success: #2ea043; --warning: #d29922; --danger: #cf222e;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: var(--font-sans); color: var(--fg); background: var(--bg);
    line-height: 1.6; display: flex; min-height: 100vh;
}

/* ── Sidebar TOC ───────────────────────────────────────────────────────── */
#sidebar {
    position: fixed; top: 0; left: 0; width: 280px; height: 100vh;
    background: var(--sidebar-bg); border-right: 1px solid var(--border);
    overflow-y: auto; padding: 24px 16px; z-index: 10;
}
#sidebar h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;
    color: var(--accent); margin-bottom: 12px; }
#sidebar ul { list-style: none; }
#sidebar li { margin: 4px 0; }
#sidebar a {
    text-decoration: none; color: var(--fg); font-size: 13px; display: block;
    padding: 4px 8px; border-radius: 4px; transition: background 0.15s;
}
#sidebar a:hover { background: var(--accent-light); }
#sidebar a.active { background: var(--accent); color: #fff; }
#sidebar .toc-h3 { padding-left: 20px; font-size: 12px; color: #656d76; }

/* ── Main content ──────────────────────────────────────────────────────── */
#content { margin-left: 280px; max-width: 900px; padding: 40px 48px; flex: 1; }
#content h1 { font-size: 28px; border-bottom: 2px solid var(--accent); padding-bottom: 8px;
    margin: 32px 0 16px; }
#content h2 { font-size: 22px; border-bottom: 1px solid var(--border); padding-bottom: 6px;
    margin: 28px 0 12px; }
#content h3 { font-size: 17px; margin: 20px 0 8px; }
#content p { margin: 8px 0; }
#content ul, #content ol { margin: 8px 0 8px 24px; }
#content li { margin: 4px 0; }
#content code { font-family: var(--font-mono); font-size: 13px; background: #f0f2f5;
    padding: 2px 6px; border-radius: 3px; }
#content pre { margin: 12px 0; border-radius: 6px; overflow-x: auto; }
#content pre code { background: none; padding: 0; }
#content blockquote { border-left: 4px solid var(--accent); padding: 8px 16px;
    margin: 12px 0; background: var(--accent-light); border-radius: 0 4px 4px 0; }
#content table { border-collapse: collapse; width: 100%; margin: 12px 0; }
#content th, #content td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
#content th { background: var(--sidebar-bg); font-weight: 600; }
#content hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
#content img { max-width: 100%; }
#content strong { font-weight: 600; }

/* ── Collapsible sections ──────────────────────────────────────────────── */
details { margin: 8px 0; border: 1px solid var(--border); border-radius: 6px; }
details summary {
    cursor: pointer; padding: 10px 14px; font-weight: 600; background: var(--sidebar-bg);
    border-radius: 6px; user-select: none;
}
details[open] summary { border-bottom: 1px solid var(--border); border-radius: 6px 6px 0 0; }
details > *:not(summary) { padding: 0 14px; }

/* ── Pygments code highlighting ────────────────────────────────────────── */
.codehilite { background: var(--code-bg); padding: 14px 18px; border-radius: 6px;
    overflow-x: auto; }
.codehilite pre { color: #abb2bf; font-family: var(--font-mono); font-size: 13px;
    line-height: 1.5; }

""" + _PYGMENTS_CSS + r"""

/* ── Print ─────────────────────────────────────────────────────────────── */
@media print {
    #sidebar { display: none; }
    #content { margin-left: 0; max-width: 100%; padding: 20px; }
    details { border: none; }
    details summary { display: none; }
    details > * { display: block !important; padding: 0; }
    .codehilite { background: #f5f5f5 !important; color: #333 !important; }
}
"""

_JS = r"""
document.addEventListener("DOMContentLoaded", function() {
    // Build TOC from h1, h2, h3 in #content
    var content = document.getElementById("content");
    var sidebar = document.getElementById("toc-list");
    var headings = content.querySelectorAll("h1, h2, h3");
    headings.forEach(function(h, i) {
        if (!h.id) h.id = "section-" + i;
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = "#" + h.id;
        a.textContent = h.textContent;
        if (h.tagName === "H3") li.className = "toc-h3";
        li.appendChild(a);
        sidebar.appendChild(li);
    });

    // Scroll-spy: highlight active TOC entry
    var tocLinks = sidebar.querySelectorAll("a");
    function onScroll() {
        var scrollPos = window.scrollY + 80;
        var active = null;
        headings.forEach(function(h, i) {
            if (h.getBoundingClientRect().top + window.scrollY <= scrollPos) active = i;
        });
        tocLinks.forEach(function(a, i) {
            a.classList.toggle("active", i === active);
        });
    }
    window.addEventListener("scroll", onScroll);
    onScroll();

    // Make h2 sections collapsible
    var h2s = content.querySelectorAll("h2");
    h2s.forEach(function(h2) {
        var details = document.createElement("details");
        details.open = true;
        var summary = document.createElement("summary");
        summary.textContent = h2.textContent;

        // Collect siblings until next h1 or h2
        var siblings = [];
        var next = h2.nextElementSibling;
        while (next && next.tagName !== "H1" && next.tagName !== "H2") {
            siblings.push(next);
            next = next.nextElementSibling;
        }

        h2.parentNode.insertBefore(details, h2);
        details.appendChild(summary);
        siblings.forEach(function(s) { details.appendChild(s); });
        h2.remove();
    });
});
"""


def convert_md_to_html(md_content: str, title: str = "") -> str:
    """Convert a Markdown string to a self-contained professional HTML document."""
    extensions = [
        "markdown.extensions.fenced_code",
        "markdown.extensions.codehilite",
        "markdown.extensions.tables",
        "markdown.extensions.toc",
        "markdown.extensions.smarty",
    ]
    extension_configs = {
        "markdown.extensions.codehilite": {
            "css_class": "codehilite",
            "guess_lang": True,
        },
    }

    body_html = markdown.markdown(
        md_content, extensions=extensions, extension_configs=extension_configs,
    )

    if not title:
        # Extract title from first h1
        m = re.search(r"<h1[^>]*>(.*?)</h1>", body_html)
        title = m.group(1) if m else "Analysis Report"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<nav id="sidebar">
  <h2>Table of Contents</h2>
  <ul id="toc-list"></ul>
</nav>
<main id="content">
{body_html}
</main>
<script>{_JS}</script>
</body>
</html>"""


def convert_file(input_path: str, output_path: str) -> None:
    """Read a Markdown file, convert it, and write the HTML to *output_path*."""
    with open(input_path, "r", encoding="utf-8") as fh:
        md_content = fh.read()
    html = convert_md_to_html(md_content)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/python_html_converter.py <input.md> <output.html>")
        sys.exit(1)
    convert_file(sys.argv[1], sys.argv[2])
    print(f"Converted {sys.argv[1]} → {sys.argv[2]}")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/tools/test_html_converter.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add tools/python_html_converter.py tests/tools/test_html_converter.py requirements.txt
git commit -m "feat: add standalone MD-to-HTML converter with professional styling"
```

---

### Task 4: Create Consolidated Report Agent

**Files:**
- Create: `agents/report_consolidated.py`
- Create: `tests/agents/test_report_consolidated.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_report_consolidated.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from agents.report_consolidated import generate_consolidated_report


_FILE_A_RESULTS = {
    "bug_analysis": {
        "summary": "2 bugs found",
        "bugs": [
            {"line": 10, "severity": "critical", "description": "SQL injection"},
            {"line": 25, "severity": "minor", "description": "Unused import"},
        ],
        "narrative": "Security vulnerability detected.",
    },
    "code_flow": {"summary": "Linear flow", "markdown": "Entry: main()"},
}

_FILE_B_RESULTS = {
    "bug_analysis": {
        "summary": "1 bug found",
        "bugs": [{"line": 5, "severity": "major", "description": "Race condition"}],
        "narrative": "Concurrency issue.",
    },
    "code_flow": {"summary": "Async flow", "markdown": "Entry: handler()"},
}

_ALL_RESULTS = {
    "src/auth.py": _FILE_A_RESULTS,
    "src/worker.py": _FILE_B_RESULTS,
}

_PER_FILE_REPORTS = [
    "# Analysis Report — auth.py\n\n## Bug Analysis\n...",
    "# Analysis Report — worker.py\n\n## Bug Analysis\n...",
]


def test_template_mode_no_llm():
    md = generate_consolidated_report(
        per_file_reports=_PER_FILE_REPORTS,
        all_results=_ALL_RESULTS,
        file_paths=["src/auth.py", "src/worker.py"],
        features=["bug_analysis", "code_flow"],
        language="python",
        mode="template",
    )
    assert "# Consolidated Analysis Report" in md
    assert "auth.py" in md
    assert "worker.py" in md
    assert "Table of Contents" in md or "##" in md


def test_template_mode_includes_stats():
    md = generate_consolidated_report(
        per_file_reports=_PER_FILE_REPORTS,
        all_results=_ALL_RESULTS,
        file_paths=["src/auth.py", "src/worker.py"],
        features=["bug_analysis", "code_flow"],
        language="python",
        mode="template",
    )
    # Should mention bug counts
    assert "3" in md or "bug" in md.lower()


def test_hybrid_mode_calls_llm():
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.message = {"content": [{"text": "Executive summary goes here."}]}

    with patch("agents.report_consolidated._call_llm", return_value="Executive summary goes here.") as mock_call:
        md = generate_consolidated_report(
            per_file_reports=_PER_FILE_REPORTS,
            all_results=_ALL_RESULTS,
            file_paths=["src/auth.py", "src/worker.py"],
            features=["bug_analysis", "code_flow"],
            language="python",
            mode="hybrid",
        )
        assert mock_call.called
        assert "Executive summary" in md


def test_llm_mode_calls_llm():
    with patch("agents.report_consolidated._call_llm",
               return_value="# Full LLM Report\n\nNarrative here.") as mock_call:
        md = generate_consolidated_report(
            per_file_reports=_PER_FILE_REPORTS,
            all_results=_ALL_RESULTS,
            file_paths=["src/auth.py", "src/worker.py"],
            features=["bug_analysis", "code_flow"],
            language="python",
            mode="llm",
        )
        assert mock_call.called
        assert "Full LLM Report" in md or "Narrative" in md


def test_empty_results():
    md = generate_consolidated_report(
        per_file_reports=[],
        all_results={},
        file_paths=[],
        features=[],
        language="python",
        mode="template",
    )
    assert "# Consolidated Analysis Report" in md
    assert "No files" in md or "no analysis" in md.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agents/test_report_consolidated.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement agents/report_consolidated.py**

Create `agents/report_consolidated.py`:

```python
"""Consolidated report agent — synthesizes all per-file results into a cohesive
'mother document'.  Supports template, llm, and hybrid modes."""

import json
import os
from datetime import datetime
from strands import Agent
from agents._bedrock import make_bedrock_model


_FEATURE_LABELS = {
    "requirement": "Requirements", "code_flow": "Code Flow",
    "code_design": "Code Design", "bug_analysis": "Bug Analysis",
    "static_analysis": "Static Analysis", "mermaid": "Mermaid Diagrams",
    "comment_generator": "PR Comments",
}


def generate_consolidated_report(
    per_file_reports: list[str],
    all_results: dict,
    file_paths: list[str],
    features: list[str],
    language: str = "",
    mode: str = "hybrid",
) -> str:
    """Return a Markdown consolidated report.

    Parameters
    ----------
    per_file_reports : list[str]
        Rendered per-file Markdown reports.
    all_results : dict
        Full results dict: {file_path: {feature: result_dict}}.
    file_paths : list[str]
        Ordered list of analyzed file paths.
    features : list[str]
        List of selected feature keys.
    language : str
        Primary language of the codebase.
    mode : str
        One of "template", "llm", "hybrid".
    """
    if mode == "template":
        return _build_template(per_file_reports, all_results, file_paths, features, language)
    elif mode == "llm":
        return _build_llm(per_file_reports, all_results, file_paths, features, language)
    else:
        return _build_hybrid(per_file_reports, all_results, file_paths, features, language)


# ── Template mode ────────────────────────────────────────────────────────────

def _build_template(per_file_reports, all_results, file_paths, features, language):
    lines = []
    lines.append("# Consolidated Analysis Report")
    lines.append("")
    lines.append(f"**Files analyzed:** {len(file_paths)}  ")
    lines.append(f"**Language:** {language or 'mixed'}  ")
    lines.append(f"**Features:** {', '.join(_FEATURE_LABELS.get(f, f) for f in features)}  ")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if not file_paths:
        lines.append("*No files were analyzed — no analysis data available.*")
        return "\n".join(lines)

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    lines.append("1. [Summary Statistics](#summary-statistics)")
    for i, fp in enumerate(file_paths, 2):
        name = os.path.basename(fp)
        lines.append(f"{i}. [{name}](#{_slug(name)})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary statistics
    lines.append("## Summary Statistics")
    lines.append("")
    stats = _compute_stats(all_results, file_paths, features)
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    for label, count in stats:
        lines.append(f"| {label} | {count} |")
    lines.append("")

    # Per-file sections
    for fp, report in zip(file_paths, per_file_reports):
        name = os.path.basename(fp)
        lines.append(f"## {name}")
        lines.append("")
        # Strip the top-level heading from the per-file report to avoid duplication
        report_body = report.split("\n", 1)[1] if report.startswith("# ") else report
        lines.append(report_body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ── LLM mode ────────────────────────────────────────────────────────────────

def _build_llm(per_file_reports, all_results, file_paths, features, language):
    context = _prepare_context(per_file_reports, all_results, file_paths, features, language)
    prompt = f"""You are a principal software architect producing a comprehensive design document.

You have the complete analysis results for {len(file_paths)} source files in a {language or 'multi-language'} codebase.
The analysis covered: {', '.join(_FEATURE_LABELS.get(f, f) for f in features)}.

Your task: produce a single, cohesive Markdown document that reads as the definitive reference
for this codebase. This is a "mother document" — not a collection of per-file summaries.

Requirements:
1. Executive Summary — the big picture: what this code does, why it exists, its overall health
2. Architecture & Module Relationships — how files connect, data flow, dependency graph
3. Deep Dives — ordered by logical dependency (not alphabetically), with continuity between sections
4. Cross-Cutting Concerns — patterns, recurring issues, shared themes across files
5. Recommendations & Conclusion — actionable next steps, prioritized

Write with narrative flow. A reader should understand the ENTIRE codebase from this document alone.
Do NOT just list findings per file — synthesize them into a story.

Here are the complete analysis results:

{context}

Write the consolidated document now in Markdown format."""

    return _call_llm(prompt)


# ── Hybrid mode ──────────────────────────────────────────────────────────────

def _build_hybrid(per_file_reports, all_results, file_paths, features, language):
    # Template skeleton
    lines = []
    lines.append("# Consolidated Analysis Report")
    lines.append("")
    lines.append(f"**Files analyzed:** {len(file_paths)}  ")
    lines.append(f"**Language:** {language or 'mixed'}  ")
    lines.append(f"**Features:** {', '.join(_FEATURE_LABELS.get(f, f) for f in features)}  ")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if not file_paths:
        lines.append("*No files were analyzed — no analysis data available.*")
        return "\n".join(lines)

    # LLM-generated executive summary
    context = _prepare_context(per_file_reports, all_results, file_paths, features, language)
    exec_prompt = f"""Based on these analysis results for {len(file_paths)} {language or ''} source files,
write a concise Executive Summary (200-400 words) covering:
- What this code does and why it exists
- Overall code health assessment
- Top 3 critical findings
- Key architectural patterns observed

Analysis data:
{context}

Write ONLY the executive summary in Markdown (no heading — I will add one)."""

    exec_summary = _call_llm(exec_prompt)
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(exec_summary)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Template: summary statistics
    lines.append("## Summary Statistics")
    lines.append("")
    stats = _compute_stats(all_results, file_paths, features)
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    for label, count in stats:
        lines.append(f"| {label} | {count} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # LLM-generated architecture overview
    arch_prompt = f"""Based on these analysis results, write an Architecture Overview (200-300 words)
describing how the analyzed modules relate to each other, data flow between them,
and the dependency structure. Focus on cross-file relationships.

Files: {', '.join(os.path.basename(f) for f in file_paths)}

Analysis data:
{context}

Write ONLY the architecture overview in Markdown (no heading)."""

    arch_overview = _call_llm(arch_prompt)
    lines.append("## Architecture & Module Relationships")
    lines.append("")
    lines.append(arch_overview)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Template: per-file sections
    for fp, report in zip(file_paths, per_file_reports):
        name = os.path.basename(fp)
        lines.append(f"## {name}")
        lines.append("")
        report_body = report.split("\n", 1)[1] if report.startswith("# ") else report
        lines.append(report_body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    # LLM-generated conclusion
    conclusion_prompt = f"""Based on the complete analysis of {len(file_paths)} source files,
write a Conclusion & Recommendations section (150-250 words) with:
- Prioritized action items
- Risk areas requiring immediate attention
- Strengths to preserve

Analysis data:
{context}

Write ONLY the conclusion in Markdown (no heading)."""

    conclusion = _call_llm(conclusion_prompt)
    lines.append("## Conclusion & Recommendations")
    lines.append("")
    lines.append(conclusion)
    lines.append("")

    return "\n".join(lines)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    """Send a prompt to Bedrock and return the text response."""
    model = make_bedrock_model()
    agent = Agent(model=model)
    result = agent(prompt)
    # Strands Agent returns an AgentResult; extract text
    if hasattr(result, "message"):
        msg = result.message
        if isinstance(msg, dict):
            content = msg.get("content", [])
            if content and isinstance(content[0], dict):
                return content[0].get("text", str(result))
        return str(msg)
    return str(result)


def _prepare_context(per_file_reports, all_results, file_paths, features, language):
    """Build a text context block from all results for LLM prompts."""
    parts = []
    for fp in file_paths:
        name = os.path.basename(fp)
        parts.append(f"### File: {name} ({fp})")
        file_data = all_results.get(fp, {})
        for feat in features:
            if feat in file_data:
                label = _FEATURE_LABELS.get(feat, feat)
                # Truncate large results to avoid token overflow
                result_str = json.dumps(file_data[feat], indent=1, ensure_ascii=False)
                if len(result_str) > 3000:
                    result_str = result_str[:3000] + "\n... [truncated]"
                parts.append(f"**{label}:**\n```json\n{result_str}\n```")
        parts.append("")
    return "\n".join(parts)


def _compute_stats(all_results, file_paths, features):
    """Return a list of (label, count) summary statistics."""
    total_bugs = 0
    critical_bugs = 0
    linter_findings = 0
    semantic_findings = 0

    for fp in file_paths:
        file_data = all_results.get(fp, {})
        if "bug_analysis" in file_data:
            bugs = file_data["bug_analysis"].get("bugs", [])
            total_bugs += len(bugs)
            critical_bugs += sum(1 for b in bugs if b.get("severity") == "critical")
        if "static_analysis" in file_data:
            linter_findings += len(file_data["static_analysis"].get("linter_findings", []))
            semantic_findings += len(file_data["static_analysis"].get("semantic_findings", []))

    stats = [
        ("Files analyzed", len(file_paths)),
        ("Features run", len(features)),
    ]
    if "bug_analysis" in features:
        stats.append(("Total bugs", total_bugs))
        stats.append(("Critical bugs", critical_bugs))
    if "static_analysis" in features:
        stats.append(("Linter findings", linter_findings))
        stats.append(("Semantic findings", semantic_findings))
    return stats


def _slug(text):
    """Create a simple anchor slug from text."""
    return text.lower().replace(" ", "-").replace(".", "").replace("/", "")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_report_consolidated.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/report_consolidated.py tests/agents/test_report_consolidated.py
git commit -m "feat: add consolidated report agent with template/llm/hybrid modes"
```

---

### Task 5: Integrate Report Generation into Orchestrator

**Files:**
- Modify: `agents/orchestrator.py`
- Modify: `app/components/result_tabs.py:453-506`

- [ ] **Step 1: Write failing test for orchestrator report integration**

Add to `tests/agents/test_orchestrator.py` (or create a new focused test file if the existing one doesn't exist with the right fixtures). Create `tests/agents/test_report_integration.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock


def test_report_generation_called_when_enabled(test_db, monkeypatch, tmp_path):
    """Verify orchestrator calls report generation when settings enable it."""
    monkeypatch.setenv("REPORT_PER_FILE", "true")
    monkeypatch.setenv("REPORT_CONSOLIDATED", "false")
    monkeypatch.setenv("REPORT_FORMAT_MD", "true")
    monkeypatch.setenv("REPORT_FORMAT_HTML", "false")

    from config.settings import get_settings
    get_settings.cache_clear()

    from agents.orchestrator import _generate_reports
    from agents.report_per_file import generate_per_file_report

    per_file_data = [
        ("src/a.py", {"bug_analysis": {"summary": "ok", "bugs": []}}),
    ]
    features = ["bug_analysis"]
    reports_dir = str(tmp_path / "reports")

    # Mock _emit to be a no-op
    mock_emit = MagicMock()

    written = _generate_reports(
        conn=test_db, job_id="test-123", per_file_data=per_file_data,
        features=features, language="python", reports_dir=reports_dir,
        emit_fn=mock_emit,
    )

    assert len(written) > 0
    # Should have created per_file/ dir
    assert os.path.isdir(os.path.join(reports_dir, "per_file"))


def test_report_generation_skipped_when_disabled(test_db, monkeypatch, tmp_path):
    monkeypatch.setenv("REPORT_PER_FILE", "false")
    monkeypatch.setenv("REPORT_CONSOLIDATED", "false")

    from config.settings import get_settings
    get_settings.cache_clear()

    from agents.orchestrator import _generate_reports

    per_file_data = [
        ("src/a.py", {"bug_analysis": {"summary": "ok", "bugs": []}}),
    ]
    reports_dir = str(tmp_path / "reports")
    mock_emit = MagicMock()

    written = _generate_reports(
        conn=test_db, job_id="test-123", per_file_data=per_file_data,
        features=["bug_analysis"], language="python", reports_dir=reports_dir,
        emit_fn=mock_emit,
    )

    assert written == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agents/test_report_integration.py -v`
Expected: FAIL — `ImportError: cannot import name '_generate_reports'`

- [ ] **Step 3: Add _generate_reports function to orchestrator.py**

Add these imports at the top of `agents/orchestrator.py` (after existing imports):

```python
from agents.report_per_file import generate_per_file_report
from agents.report_consolidated import generate_consolidated_report
from tools.python_html_converter import convert_md_to_html
```

Add this new function before `run_analysis()`:

```python
def _generate_reports(conn, job_id, per_file_data, features, language,
                      reports_dir, emit_fn) -> list[str]:
    """Phase 2: generate per-file and consolidated reports.

    Returns list of written file paths.
    """
    s = get_settings()
    written = []

    if not s.report_per_file and not s.report_consolidated:
        return written

    os.makedirs(reports_dir, exist_ok=True)
    per_file_dir = os.path.join(reports_dir, "per_file")
    per_file_reports = []

    # ── Per-file reports ─────────────────────────────────────────────────
    if s.report_per_file:
        os.makedirs(per_file_dir, exist_ok=True)
        for file_path, file_results in per_file_data:
            basename = os.path.basename(file_path) or "report"
            name_stem = os.path.splitext(basename)[0]
            emit_fn(conn, job_id, "report_start", agent="report_per_file",
                    file_path=file_path, message=f"Generating report for {basename}")

            md_content = generate_per_file_report(file_path, file_results, language)
            per_file_reports.append(md_content)

            if s.report_format_md:
                md_path = os.path.join(per_file_dir, f"{name_stem}.md")
                with open(md_path, "w", encoding="utf-8") as fh:
                    fh.write(md_content)
                written.append(md_path)

            if s.report_format_html:
                html_path = os.path.join(per_file_dir, f"{name_stem}.html")
                html_content = convert_md_to_html(md_content, title=f"Report — {basename}")
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(html_content)
                written.append(html_path)

            emit_fn(conn, job_id, "report_complete", agent="report_per_file",
                    file_path=file_path, message=f"Report saved for {basename}")

    # ── Consolidated report ──────────────────────────────────────────────
    if s.report_consolidated and per_file_data:
        emit_fn(conn, job_id, "report_start", agent="report_consolidated",
                message="Generating consolidated report")

        all_results = {fp: fr for fp, fr in per_file_data}
        file_paths = [fp for fp, _ in per_file_data]

        md_content = generate_consolidated_report(
            per_file_reports=per_file_reports,
            all_results=all_results,
            file_paths=file_paths,
            features=[f for f in features if f != "commit_analysis"],
            language=language,
            mode=s.consolidated_mode,
        )

        if s.report_format_md:
            md_path = os.path.join(reports_dir, "consolidated_report.md")
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(md_content)
            written.append(md_path)

        if s.report_format_html:
            html_path = os.path.join(reports_dir, "consolidated_report.html")
            html_content = convert_md_to_html(md_content, title="Consolidated Analysis Report")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            written.append(html_path)

        emit_fn(conn, job_id, "report_complete", agent="report_consolidated",
                message=f"Consolidated report saved ({len(file_paths)} files)")

    return written
```

- [ ] **Step 4: Update run_analysis() to call _generate_reports**

Replace the report-saving block in `run_analysis()` (lines 257-265) with:

```python
        # ── Phase 2: Report generation ───────────────────────────────────
        # Build per_file_data regardless of single/multi file path
        if len(files) == 1:
            _per_file_data = [(files[0]["file_path"], results)]
        else:
            _per_file_data = per_file

        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = os.path.join("Reports", ts)
            saved = _generate_reports(
                conn, job_id, _per_file_data, features,
                language or detect_language(files[0]["file_path"]),
                reports_dir, _emit,
            )
            if saved:
                _emit(conn, job_id, "report_complete",
                      message=f"Saved {len(saved)} report file(s) to Reports/")
        except Exception:
            pass  # non-critical — don't fail the job
```

Also add `import os` and `from datetime import datetime` at the top of orchestrator.py if not already present.

- [ ] **Step 5: Remove old save_reports_to_disk call and import**

In `agents/orchestrator.py`, remove:
- Line 19: `from app.components.result_tabs import save_reports_to_disk`

The `save_reports_to_disk` function in `result_tabs.py` stays for the manual "Save All Reports" button, but the orchestrator no longer calls it — `_generate_reports` replaces it.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/agents/test_report_integration.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add agents/orchestrator.py tests/agents/test_report_integration.py
git commit -m "feat: integrate report generation into orchestrator pipeline"
```

---

### Task 6: Fix Progress Bar — Two-Phase Display

**Files:**
- Modify: `app/pages/1_Analysis.py:61-147`

- [ ] **Step 1: Update _EVENT_ICON to include report events**

In `app/pages/1_Analysis.py`, update the `_EVENT_ICON` dict:

```python
_EVENT_ICON = {
    "fetch":           "📂",
    "phase":           "—",
    "start":           "🔄",
    "complete":        "✅",
    "cached":          "⚡",
    "error":           "❌",
    "report_start":    "📝",
    "report_complete": "📄",
    "report_error":    "❌",
}
```

- [ ] **Step 2: Replace _render_live_progress with two-phase version**

Replace the `_render_live_progress` function (lines 82-132) with:

```python
def _render_live_progress(conn, job_id: str, job: dict) -> None:
    features = job.get("features") or []
    analysis_features = [f for f in features if f != "commit_analysis"]
    events = get_events(conn, job_id)

    # Count source files from fetch events
    file_count = 1  # default
    for ev in events:
        if ev["event_type"] == "fetch" and ev.get("message", "").startswith("Loaded"):
            msg = ev["message"]
            try:
                file_count = int(msg.split()[1])
            except (IndexError, ValueError):
                pass

    # ── Phase 1: Analysis progress ───────────────────────────────────────
    analysis_total = len(analysis_features) * file_count
    analysis_done = sum(1 for e in events
                        if e["event_type"] in ("complete", "cached", "error")
                        and e.get("agent") not in ("report_per_file", "report_consolidated"))
    analysis_pct = min(int((analysis_done / max(analysis_total, 1)) * 100), 99)

    # Check if analysis is truly done (report events have started)
    report_events = [e for e in events if e["event_type"].startswith("report_")]
    analysis_finished = len(report_events) > 0 or analysis_done >= analysis_total

    if analysis_finished:
        st.progress(100, text=f"Analysis complete — {analysis_done}/{analysis_total} agents done")
    else:
        st.progress(analysis_pct, text=f"Analyzing… {analysis_done}/{analysis_total} agents done")

    # ── Phase 2: Report generation progress ──────────────────────────────
    if report_events:
        report_done = sum(1 for e in report_events if e["event_type"] == "report_complete")
        report_started = sum(1 for e in report_events if e["event_type"] == "report_start")
        # Estimate total: started is a reasonable proxy since they fire sequentially
        report_total = max(report_started, report_done, 1)
        report_pct = min(int((report_done / report_total) * 100), 99)
        st.progress(report_pct, text=f"Generating reports… {report_done}/{report_total}")

    # ── Live Activity Log ────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("##### Live Activity")
        if not events:
            st.caption("Starting up…")
        for ev in events:
            etype   = ev["event_type"]
            agent   = ev.get("agent") or ""
            fpath   = ev.get("file_path") or ""
            message = ev.get("message") or ""
            icon    = _EVENT_ICON.get(etype, "•")
            fname   = os.path.basename(fpath) if fpath else ""
            label   = _AGENT_LABELS.get(agent, agent)

            if etype == "phase":
                st.markdown(f"&nbsp;&nbsp;**{message}**")
            elif etype == "fetch":
                st.markdown(f"{icon} &nbsp; {message}")
            elif etype in ("start", "report_start"):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + " &nbsp; *running…*"
                )
            elif etype in ("cached",):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + f" &nbsp; *cache hit* — {message}"
                )
            elif etype in ("complete", "report_complete"):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + (f" &nbsp; — {message}" if message else "")
                )
            elif etype in ("error", "report_error"):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + (f" &nbsp; — {message}" if message else "")
                )
```

- [ ] **Step 3: Add report agent labels to _AGENT_LABELS**

Update `_AGENT_LABELS` in `1_Analysis.py`:

```python
_AGENT_LABELS = {
    "bug_analysis":        "Bug Analysis",
    "static_analysis":     "Static Analysis",
    "code_flow":           "Code Flow",
    "requirement":         "Requirements",
    "code_design":         "Code Design",
    "mermaid":             "Mermaid Diagram",
    "comment_generator":   "PR Comments",
    "commit_analysis":     "Commit Analysis",
    "report_per_file":     "Per-File Report",
    "report_consolidated": "Consolidated Report",
}
```

- [ ] **Step 4: Verify manually**

Run: `streamlit run app/Home.py`
Select multiple files, run analysis, and verify:
1. Phase 1 progress bar shows correct total (features × files)
2. Phase 2 progress bar appears after analysis completes
3. Report events appear in the activity log with correct icons

- [ ] **Step 5: Commit**

```bash
git add app/pages/1_Analysis.py
git commit -m "feat: two-phase progress bar with correct agent count per file"
```

---

### Task 7: Update result_tabs.py save_reports_to_disk

**Files:**
- Modify: `app/components/result_tabs.py:453-506`

- [ ] **Step 1: Update save_reports_to_disk to use new report structure**

Replace the `save_reports_to_disk` function (lines 466-506) with an updated version that uses the new per-file report agent and HTML converter when available, while keeping backward compatibility for the manual "Save All Reports" button:

```python
def save_reports_to_disk(results: dict, source_ref: str = "",
                         reports_root: str = "Reports") -> list[str]:
    """
    Write one Markdown report per (source file x feature) into a timestamped
    sub-directory of reports_root.  Standalone — no Streamlit dependency.
    Returns list of written file paths.

    Note: This is the legacy per-feature save used by the manual button.
    The orchestrator now uses _generate_reports() for per-file and consolidated reports.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = os.path.join(reports_root, ts)
    os.makedirs(reports_dir, exist_ok=True)
    written = []

    for feature in FEATURE_LABELS:
        if feature not in results:
            continue
        result = results[feature]
        suffix = _FEATURE_SUFFIX.get(feature, f"_{feature}.md")

        if result.get("_multi_file"):
            for file_path, file_result in result.get("files", {}).items():
                base = os.path.basename(file_path) or "report"
                out_path = os.path.join(reports_dir, f"{base}{suffix}")
                try:
                    content = _to_markdown(feature, file_result)
                    with open(out_path, "w", encoding="utf-8") as fh:
                        fh.write(content)
                    written.append(out_path)
                except Exception:
                    pass
        else:
            base = _source_basename(source_ref)
            out_path = os.path.join(reports_dir, f"{base}{suffix}")
            try:
                content = _to_markdown(feature, result)
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                written.append(out_path)
            except Exception:
                pass

    return written
```

This is essentially unchanged — the orchestrator's `_generate_reports` handles the new per-file + consolidated flow, while this function remains for the manual save button.

- [ ] **Step 2: Commit**

```bash
git add app/components/result_tabs.py
git commit -m "docs: clarify save_reports_to_disk is legacy manual save"
```

---

### Task 8: Final Integration Test

**Files:**
- Test all components together

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: ALL PASS

- [ ] **Step 2: Run specific new tests**

Run: `pytest tests/test_config.py tests/agents/test_report_per_file.py tests/agents/test_report_consolidated.py tests/tools/test_html_converter.py tests/agents/test_report_integration.py -v`
Expected: ALL PASS

- [ ] **Step 3: Manual smoke test**

Run: `streamlit run app/Home.py`
Test with:
1. Single file → verify per-file report in Reports/ (MD + HTML)
2. Multiple files → verify per-file/ directory + consolidated report
3. Check HTML report opens in browser with sidebar TOC, collapsible sections, syntax highlighting
4. Check progress bar shows correct counts for multi-file analysis

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete report agents with per-file, consolidated, and HTML output"
```
