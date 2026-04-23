from agents.traceability_matrix import run_traceability_matrix


def test_stub_returns_placeholder_markdown(test_db):
    # Now that F10 is filled, with empty story we get an error markdown.
    result = run_traceability_matrix(
        conn=test_db,
        job_id="test-job-1",
        file_path="story.txt",
        content="",
        file_hash="fakehash-no-story",
        language=None,
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Traceability" in result["markdown"] or "error" in result["summary"].lower()


def test_orchestrator_dispatches_traceability_matrix(test_db, tmp_path):
    from db.queries.jobs import create_job, get_job, get_job_results
    from db.queries.job_events import get_events
    from agents.orchestrator import run_analysis
    story = tmp_path / "story.txt"
    story.write_text("As a user I want to reset my password.", encoding="utf-8")
    job_id = create_job(test_db, source_type="local",
                        source_ref=str(story),
                        language=None,
                        features=["traceability_matrix"])
    run_analysis(test_db, job_id)
    job = get_job(test_db, job_id)
    assert job is not None
    assert job["status"] in ("completed", "failed"), f"unexpected status: {job['status']}"
    results = get_job_results(test_db, job_id) or {}
    events = get_events(test_db, job_id)
    assert len(events) > 0, "expected at least one job_events row for the dispatch"
    dispatch_trace = str(results) + " " + " ".join(str(e) for e in events)
    assert "traceability_matrix" in dispatch_trace, \
        f"dispatch did not produce a result for traceability_matrix: results={results!r} events={events!r}"


import json
from unittest.mock import patch, MagicMock
from agents.traceability_matrix import (
    _extract_acs_deterministic, _score_pair, _jaccard_match, _is_ambiguous,
    _STOP_WORDS, _strip_append_prefix,
)


def test_strip_append_prefix_handles_wrapped():
    from agents._bedrock import _APPEND_PREFIX
    wrapped = f"{_APPEND_PREFIX}__stories__\nACs"
    stripped = _strip_append_prefix(wrapped)
    assert stripped.startswith("__stories__")


def test_strip_append_prefix_leaves_unwrapped_alone():
    assert _strip_append_prefix("__stories__\nfoo") == "__stories__\nfoo"
    assert _strip_append_prefix(None) == ""


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
    assert by_id["AC-2"]["Status"] == "amber"
    assert by_id["AC-3"]["Status"] == "red"


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
    rows = list(_csv.DictReader(open(csv_path, "r", encoding="utf-8")))
    assert len(rows) == 2
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


def test_resolve_inputs_handles_append_prefix_wrap(tmp_path):
    from agents._bedrock import _APPEND_PREFIX
    tests_dir = tmp_path / "t"
    tests_dir.mkdir()
    prompt = (
        f"{_APPEND_PREFIX}__stories__\nAC-1: foo.\n"
        f"__tests_dir__={tests_dir}\n"
    )
    res = _resolve_inputs(file_path="ignored", content="", custom_prompt=prompt)
    assert "AC-1" in res["stories"]
    assert res["tests_dir"] == str(tests_dir)


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


import os as _os_lib


def _project_root():
    import pathlib
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


_CANNED_MATCH_BATCH = json.dumps({
    "matches": {
        "AC-3": [],
        "AC-4": ["test_unknown_email_returns_generic_200"],
    }
})


def test_full_run_writes_three_artifacts(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = _project_root()
    story = (root / "tests/fixtures/wave6a/reset_password_story.txt").read_text(encoding="utf-8")
    tests_dir = str(root / "tests/fixtures/wave6a/reset_password_tests")
    prefix = f"__stories__\n{story}\n__tests_dir__={tests_dir}"

    with patch("agents.traceability_matrix.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.side_effect = [_CANNED_MATCH_BATCH] * 5
        mock_cls.return_value = mock_agent
        result = run_traceability_matrix(
            conn=test_db, job_id="j1",
            file_path="story.txt", content=story,
            file_hash="h1", language=None,
            custom_prompt=prefix,
        )

    out_dir = _os_lib.path.dirname(result["output_path"])
    assert _os_lib.path.isfile(_os_lib.path.join(out_dir, "matrix.csv"))
    assert _os_lib.path.isfile(_os_lib.path.join(out_dir, "matrix.md"))
    assert _os_lib.path.isfile(_os_lib.path.join(out_dir, "gaps.md"))

    rows = list(_csv.DictReader(open(_os_lib.path.join(out_dir, "matrix.csv"),
                                     "r", encoding="utf-8")))
    assert len(rows) == 4

    gaps = open(_os_lib.path.join(out_dir, "gaps.md"), "r", encoding="utf-8").read()
    assert "test_admin_audit_log_flush" in gaps


def test_empty_tests_folder_yields_all_red(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    story = "AC-1: do thing A.\nAC-2: do thing B.\n"
    prefix = f"__stories__\n{story}\n__tests_dir__={empty}"
    with patch("agents.traceability_matrix.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_MATCH_BATCH
        mock_cls.return_value = mock_agent
        result = run_traceability_matrix(
            conn=test_db, job_id="j3",
            file_path="story.txt", content=story,
            file_hash="h3", language=None, custom_prompt=prefix,
        )
    rows = list(_csv.DictReader(open(_os_lib.path.join(_os_lib.path.dirname(result["output_path"]),
                                                        "matrix.csv"), "r", encoding="utf-8")))
    assert all(r["Status"] == "red" for r in rows)


def test_append_prefix_wrap_is_handled_end_to_end(test_db, tmp_path, monkeypatch):
    """Regression: Commit 1 wraps F10 prefix with _APPEND_PREFIX."""
    from agents._bedrock import _APPEND_PREFIX
    monkeypatch.chdir(tmp_path)
    root = _project_root()
    story = (root / "tests/fixtures/wave6a/reset_password_story.txt").read_text(encoding="utf-8")
    tests_dir = str(root / "tests/fixtures/wave6a/reset_password_tests")
    prefix = f"{_APPEND_PREFIX}__stories__\n{story}\n__tests_dir__={tests_dir}"
    with patch("agents.traceability_matrix.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.side_effect = [_CANNED_MATCH_BATCH] * 5
        mock_cls.return_value = mock_agent
        result = run_traceability_matrix(
            conn=test_db, job_id="j4",
            file_path="story.txt", content=story,
            file_hash="h4", language=None, custom_prompt=prefix,
        )
    # Should produce the same kind of output - story resolved, matrix written
    assert result.get("output_path")
    assert _os_lib.path.isfile(result["output_path"])
