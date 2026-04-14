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
