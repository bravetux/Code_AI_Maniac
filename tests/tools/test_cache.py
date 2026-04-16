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
