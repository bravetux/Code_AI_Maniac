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

"""GitHub Advisory Database backend. Uses existing GITHUB_TOKEN."""
from __future__ import annotations
import httpx

_GHSA_GRAPHQL = "https://api.github.com/graphql"
_ECO_MAP = {"PyPI": "PIP", "npm": "NPM", "Maven": "MAVEN", "NuGet": "NUGET", "Go": "GO", "crates.io": "RUST"}
_QUERY = """
query($ecosystem: SecurityAdvisoryEcosystem, $package: String!) {
  securityVulnerabilities(first: 10, ecosystem: $ecosystem, package: $package) {
    nodes { advisory { ghsaId summary severity } firstPatchedVersion { identifier } vulnerableVersionRange }
  }
}"""
_SEVERITY_MAP = {"CRITICAL": "critical", "HIGH": "major", "MODERATE": "major", "LOW": "minor"}

def lookup_github(packages: list[dict], token: str | None = None) -> list[dict]:
    if token is None:
        from config.settings import get_settings
        token = get_settings().github_token
    if not token:
        return [{"package": p["name"], "version": p.get("version"), "ecosystem": p.get("ecosystem", ""),
                 "vulnerabilities": [], "error": "GITHUB_TOKEN required for GitHub Advisory backend"} for p in packages]
    headers = {"Authorization": f"bearer {token}"}
    results = []
    for pkg in packages:
        vulns, error = [], None
        ecosystem = _ECO_MAP.get(pkg.get("ecosystem", ""))
        if ecosystem:
            try:
                resp = httpx.post(_GHSA_GRAPHQL, json={"query": _QUERY, "variables": {"ecosystem": ecosystem, "package": pkg["name"]}}, headers=headers, timeout=15)
                if resp.status_code == 200:
                    nodes = resp.json().get("data", {}).get("securityVulnerabilities", {}).get("nodes", [])
                    for node in nodes:
                        adv = node.get("advisory", {})
                        vulns.append({"cve_id": adv.get("ghsaId", ""), "summary": adv.get("summary", ""),
                                      "severity": _SEVERITY_MAP.get(adv.get("severity", ""), "major"),
                                      "fixed_in": (node.get("firstPatchedVersion") or {}).get("identifier"), "source": "github"})
                else: error = f"GitHub API returned {resp.status_code}"
            except Exception as e: error = str(e)
        else: error = f"Ecosystem {pkg.get('ecosystem')} not supported by GitHub Advisory DB"
        entry = {"package": pkg["name"], "version": pkg.get("version"), "ecosystem": pkg.get("ecosystem", ""), "vulnerabilities": vulns}
        if error: entry["error"] = error
        results.append(entry)
    return results
