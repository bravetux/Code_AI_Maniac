from tools.run_linter import run_linter


def test_run_linter_python_clean(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\nprint(x)\n")
    result = run_linter(str(f), language="Python")
    assert "findings" in result
    assert isinstance(result["findings"], list)


def test_run_linter_python_with_issue(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("import os\nx=1\n")  # unused import, spacing issue
    result = run_linter(str(f), language="Python")
    assert "findings" in result


def test_run_linter_unknown_language(tmp_path):
    f = tmp_path / "file.cobol"
    f.write_text("IDENTIFICATION DIVISION.\n")
    result = run_linter(str(f), language="COBOL")
    assert result["findings"] == []
    assert result["skipped"] is True
