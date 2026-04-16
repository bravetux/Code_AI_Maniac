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
import pytest
from unittest.mock import patch, MagicMock
from tools.cve_backends import get_backend, lookup_vulnerabilities
from tools.cve_backends.osv import lookup_osv
from tools.cve_backends.nvd import lookup_nvd
from tools.cve_backends.github_advisory import lookup_github
from tools.cve_backends.llm_only import lookup_llm
from tools.cve_backends.hybrid import lookup_hybrid


# ── Backend registry ─────────────────────────────────────────────────────────

def test_get_backend_osv():
    fn = get_backend("osv")
    assert fn is lookup_osv

def test_get_backend_nvd():
    fn = get_backend("nvd")
    assert fn is lookup_nvd

def test_get_backend_github():
    fn = get_backend("github")
    assert fn is lookup_github

def test_get_backend_llm():
    fn = get_backend("llm")
    assert fn is lookup_llm

def test_get_backend_osv_llm():
    fn = get_backend("osv_llm")
    assert fn is lookup_hybrid

def test_get_backend_invalid():
    with pytest.raises(ValueError, match="Unknown CVE backend"):
        get_backend("invalid")


# ── OSV backend ──────────────────────────────────────────────────────────────

def test_osv_lookup_with_mock(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulns": [
            {
                "id": "GHSA-xxxx-xxxx-xxxx",
                "summary": "Test vulnerability",
                "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"}],
                "affected": [{"ranges": [{"events": [{"fixed": "2.31.0"}]}]}],
            }
        ]
    }

    with patch("tools.cve_backends.osv.httpx.post", return_value=mock_response):
        results = lookup_osv([{"name": "requests", "version": "2.25.1", "ecosystem": "PyPI"}])

    assert len(results) == 1
    assert results[0]["package"] == "requests"
    assert len(results[0]["vulnerabilities"]) == 1
    assert results[0]["vulnerabilities"][0]["cve_id"] == "GHSA-xxxx-xxxx-xxxx"


def test_osv_lookup_no_vulns(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"vulns": []}

    with patch("tools.cve_backends.osv.httpx.post", return_value=mock_response):
        results = lookup_osv([{"name": "safe-pkg", "version": "1.0.0", "ecosystem": "PyPI"}])

    assert len(results) == 1
    assert results[0]["vulnerabilities"] == []


def test_osv_lookup_api_error(monkeypatch):
    with patch("tools.cve_backends.osv.httpx.post", side_effect=Exception("network error")):
        results = lookup_osv([{"name": "requests", "version": "2.25.1", "ecosystem": "PyPI"}])

    assert len(results) == 1
    assert results[0]["vulnerabilities"] == []
    assert "error" in results[0]


# ── Dispatcher ───────────────────────────────────────────────────────────────

def test_lookup_vulnerabilities_dispatches():
    packages = [{"name": "requests", "version": "2.25.1", "ecosystem": "PyPI"}]
    with patch("tools.cve_backends.osv.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"vulns": []}
        mock_post.return_value = mock_resp
        results = lookup_vulnerabilities(packages, backend="osv")
    assert len(results) == 1
