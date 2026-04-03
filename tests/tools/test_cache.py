from tools.cache import compute_cache_key, check_cache, write_cache


def test_compute_cache_key_deterministic():
    key1 = compute_cache_key("abc123", "bug_analysis", "Python", None)
    key2 = compute_cache_key("abc123", "bug_analysis", "Python", None)
    assert key1 == key2


def test_compute_cache_key_prompt_sensitive():
    key1 = compute_cache_key("abc123", "bug_analysis", "Python", "custom prompt A")
    key2 = compute_cache_key("abc123", "bug_analysis", "Python", "custom prompt B")
    assert key1 != key2


def test_check_cache_miss(test_db):
    result = check_cache(test_db, "nonexistent_hash", "bug_analysis", "Python", None)
    assert result is None


def test_write_and_read_cache(test_db):
    from db.queries.jobs import create_job
    job_id = create_job(test_db, source_type="local", source_ref="/tmp/f.py",
                        language="Python", features=["bug_analysis"])
    payload = {"bugs": [{"line": 5, "severity": "major"}]}
    write_cache(test_db, job_id=job_id, feature="bug_analysis",
                file_hash="hash_abc", language="Python",
                custom_prompt=None, result=payload)
    cached = check_cache(test_db, "hash_abc", "bug_analysis", "Python", None)
    assert cached is not None
    assert cached["bugs"][0]["line"] == 5
