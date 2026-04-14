"""SCA / Dependency Analysis agent — Phase 1.

Two-layer approach:
  Layer 1: Parse dependency file (tools/dependency_parser.py)
  Layer 2: CVE lookup + LLM risk assessment (tools/cve_backends/)
"""
from __future__ import annotations
import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.dependency_parser import parse_dependency_file
from tools.cve_backends import lookup_vulnerabilities
from tools.cache import check_cache, write_cache
from db.queries.history import add_history
from config.settings import get_settings

_SYSTEM_PROMPT = """You are a software supply chain security expert.

You will receive a list of dependencies with their known vulnerability data.
Provide:
1. A prioritized risk summary — which vulnerabilities matter most and why
2. A remediation plan — concrete upgrade steps ordered by priority
3. Assessment of overall supply chain health

Return a JSON object:
{
  "risk_summary": "<prioritized assessment of the most critical findings>",
  "remediation": "<concrete upgrade/migration plan>",
  "summary": "<one sentence count: X dependencies scanned, Y vulnerable, Z outdated>"
}"""

_CACHE_KEY = "dependency_analysis:v1"

_DEP_BASENAMES = {
    "requirements.txt", "pyproject.toml", "setup.cfg", "Pipfile",
    "package.json", "package-lock.json", "yarn.lock",
    "pom.xml", "build.gradle",
    "CMakeLists.txt", "conanfile.txt", "vcpkg.json",
    "packages.config", "Directory.Packages.props",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
}
_DEP_EXTENSIONS = {".csproj"}


def _is_dep_file(file_path: str) -> bool:
    import os
    basename = os.path.basename(file_path)
    ext = os.path.splitext(basename)[1]
    return basename in _DEP_BASENAMES or ext in _DEP_EXTENSIONS


def run_dependency_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None,
                            custom_prompt: str | None) -> dict:
    if not _is_dep_file(file_path):
        return {
            "dependencies": [],
            "risk_summary": "",
            "remediation": "",
            "summary": "No dependency file detected — SCA skipped.",
        }

    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    s = get_settings()

    parsed = parse_dependency_file(file_path, content)
    packages = parsed.get("packages", [])

    if not packages:
        result = {
            "dependencies": [],
            "risk_summary": "No packages found in dependency file.",
            "remediation": "",
            "summary": "0 dependencies found.",
        }
        write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                    file_hash=file_hash, language=language,
                    custom_prompt=custom_prompt, result=result)
        return result

    ecosystem = parsed.get("ecosystem", "unknown")
    for pkg in packages:
        pkg.setdefault("ecosystem", ecosystem)

    cve_results = lookup_vulnerabilities(packages, backend=s.sca_cve_backend)

    vulnerable_count = sum(1 for r in cve_results if r.get("vulnerabilities"))
    risk_summary = ""
    remediation = ""

    if s.sca_cve_backend != "llm":
        try:
            model = make_bedrock_model()
            agent = Agent(model=model,
                          system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))
            dep_summary = json.dumps(cve_results, indent=2, default=str)
            raw = str(agent(f"Assess these dependency scan results:\n\n{dep_summary}"))
            parsed_resp = parse_json_response(raw)
            risk_summary = parsed_resp.get("risk_summary", "")
            remediation = parsed_resp.get("remediation", "")
        except Exception:
            risk_summary = f"{vulnerable_count} vulnerable package(s) found."
            remediation = ""

    result = {
        "dependencies": cve_results,
        "risk_summary": risk_summary,
        "remediation": remediation,
        "summary": (f"{len(packages)} dependencies scanned, "
                    f"{vulnerable_count} vulnerable."),
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="dependency_analysis",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
