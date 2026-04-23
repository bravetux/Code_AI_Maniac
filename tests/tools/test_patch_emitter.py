import json
import os
from tools.patch_emitter import emit


def test_new_file_mode_writes_content_and_empty_diff(tmp_path):
    result = emit(
        agent_key="sql_generator",
        reports_root=str(tmp_path),
        file_path="query.sql",
        new_content="SELECT 1;",
        description="Simple select",
    )
    content_path = tmp_path / "sql_generator" / "patches" / "query.sql"
    diff_path = tmp_path / "sql_generator" / "patches" / "query.sql.diff"
    assert content_path.exists()
    assert content_path.read_text(encoding="utf-8") == "SELECT 1;"
    assert diff_path.exists()
    # New file: diff contains only added lines
    assert "+SELECT 1;" in diff_path.read_text(encoding="utf-8")
    # pr_comment.md + summary.json created
    assert (tmp_path / "sql_generator" / "pr_comment.md").exists()
    assert (tmp_path / "sql_generator" / "summary.json").exists()
    # Return shape
    assert result["applied"] is True
    assert result["paths"]["content"] == str(content_path)
    assert result["paths"]["diff"] == str(diff_path)


def test_diff_mode_validates_base_content_reverse_apply(tmp_path):
    base = "line 1\nline 2\nline 3\n"
    diff_text = (
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,3 +1,3 @@\n"
        " line 1\n"
        "-line 2\n"
        "+line TWO\n"
        " line 3\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo.py",
        base_content=base,
        diff=diff_text,
        description="fix line 2",
    )
    assert result["applied"] is True
    content = (tmp_path / "auto_fix" / "patches" / "foo.py").read_text(encoding="utf-8")
    assert "line TWO" in content


def test_base_plus_new_computes_unified_diff(tmp_path):
    base = "a\nb\nc\n"
    new = "a\nB\nc\n"
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="x.txt",
        base_content=base,
        new_content=new,
        description="b -> B",
    )
    diff = (tmp_path / "auto_fix" / "patches" / "x.txt.diff").read_text(encoding="utf-8")
    assert "-b" in diff
    assert "+B" in diff
    assert result["applied"] is True


def test_invalid_diff_reverse_apply_fails_gracefully(tmp_path):
    base = "actual content\n"
    bad_diff = (
        "--- a/foo\n"
        "+++ b/foo\n"
        "@@ -1 +1 @@\n"
        "-wrong base\n"
        "+new content\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo",
        base_content=base,
        diff=bad_diff,
        description="bad diff",
    )
    assert result["applied"] is False
    # Raw diff still written for manual review
    assert (tmp_path / "auto_fix" / "patches" / "foo.diff").exists()


def test_multi_call_merges_pr_comment_and_summary(tmp_path):
    emit(agent_key="sonar_fix", reports_root=str(tmp_path),
         file_path="a.py", new_content="print('a')\n", description="first")
    emit(agent_key="sonar_fix", reports_root=str(tmp_path),
         file_path="b.py", new_content="print('b')\n", description="second",
         summary_extras={"issues_fixed": ["S100"]})
    pr = (tmp_path / "sonar_fix" / "pr_comment.md").read_text(encoding="utf-8")
    assert "a.py" in pr
    assert "b.py" in pr
    summary = json.loads((tmp_path / "sonar_fix" / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["files"]) == 2
    assert "S100" in summary.get("issues_fixed", [])


def test_requires_at_least_one_of_new_content_or_diff(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        emit(agent_key="x", reports_root=str(tmp_path), file_path="f.py")


def test_no_trailing_newline_preserved_when_base_has_none(tmp_path):
    """Bug 1 regression: files without trailing newline stay that way after patch."""
    base = "line 1\nline 2"  # NO trailing newline
    diff_text = (
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-line 1\n"
        "+line ONE\n"
        " line 2"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo.py",
        base_content=base,
        diff=diff_text,
        description="no-trailing-newline preserved",
    )
    content = (tmp_path / "auto_fix" / "patches" / "foo.py").read_text(encoding="utf-8")
    assert not content.endswith("\n"), (
        f"patched content gained a spurious trailing newline: {content!r}"
    )
    assert "line ONE" in content
    assert result["applied"] is True


def test_trailing_newline_preserved_when_base_has_one(tmp_path):
    """Complement: files WITH trailing newline still have one after patch."""
    base = "line 1\nline 2\n"  # WITH trailing newline
    diff_text = (
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-line 1\n"
        "+line ONE\n"
        " line 2\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo.py",
        base_content=base,
        diff=diff_text,
        description="trailing-newline preserved",
    )
    content = (tmp_path / "auto_fix" / "patches" / "foo.py").read_text(encoding="utf-8")
    assert content.endswith("\n")


def test_crlf_base_normalized_to_lf(tmp_path):
    """Bug 2 regression: CRLF base + LF diff should apply cleanly."""
    base = "line 1\r\nline 2\r\nline 3\r\n"  # Windows-style
    diff_text = (
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,3 +1,3 @@\n"
        " line 1\n"
        "-line 2\n"
        "+line TWO\n"
        " line 3\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo.py",
        base_content=base,
        diff=diff_text,
        description="CRLF base normalized",
    )
    assert result["applied"] is True
    content = (tmp_path / "auto_fix" / "patches" / "foo.py").read_text(encoding="utf-8")
    # Content is normalized to LF (acceptable - unified-diff convention)
    assert "line TWO" in content
    assert "\r" not in content  # LF-only output


def test_empty_base_hunk_header_zero_origin_is_safe(tmp_path):
    """Bug 3 regression: @@ -0,0 +1,N @@ style header doesn't index base[-1]."""
    # Simulate new-file creation via diff mode (unusual but valid)
    base = ""
    diff_text = (
        "--- a/new.py\n"
        "+++ b/new.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+line 1\n"
        "+line 2\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="new.py",
        base_content=base,
        diff=diff_text,
        description="new file via empty-base diff",
    )
    assert result["applied"] is True
    content = (tmp_path / "auto_fix" / "patches" / "new.py").read_text(encoding="utf-8")
    assert "line 1" in content
    assert "line 2" in content


def test_diff_with_bare_empty_context_line_applies_cleanly(tmp_path):
    """Regression: unified diffs with bare empty context lines (no leading ' ')
    should apply, matching git apply's tolerance."""
    base = "line 1\n\nline 3\n"  # blank line between 1 and 3
    # Note the bare empty line (not ' \n') between context lines
    diff_text = (
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,3 +1,3 @@\n"
        " line 1\n"
        "\n"                 # BARE empty line - blank context
        "-line 3\n"
        "+line THREE\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo.py",
        base_content=base,
        diff=diff_text,
        description="bare blank context",
    )
    assert result["applied"] is True
    content = (tmp_path / "auto_fix" / "patches" / "foo.py").read_text(encoding="utf-8")
    assert "line THREE" in content


def test_diff_with_no_newline_marker_is_tolerated(tmp_path):
    """Regression: '\\ No newline at end of file' markers should not trip validation."""
    base = "line 1\nline 2"  # no trailing newline
    diff_text = (
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        " line 1\n"
        "-line 2\n"
        "+line TWO\n"
        "\\ No newline at end of file\n"
    )
    result = emit(
        agent_key="auto_fix",
        reports_root=str(tmp_path),
        file_path="foo.py",
        base_content=base,
        diff=diff_text,
        description="no-newline marker",
    )
    assert result["applied"] is True
