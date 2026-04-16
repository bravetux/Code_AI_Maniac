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

import json
from unittest.mock import patch, MagicMock
from agents.dependency_analysis import run_dependency_analysis


SAMPLE_REQUIREMENTS = "requests==2.25.1\nflask>=2.0.0\n"

MOCK_CVE_RESULTS = [
    {
        "package": "requests",
        "version": "2.25.1",
        "ecosystem": "PyPI",
        "vulnerabilities": [
            {
                "cve_id": "CVE-2023-32681",
                "summary": "Unintended leak of Proxy-Authorization header",
                "severity": "major",
                "fixed_in": "2.31.0",
                "source": "osv",
            }
        ],
    },
    {
        "package": "flask",
        "version": "2.0.0",
        "ecosystem": "PyPI",
        "vulnerabilities": [],
    },
]

MOCK_LLM_RESPONSE = json.dumps({
    "risk_summary": "1 vulnerable dependency found. requests has a known proxy header leak.",
    "remediation": "Upgrade requests to 2.31.0 or later.",
    "summary": "2 dependencies scanned, 1 vulnerable."
})


def test_run_dependency_analysis_structured_result(test_db):
    with patch("agents.dependency_analysis.lookup_vulnerabilities", return_value=MOCK_CVE_RESULTS), \
         patch("agents.dependency_analysis.Agent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_LLM_RESPONSE
        mock_agent_cls.return_value = mock_agent

        result = run_dependency_analysis(
            conn=test_db,
            job_id="test-job-1",
            file_path="requirements.txt",
            content=SAMPLE_REQUIREMENTS,
            file_hash="fakehash",
            language="Python",
            custom_prompt=None,
        )

    assert "dependencies" in result
    assert len(result["dependencies"]) == 2
    vuln_pkg = next(d for d in result["dependencies"] if d["package"] == "requests")
    assert len(vuln_pkg["vulnerabilities"]) == 1
    assert "summary" in result


def test_run_dependency_analysis_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="requirements.txt",
                        language="Python", features=["dependency_analysis"])
    cached = {"dependencies": [], "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="dependency_analysis:v1",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached)

    with patch("agents.dependency_analysis.Agent") as mock_cls:
        result = run_dependency_analysis(
            conn=test_db, job_id=job_id,
            file_path="requirements.txt", content="requests==2.25.1",
            file_hash="cached_hash", language="Python", custom_prompt=None,
        )
        mock_cls.assert_not_called()

    assert result["summary"] == "from cache"


def test_run_dependency_analysis_no_dep_file(test_db):
    """Running on a non-dependency file returns empty results."""
    result = run_dependency_analysis(
        conn=test_db,
        job_id="test-job-2",
        file_path="main.py",
        content="print('hello')",
        file_hash="nondep",
        language="Python",
        custom_prompt=None,
    )
    assert result["dependencies"] == []
    assert "No dependency file" in result["summary"]
