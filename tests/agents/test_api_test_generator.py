from agents.api_test_generator import run_api_test_generator


def test_stub_returns_placeholder_markdown(test_db):
    # Now that F5 is filled, with no spec resolvable we get an error markdown.
    result = run_api_test_generator(
        conn=test_db,
        job_id="test-job-1",
        file_path="not_a_spec.py",
        content="print('hi')",
        file_hash="fakehash-no-spec",
        language="python",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "error" in result["summary"].lower() or "API Test Generator" in result["markdown"]


def test_orchestrator_dispatches_api_test_generator(test_db):
    from db.queries.jobs import create_job, get_job, get_job_results
    from db.queries.job_events import get_events
    from agents.orchestrator import run_analysis
    job_id = create_job(test_db, source_type="local",
                        source_ref="tests/fixtures/wave6a/petstore_openapi.yaml",
                        language="python",
                        features=["api_test_generator"])
    run_analysis(test_db, job_id)
    job = get_job(test_db, job_id)
    assert job is not None
    assert job["status"] in ("completed", "failed"), f"unexpected status: {job['status']}"
    # Stub returns a placeholder — it should have produced a per-file result
    # under the api_test_generator key visible via the job's result_json payload.
    results = get_job_results(test_db, job_id) or {}
    events = get_events(test_db, job_id)
    assert len(events) > 0, "expected at least one job_events row for the dispatch"
    # Accept either a dict with the feature key OR a JSON-ish payload that mentions it,
    # OR an event referencing the agent name.
    dispatch_trace = str(results) + " " + " ".join(str(e) for e in events)
    assert "api_test_generator" in dispatch_trace, \
        f"dispatch did not produce a result for api_test_generator: results={results!r} events={events!r}"


import pytest
from agents.api_test_generator import _resolve_spec, _SpecResolution


def test_resolve_spec_from_prefix():
    prefix = "__openapi_spec__\nopenapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n"
    res = _resolve_spec(file_path="ignored.py", content="print('hi')", custom_prompt=prefix)
    assert res.source == "prefix"
    assert res.spec["info"]["title"] == "t"


def test_resolve_spec_from_source_file_when_yaml():
    content = "openapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n"
    res = _resolve_spec(file_path="openapi.yaml", content=content, custom_prompt=None)
    assert res.source == "source"
    assert res.spec["openapi"] == "3.0.0"


def test_resolve_spec_from_source_file_when_json():
    content = '{"openapi":"3.0.0","info":{"title":"t","version":"0.1"},"paths":{}}'
    res = _resolve_spec(file_path="openapi.json", content=content, custom_prompt=None)
    assert res.source == "source"


def test_resolve_spec_from_sibling(tmp_path):
    code_file = tmp_path / "api_app.py"
    code_file.write_text("# pretend code\n", encoding="utf-8")
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text("openapi: 3.0.0\ninfo: {title: sib, version: '0.1'}\npaths: {}\n",
                         encoding="utf-8")
    res = _resolve_spec(file_path=str(code_file), content="# pretend code\n",
                        custom_prompt=None)
    assert res.source == "sibling"
    assert res.spec["info"]["title"] == "sib"


def test_resolve_spec_raises_on_malformed():
    with pytest.raises(Exception):
        _resolve_spec(file_path="openapi.yaml",
                      content="not: : : valid :: yaml ::",
                      custom_prompt="__openapi_spec__\nnot: : : valid :: yaml ::")


def test_resolve_spec_raises_when_nothing_found(tmp_path):
    code_file = tmp_path / "foo.py"
    code_file.write_text("print('hi')\n", encoding="utf-8")
    with pytest.raises(Exception):
        _resolve_spec(file_path=str(code_file), content="print('hi')\n", custom_prompt=None)


from agents.api_test_generator import _pick_framework


def test_pick_framework_python():
    meta = _pick_framework("python")
    assert meta["framework"] == "pytest + requests"
    assert meta["suffix"] == "test_api.py"
    assert meta["fence"] == "python"
    assert meta["mock"]


def test_pick_framework_java():
    meta = _pick_framework("java")
    assert "REST Assured" in meta["framework"]
    assert meta["suffix"] == "ApiTests.java"


def test_pick_framework_kotlin_uses_java_stack():
    assert _pick_framework("kotlin")["framework"] == _pick_framework("java")["framework"]


def test_pick_framework_csharp_aliases():
    for lang in ("csharp", "c#", ".net"):
        meta = _pick_framework(lang)
        assert "xUnit" in meta["framework"]
        assert meta["suffix"] == "ApiTests.cs"


def test_pick_framework_typescript():
    meta = _pick_framework("typescript")
    assert "supertest" in meta["framework"].lower()
    assert meta["suffix"] == "api.test.ts"


def test_pick_framework_javascript_uses_typescript_stack():
    assert _pick_framework("javascript")["framework"] == _pick_framework("typescript")["framework"]


def test_pick_framework_blank_returns_none():
    assert _pick_framework("") is None
    assert _pick_framework(None) is None


def test_pick_framework_unknown_returns_none():
    assert _pick_framework("cobol") is None


import json as _json_lib
import os as _os_lib
from unittest.mock import patch, MagicMock


_CANNED_PYTEST = '''```python
import pytest
import requests

BASE = "https://api.example.test"

def test_list_pets():
    r = requests.get(f"{BASE}/pets")
    assert r.status_code == 200

def test_create_pet():
    r = requests.post(f"{BASE}/pets", json={"name": "Rex"})
    assert r.status_code == 201

def test_create_pet_rejects_bad_body():
    r = requests.post(f"{BASE}/pets", json={})
    assert r.status_code == 400

def test_get_pet():
    r = requests.get(f"{BASE}/pets/1")
    assert r.status_code == 200

def test_get_pet_missing():
    r = requests.get(f"{BASE}/pets/99999")
    assert r.status_code == 404
```'''


_FIXTURE_PATH = "tests/fixtures/wave6a/petstore_openapi.yaml"


def test_run_api_test_generator_writes_both_artifacts(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import pathlib as _pl
    # Find project root by walking up until we see pytest.ini
    cur = _pl.Path(__file__).resolve()
    project_root = None
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            project_root = parent
            break
    if project_root is None:
        project_root = _pl.Path.cwd()
    spec_content = (project_root / _FIXTURE_PATH).read_text(encoding="utf-8")

    with patch("agents.api_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_PYTEST
        mock_cls.return_value = mock_agent
        result = run_api_test_generator(
            conn=test_db, job_id="j1",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h1", language="python", custom_prompt=None,
        )
    assert "output_path" in result and result["output_path"]
    assert _os_lib.path.isfile(result["output_path"])
    postman = _os_lib.path.join(_os_lib.path.dirname(result["output_path"]), "api_collection.json")
    assert _os_lib.path.isfile(postman)
    collection = _json_lib.loads(open(postman, "r", encoding="utf-8").read())
    assert len(collection["item"]) == 3
    assert "pytest" in result["markdown"].lower()


def test_run_api_test_generator_blank_language_still_writes_postman(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import pathlib as _pl
    cur = _pl.Path(__file__).resolve()
    project_root = None
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            project_root = parent
            break
    if project_root is None:
        project_root = _pl.Path.cwd()
    spec_content = (project_root / _FIXTURE_PATH).read_text(encoding="utf-8")
    with patch("agents.api_test_generator.Agent") as mock_cls:
        result = run_api_test_generator(
            conn=test_db, job_id="j2",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h2", language=None, custom_prompt=None,
        )
        mock_cls.assert_not_called()
    postman = result["postman_path"]
    assert _os_lib.path.isfile(postman)
    collection = _json_lib.loads(open(postman, "r", encoding="utf-8").read())
    assert len(collection["item"]) == 3


def test_run_api_test_generator_bad_spec_returns_error(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.api_test_generator.Agent") as mock_cls:
        result = run_api_test_generator(
            conn=test_db, job_id="j3",
            file_path="openapi.yaml", content="not: : : valid :: yaml",
            file_hash="h3", language="python", custom_prompt=None,
        )
        mock_cls.assert_not_called()
    assert "error" in result["summary"].lower() or "failed" in result["summary"].lower()
    assert result.get("output_path") is None


def test_run_api_test_generator_uses_cache(test_db):
    from tools.cache import write_cache
    cached = {"markdown": "CACHED", "summary": "cached", "output_path": "/tmp/cached.py"}
    write_cache(test_db, job_id="j4", feature="api_test_generator",
                file_hash="cachehash", language="python", custom_prompt=None,
                result=cached)
    result = run_api_test_generator(
        conn=test_db, job_id="j4",
        file_path="openapi.yaml", content="openapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}",
        file_hash="cachehash", language="python", custom_prompt=None,
    )
    assert result["markdown"] == "CACHED"
