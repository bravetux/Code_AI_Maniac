"""SAST / Threat Model agent — Phase 4.

Produces formal STRIDE threat models or attacker-narrative reports.
Consumes findings from all prior phases for maximum context.
"""
from __future__ import annotations
import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_FORMAL_PROMPT = """You are a security architect performing a formal threat model using STRIDE methodology.

You will receive source code and findings from prior analysis agents (bugs, static analysis,
secret scan, dependency analysis). Use ALL of this context to produce a comprehensive threat model.

Analyze the code for:
- Trust boundaries between components
- Attack surface (entry points, data inputs, external interfaces)
- STRIDE threats: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege

For each threat, cross-reference with prior findings when relevant.

Return a JSON object:
{
  "mode": "formal",
  "trust_boundaries": [
    {"id": "TB-N", "description": "<boundary description>", "components": ["<function/class names>"]}
  ],
  "attack_surface": [
    {"entry_point": "<endpoint/function>", "exposure": "<public|internal|authenticated>", "data_handled": "<what data>"}
  ],
  "stride_analysis": [
    {
      "id": "T-NNN",
      "category": "<Spoofing|Tampering|Repudiation|Information Disclosure|Denial of Service|Elevation of Privilege>",
      "asset": "<what is threatened>",
      "threat": "<threat description>",
      "attack_vector": "<how an attacker exploits this>",
      "likelihood": "<high|medium|low>",
      "impact": "<high|medium|low>",
      "risk_score": "<critical|major|minor>",
      "existing_mitigation": "<what defenses exist>",
      "recommended_mitigation": "<what to add>",
      "original_code": "<the vulnerable code snippet from the source>",
      "fixed_code": "<the corrected code snippet that mitigates the threat>",
      "related_findings": ["<agent:detail>"]
    }
  ],
  "data_flow_mermaid": "<Mermaid flowchart source showing data flow and trust boundaries>",
  "summary": "<count of threats by severity>"
}"""

_ATTACKER_PROMPT = """You are a penetration tester writing an attack assessment report.

Think like a malicious hacker. You will receive source code and findings from prior analysis agents.
Identify realistic attack scenarios and explain how to exploit them.

Return a JSON object:
{
  "mode": "attacker",
  "executive_summary": "<2-3 sentence overall risk posture>",
  "attack_scenarios": [
    {
      "id": "A-NNN",
      "title": "<attack name>",
      "stride_category": "<STRIDE category>",
      "risk_score": "<critical|major|minor>",
      "narrative": "<step-by-step attack story>",
      "prerequisites": "<what attacker needs>",
      "impact": "<business impact>",
      "proof_of_concept": "<pseudocode or exploit description>",
      "mitigation": "<defensive measures>",
      "original_code": "<the vulnerable code snippet from the source>",
      "fixed_code": "<the corrected code snippet that mitigates the threat>",
      "related_findings": ["<agent:detail>"]
    }
  ],
  "priority_ranking": ["A-NNN", "..."],
  "summary": "<count of scenarios by severity>"
}"""

_CACHE_KEY = "threat_model:v1"


def run_threat_model(conn: duckdb.DuckDBPyConnection, job_id: str,
                     file_path: str, content: str, file_hash: str,
                     language: str | None, custom_prompt: str | None,
                     threat_model_mode: str | None = None,
                     bug_results: dict | None = None,
                     static_results: dict | None = None,
                     secret_results: dict | None = None,
                     dependency_results: dict | None = None) -> dict:
    mode = threat_model_mode or "formal"

    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    system_prompt = _FORMAL_PROMPT if mode == "formal" else _ATTACKER_PROMPT
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, system_prompt))

    # Build context from prior phases
    context_parts = []
    if bug_results and bug_results.get("bugs"):
        bug_summary = [f"Line {b.get('line', '?')}: [{b.get('severity', '')}] {b.get('description', '')[:100]}"
                       for b in bug_results["bugs"][:10]]
        context_parts.append(f"Bug Analysis findings:\n" + "\n".join(bug_summary))
    if static_results and static_results.get("semantic_findings"):
        static_summary = [f"Line {f.get('line', '?')}: [{f.get('category', '')}] {f.get('description', '')[:100]}"
                          for f in static_results["semantic_findings"][:10]]
        context_parts.append(f"Static Analysis findings:\n" + "\n".join(static_summary))
    if secret_results and secret_results.get("secrets"):
        secret_summary = [f"Line {s.get('line', '?')}: [{s.get('type', '')}] {s.get('description', '')[:100]}"
                          for s in secret_results["secrets"][:10]]
        context_parts.append(f"Secret Scan findings:\n" + "\n".join(secret_summary))
    if dependency_results and dependency_results.get("dependencies"):
        vuln_deps = [d for d in dependency_results["dependencies"] if d.get("vulnerabilities")]
        if vuln_deps:
            dep_summary = [f"{d['package']} {d.get('version', '?')}: {len(d['vulnerabilities'])} CVE(s)"
                           for d in vuln_deps[:10]]
            context_parts.append(f"Dependency Analysis findings:\n" + "\n".join(dep_summary))

    prior_context = "\n\n".join(context_parts) if context_parts else "No prior findings."
    chunks = chunk_by_lines(content, max_tokens=3000)
    all_code = "\n".join(c["content"] for c in chunks)

    prompt = (f"Language: {language or 'detect from code'}\nFile: {file_path}\n"
              f"Threat model mode: {mode}\n\nPrior agent findings:\n{prior_context}\n\n"
              f"Source code:\n{all_code}")

    raw = str(agent(prompt))
    try:
        result = parse_json_response(raw)
        result["mode"] = mode
    except (json.JSONDecodeError, ValueError):
        result = {"mode": mode, "summary": "Threat model generation failed.", "narrative": raw}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="threat_model",
                source_ref=file_path, language=language,
                summary=result.get("summary", ""))
    return result
