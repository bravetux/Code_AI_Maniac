from db.queries.jobs import create_job, get_job, update_job_status, list_jobs
from db.queries.cache import store_result, get_cached_result
from db.queries.presets import create_preset, list_presets, delete_preset


def test_create_and_get_job(test_db):
    job_id = create_job(test_db, source_type="local", source_ref="/tmp/foo.py",
                        language="Python", features=["bug_analysis"])
    job = get_job(test_db, job_id)
    assert job["status"] == "pending"
    assert job["source_type"] == "local"
    assert job["language"] == "Python"
    assert "bug_analysis" in job["features"]


def test_update_job_status(test_db):
    job_id = create_job(test_db, source_type="local", source_ref="/tmp/bar.py",
                        language="Go", features=["mermaid"])
    update_job_status(test_db, job_id, "completed")
    job = get_job(test_db, job_id)
    assert job["status"] == "completed"
    assert job["completed_at"] is not None


def test_cache_miss_returns_none(test_db):
    result = get_cached_result(test_db, file_hash="abc123", feature="bug_analysis", language="Python")
    assert result is None


def test_cache_store_and_hit(test_db):
    job_id = create_job(test_db, source_type="local", source_ref="/tmp/test.py",
                        language="Python", features=["bug_analysis"])
    store_result(test_db, job_id=job_id, feature="bug_analysis",
                 file_hash="abc123", language="Python",
                 result={"bugs": [{"line": 10, "severity": "major", "message": "unused variable"}]})
    result = get_cached_result(test_db, file_hash="abc123", feature="bug_analysis", language="Python")
    assert result is not None
    assert result["bugs"][0]["line"] == 10


def test_preset_crud(test_db):
    preset_id = create_preset(test_db, name="Security Review",
                               feature="bug_analysis",
                               system_prompt="Focus on security issues only.",
                               extra_instructions="Highlight OWASP top 10.")
    presets = list_presets(test_db, feature="bug_analysis")
    assert any(p["name"] == "Security Review" for p in presets)
    delete_preset(test_db, preset_id)
    presets = list_presets(test_db, feature="bug_analysis")
    assert not any(p["name"] == "Security Review" for p in presets)
