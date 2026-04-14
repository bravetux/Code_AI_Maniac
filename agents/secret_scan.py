"""Deep Secret Scanner agent — Phase 3 (synthesis).

AI-powered detection of secrets that regex-based scanning misses:
encoded credentials, split secrets, hardcoded fallbacks, etc.
"""
from __future__ import annotations
import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a secrets detection specialist performing deep analysis.

You will receive source code along with:
- Phase 0 regex findings (secrets already detected by pattern matching)
- Static analysis results (security issues already flagged)

Your job is to find what regex and static analysis MISSED:
- Base64/hex-encoded secrets
- Secrets assembled across multiple variables (key = prefix + suffix)
- Secrets in string formatting or interpolation
- Hardcoded encryption keys or salts
- Secrets in comments or docstrings
- Environment variable fallbacks to hardcoded values: os.getenv("KEY", "actual-secret")
- Config values that look like placeholders but are actually real credentials

Also validate Phase 0 regex findings — confirm or dismiss each as a false positive.

Return a JSON object:
{
  "secrets": [
    {
      "line": <integer>,
      "type": "<encoded_credential|split_secret|hardcoded_fallback|embedded_key|comment_secret>",
      "severity": "<critical|major|minor>",
      "description": "<what the secret is and why it's a risk>",
      "evidence": "<the suspicious code pattern — mask the actual secret value>",
      "recommendation": "<specific remediation step>",
      "false_positive_risk": "<low|medium|high>"
    }
  ],
  "phase0_validation": [
    {
      "line": <integer>,
      "phase0_type": "<type from Phase 0>",
      "verdict": "<confirmed|false_positive>",
      "reason": "<why you confirm or dismiss this finding>"
    }
  ],
  "narrative": "<overall secrets hygiene assessment>",
  "summary": "<one sentence count>"
}

If no additional secrets are found, return empty lists. Always validate Phase 0 findings."""

_CACHE_KEY = "secret_scan:v1"


def run_secret_scan(conn: duckdb.DuckDBPyConnection, job_id: str,
                    file_path: str, content: str, file_hash: str,
                    language: str | None, custom_prompt: str | None,
                    phase0_findings: list[dict] | None = None,
                    static_results: dict | None = None) -> dict:
    """Run AI-powered deep secret detection."""
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_secrets = []
    all_validations = []
    narratives = []

    phase0_ctx = json.dumps(phase0_findings or [], indent=2)
    static_ctx = ""
    if static_results:
        static_security = [
            f for f in static_results.get("semantic_findings", [])
            if f.get("category") == "security"
        ]
        if static_security:
            static_ctx = f"\nStatic analysis security findings: {json.dumps(static_security, indent=2)}"

    for chunk in chunks:
        prompt = (
            f"Language: {language or 'detect from code'}\n"
            f"File: {file_path}\n"
            f"Phase 0 regex findings: {phase0_ctx}\n"
            f"{static_ctx}\n\n"
            f"Source code (lines {chunk['start_line']}-{chunk['end_line']}):\n"
            f"{chunk['content']}"
        )
        raw = str(agent(prompt))
        try:
            parsed = parse_json_response(raw)
            all_secrets.extend(parsed.get("secrets", []))
            all_validations.extend(parsed.get("phase0_validation", []))
            if parsed.get("narrative"):
                narratives.append(parsed["narrative"])
        except (json.JSONDecodeError, ValueError):
            narratives.append(raw)

    # Deduplicate by (line, type)
    seen = set()
    deduped = []
    for secret in all_secrets:
        key = (secret.get("line"), secret.get("type"))
        if key not in seen:
            seen.add(key)
            deduped.append(secret)

    confirmed = sum(1 for v in all_validations if v.get("verdict") == "confirmed")
    dismissed = sum(1 for v in all_validations if v.get("verdict") == "false_positive")

    result = {
        "secrets": deduped,
        "phase0_validation": all_validations,
        "narrative": "\n\n".join(narratives) if narratives else "",
        "summary": (
            f"{len(deduped)} secret(s) found"
            + (f", {confirmed} Phase 0 confirmed" if confirmed else "")
            + (f", {dismissed} dismissed" if dismissed else "")
            + "."
        ),
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="secret_scan",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
