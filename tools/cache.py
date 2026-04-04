import hashlib
import duckdb
from db.queries.cache import get_cached_result, store_result


def compute_cache_key(file_hash: str, feature: str,
                      language: str | None, custom_prompt: str | None) -> str:
    """Combine file hash + feature + language + prompt into a single cache key."""
    raw = f"{file_hash}:{feature}:{language or ''}:{custom_prompt or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def check_cache(conn: duckdb.DuckDBPyConnection, file_hash: str, feature: str,
                language: str | None, custom_prompt: str | None) -> dict | None:
    """Return cached result if available, else None.
    Cached results carry _from_cache=True so callers can distinguish hits from fresh runs."""
    key = compute_cache_key(file_hash, feature, language, custom_prompt)
    result = get_cached_result(conn, file_hash=key, feature=feature, language=language)
    if result is not None:
        result = dict(result)
        result["_from_cache"] = True
    return result


def write_cache(conn: duckdb.DuckDBPyConnection, job_id: str, feature: str,
                file_hash: str, language: str | None, custom_prompt: str | None,
                result: dict) -> None:
    """Store result in cache keyed by composite hash."""
    key = compute_cache_key(file_hash, feature, language, custom_prompt)
    store_result(conn, job_id=job_id, feature=feature,
                 file_hash=key, language=language, result=result)
