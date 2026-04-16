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

"""OSV.dev API backend — free, no API key, covers all ecosystems."""
from __future__ import annotations
import httpx

_OSV_URL = "https://api.osv.dev/v1/query"
_ECOSYSTEM_MAP = {
    "PyPI": "PyPI", "npm": "npm", "Maven": "Maven", "NuGet": "NuGet",
    "Go": "Go", "crates.io": "crates.io", "conan": "ConanCenter", "vcpkg": None,
}

def _severity_from_cvss(severity_list: list[dict]) -> str:
    for entry in severity_list:
        score_str = entry.get("score", "")
        if "CVSS" in score_str:
            parts = score_str.split("/")
            for p in parts:
                if p.replace(".", "").replace("-", "").isdigit():
                    try:
                        score = float(p)
                        if score >= 9.0: return "critical"
                        if score >= 7.0: return "major"
                        return "minor"
                    except ValueError:
                        continue
    return "major"

def _extract_fixed_version(affected: list[dict]) -> str | None:
    for aff in affected:
        for rng in aff.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event: return event["fixed"]
    return None

def lookup_osv(packages: list[dict]) -> list[dict]:
    results = []
    for pkg in packages:
        ecosystem = _ECOSYSTEM_MAP.get(pkg.get("ecosystem", ""), pkg.get("ecosystem"))
        version = pkg.get("version")
        vulns, error = [], None
        if ecosystem and version:
            try:
                resp = httpx.post(_OSV_URL, json={"package": {"name": pkg["name"], "ecosystem": ecosystem}, "version": version}, timeout=15)
                if resp.status_code == 200:
                    for v in resp.json().get("vulns", []):
                        vulns.append({"cve_id": v.get("id", ""), "summary": v.get("summary", ""),
                                      "severity": _severity_from_cvss(v.get("severity", [])),
                                      "fixed_in": _extract_fixed_version(v.get("affected", [])), "source": "osv"})
            except Exception as e:
                error = str(e)
        entry = {"package": pkg["name"], "version": version, "ecosystem": pkg.get("ecosystem", ""), "vulnerabilities": vulns}
        if error: entry["error"] = error
        results.append(entry)
    return results
