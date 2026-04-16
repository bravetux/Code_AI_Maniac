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

from db.queries.jobs import create_job, get_job, update_job_status, list_jobs
from db.queries.cache import store_result, get_cached_result
from db.queries.presets import create_preset, list_presets, delete_preset
from db.queries.sidebar_profiles import save_profile, list_profiles, get_profile, delete_profile


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


def test_sidebar_profile_save_and_load(test_db):
    profile_id = save_profile(
        test_db,
        name="Bug Finder",
        source_type="local",
        features=["bug_analysis", "static_analysis"],
        language="Python",
        custom_prompt="Focus on security.",
        extra_instructions="OWASP top 10.",
        mermaid_type="flowchart",
    )
    assert profile_id

    profile = get_profile(test_db, "Bug Finder")
    assert profile is not None
    assert profile["source_type"] == "local"
    assert "bug_analysis" in profile["features"]
    assert profile["language"] == "Python"
    assert profile["mermaid_type"] == "flowchart"


def test_sidebar_profile_upsert_by_name(test_db):
    save_profile(test_db, name="My Profile", source_type="local",
                 features=["bug_analysis"], language="Python",
                 custom_prompt=None, extra_instructions=None)
    # Save again with same name — should update, not duplicate
    save_profile(test_db, name="My Profile", source_type="github",
                 features=["code_design"], language="Go",
                 custom_prompt=None, extra_instructions=None)

    profiles = [p for p in list_profiles(test_db) if p["name"] == "My Profile"]
    assert len(profiles) == 1
    assert profiles[0]["source_type"] == "github"
    assert profiles[0]["language"] == "Go"


def test_sidebar_profile_list_and_delete(test_db):
    save_profile(test_db, name="Profile A", source_type="local",
                 features=["mermaid"], language=None,
                 custom_prompt=None, extra_instructions=None)
    save_profile(test_db, name="Profile B", source_type="gitea",
                 features=["commit_analysis"], language=None,
                 custom_prompt=None, extra_instructions=None)

    profiles = list_profiles(test_db)
    names = [p["name"] for p in profiles]
    assert "Profile A" in names
    assert "Profile B" in names

    target = next(p for p in profiles if p["name"] == "Profile A")
    delete_profile(test_db, target["id"])

    remaining = [p["name"] for p in list_profiles(test_db)]
    assert "Profile A" not in remaining
    assert "Profile B" in remaining


def test_sidebar_profile_get_missing_returns_none(test_db):
    assert get_profile(test_db, "Nonexistent Profile") is None
