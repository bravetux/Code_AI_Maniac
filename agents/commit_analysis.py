import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior engineer reviewing a git commit history.
Analyze the commits and provide:
1. Commit quality (message clarity, atomic vs mixed changes)
2. Changelog summary (what was added, changed, removed)
3. Risk assessment (risky changes, patterns of concern)

Return JSON:
{
  "commit_quality": [
    {"sha": "<short sha>", "message": "<message>", "quality": "<good|needs-improvement|poor>", "reason": "<why>"}
  ],
  "changelog": {
    "added": ["<feature or capability added>"],
    "changed": ["<what was modified>"],
    "removed": ["<what was deleted>"]
  },
  "risk_assessment": {
    "level": "<low|medium|high>",
    "concerns": ["<concern description>"]
  },
  "summary": "<overall assessment in one paragraph>"
}
Return ONLY valid JSON. No markdown fences."""


def run_commit_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                        repo_ref: str, commits: list[dict],
                        custom_prompt: str | None) -> dict:
    if not commits:
        return {"error": "No commits provided", "commit_quality": [],
                "changelog": {"added": [], "changed": [], "removed": []},
                "risk_assessment": {"level": "low", "concerns": []},
                "summary": "No commits to analyze."}

    s = get_settings()
    model = BedrockModel(model_id=s.bedrock_model_id, temperature=s.bedrock_temperature,
                         region_name=s.aws_region)
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    batch_size = 20
    all_quality = []
    all_added, all_changed, all_removed, all_concerns = [], [], [], []
    risk_levels = []

    for i in range(0, len(commits), batch_size):
        batch = commits[i:i + batch_size]
        prompt = f"Repository: {repo_ref}\nCommits:\n{json.dumps(batch, indent=2)}"
        raw = str(agent(prompt))
        text = re.sub(r"^```(?:json)?\n?", "", raw.strip())
        text = re.sub(r"\n?```$", "", text)
        try:
            parsed = json.loads(text)
            all_quality.extend(parsed.get("commit_quality", []))
            cl = parsed.get("changelog", {})
            all_added.extend(cl.get("added", []))
            all_changed.extend(cl.get("changed", []))
            all_removed.extend(cl.get("removed", []))
            ra = parsed.get("risk_assessment", {})
            risk_levels.append(ra.get("level", "low"))
            all_concerns.extend(ra.get("concerns", []))
        except (json.JSONDecodeError, ValueError):
            pass

    risk_map = {"high": 3, "medium": 2, "low": 1}
    max_risk = max((risk_map.get(r, 1) for r in risk_levels), default=1)
    final_risk = {3: "high", 2: "medium", 1: "low"}[max_risk]

    result = {
        "commit_quality": all_quality,
        "changelog": {"added": all_added, "changed": all_changed, "removed": all_removed},
        "risk_assessment": {"level": final_risk, "concerns": all_concerns},
        "summary": f"Analyzed {len(commits)} commits. Risk: {final_risk}."
    }
    add_history(conn, job_id=job_id, feature="commit_analysis", source_ref=repo_ref,
                language=None, summary=result["summary"])
    return result
