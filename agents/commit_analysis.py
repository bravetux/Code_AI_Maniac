import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior engineering lead reviewing a git commit history before a release.

Write a thorough, honest commit history review as you would present it to the team in a retro or
release readiness meeting. Use markdown with clear sections.

Cover:

## Commit Quality
For each commit: was the message clear and atomic? Mixed concerns? Good practice examples?
Don't just rate them — explain your reasoning with specific examples from the messages.

## Changelog
What was actually built, changed, or removed? Write this as a proper changelog, not a list of
commit messages — synthesise across commits to describe features/fixes at the right level of abstraction.

## Risk Assessment
What is the overall release risk? Call out:
- Large or complex changesets
- Areas with many changes (churn — often where bugs hide)
- Missing tests or documentation signals
- Patterns of concern (many fixup commits, unclear messages suggesting rushed work)
- Any commits that look risky for production

## Recommendations
What should the team do before releasing? What should they improve in their commit hygiene?"""


def run_commit_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                        repo_ref: str, commits: list[dict],
                        custom_prompt: str | None) -> dict:
    if not commits:
        return {
            "markdown": "No commits provided for analysis.",
            "summary": "No commits to analyze.",
            "risk_level": "low",
        }

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    batch_size = 20
    section_docs = []

    for i in range(0, len(commits), batch_size):
        batch = commits[i:i + batch_size]
        prompt = (f"Repository: {repo_ref}\n"
                  f"Commits {i + 1}–{i + len(batch)} of {len(commits)}:\n"
                  + json.dumps(batch, indent=2))
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You have reviewed {len(commits)} commits from {repo_ref} in batches. "
            "Synthesise the batch analyses below into one cohesive commit history review. "
            "Produce a single Risk Assessment and a single Changelog that covers all commits.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    # Extract risk level from the text for structured use
    text_lower = markdown.lower()
    if "high risk" in text_lower or "**high**" in text_lower:
        risk_level = "high"
    elif "medium risk" in text_lower or "**medium**" in text_lower:
        risk_level = "medium"
    else:
        risk_level = "low"

    summary = f"Analysed {len(commits)} commits from {repo_ref}. Risk: {risk_level}."
    result = {
        "markdown": markdown,
        "summary": summary,
        "risk_level": risk_level,
    }
    add_history(conn, job_id=job_id, feature="commit_analysis", source_ref=repo_ref,
                language=None, summary=summary)
    return result
