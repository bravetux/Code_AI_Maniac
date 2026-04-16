# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

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
