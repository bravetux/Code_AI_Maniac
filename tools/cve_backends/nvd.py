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

"""NVD API backend. Requires NVD_API_KEY for reasonable rate limits."""
from __future__ import annotations
import httpx

_NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

def lookup_nvd(packages: list[dict], api_key: str | None = None) -> list[dict]:
    if api_key is None:
        from config.settings import get_settings
        api_key = get_settings().nvd_api_key or None
    headers = {}
    if api_key: headers["apiKey"] = api_key
    results = []
    for pkg in packages:
        vulns, error = [], None
        try:
            resp = httpx.get(_NVD_URL, params={"keywordSearch": pkg["name"], "resultsPerPage": 10}, headers=headers, timeout=20)
            if resp.status_code == 200:
                for item in resp.json().get("vulnerabilities", []):
                    cve = item.get("cve", {})
                    desc_list = cve.get("descriptions", [])
                    summary = next((d["value"] for d in desc_list if d.get("lang") == "en"), "")
                    metrics = cve.get("metrics", {})
                    severity = "major"
                    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        ml = metrics.get(key, [])
                        if ml:
                            bs = ml[0].get("cvssData", {}).get("baseScore", 0)
                            severity = "critical" if bs >= 9.0 else ("major" if bs >= 7.0 else "minor")
                            break
                    vulns.append({"cve_id": cve.get("id", ""), "summary": summary[:200], "severity": severity, "fixed_in": None, "source": "nvd"})
            elif resp.status_code == 403:
                error = "NVD API key required or rate limit exceeded"
        except Exception as e:
            error = str(e)
        entry = {"package": pkg["name"], "version": pkg.get("version"), "ecosystem": pkg.get("ecosystem", ""), "vulnerabilities": vulns}
        if error: entry["error"] = error
        results.append(entry)
    return results
