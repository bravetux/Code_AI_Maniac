"""Hybrid backend — OSV.dev + LLM enrichment. Default backend (osv_llm)."""
from __future__ import annotations
import json
from tools.cve_backends.osv import lookup_osv
from agents._bedrock import make_bedrock_model, parse_json_response
from strands import Agent

_SYSTEM_PROMPT = """You are a software security expert. You receive dependencies with CVE data from OSV.
Provide risk assessment, exploitability rating, and remediation priority.
Also identify packages with no CVEs that you know have security concerns.
Return JSON: {"enrichments": [{"package": "<name>", "risk_context": "<context>", "exploitability": "<high|medium|low>", "remediation_priority": "<immediate|soon|low>"}],
"additional_concerns": [{"package": "<name>", "cve_id": "LLM-assessment", "summary": "<concern>", "severity": "<critical|major|minor>", "fixed_in": "<version>"}]}"""

def lookup_hybrid(packages: list[dict]) -> list[dict]:
    osv_results = lookup_osv(packages)
    try:
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)
        summary_lines = [f"- {r['package']} {r.get('version', '?')} ({r.get('ecosystem', '?')}): {len(r['vulnerabilities'])} known CVE(s)"
                         + (f" — {', '.join(v['cve_id'] for v in r['vulnerabilities'][:3])}" if r['vulnerabilities'] else "")
                         for r in osv_results]
        raw = str(agent(f"Assess these dependencies:\n\n" + "\n".join(summary_lines)))
        parsed = parse_json_response(raw)
        enrichments = {e["package"]: e for e in parsed.get("enrichments", [])}
        for r in osv_results:
            e = enrichments.get(r["package"])
            if e:
                r["risk_context"] = e.get("risk_context", "")
                r["exploitability"] = e.get("exploitability", "")
                r["remediation_priority"] = e.get("remediation_priority", "")
        pkg_map = {r["package"]: r for r in osv_results}
        for concern in parsed.get("additional_concerns", []):
            pn = concern.get("package", "")
            if pn in pkg_map:
                pkg_map[pn]["vulnerabilities"].append({"cve_id": concern.get("cve_id", "LLM-assessment"),
                    "summary": concern.get("summary", ""), "severity": concern.get("severity", "major"),
                    "fixed_in": concern.get("fixed_in"), "source": "llm"})
    except Exception:
        pass
    return osv_results
