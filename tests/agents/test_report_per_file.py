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
