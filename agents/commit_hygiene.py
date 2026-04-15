import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a commit hygiene auditor reviewing a git commit history against
industry best practices and the Conventional Commits specification (https://www.conventionalcommits.org).

Produce a thorough markdown report with these sections:

## Compliance Summary
- Total commits analysed
- Number and percentage following Conventional Commits format (feat:, fix:, chore:, docs:,
  refactor:, test:, style:, perf:, ci:, build:, revert:)
- Overall hygiene grade: A (>90%), B (70-90%), C (50-70%), D (<50%)

## Convention Violations
List commits that do NOT follow Conventional Commits format. For each:
- SHA and original message
- What is wrong (missing type prefix, wrong format, etc.)
- Suggested rewrite

## Message Quality Issues
Flag commits with quality problems:
- Too short or vague (e.g. "fix", "update", "wip", "changes", "stuff")
- Too long (subject > 72 chars)
- No imperative mood in subject
- Missing body for complex changes
- Non-descriptive messages that make the history hard to read

## Squash Candidates
Identify chains of commits that should be squashed:
- Sequential "fixup" or "wip" commits
- Multiple commits with near-identical messages
- Rapid-fire tiny commits that represent a single logical change

## Large Commits
(Only if file change data is available — skip this section if not.)
Flag commits that modify many files (10+), as these are harder to review and more
likely to introduce issues.

## Recommendations
- Concrete, actionable suggestions for the team to improve commit hygiene
- Pre-commit hook suggestions (commitlint, etc.)
- Template recommendations

Guidelines:
- Be specific — cite SHAs and quote messages
- Be constructive, not condescending
- Prioritise the most impactful improvements"""


def run_commit_hygiene(conn: duckdb.DuckDBPyConnection, job_id: str,
                       repo_ref: str, commits: list[dict],
                       custom_prompt: str | None) -> dict:
    if not commits:
        return {
            "markdown": "No commits provided for hygiene audit.",
            "summary": "No commits to audit.",
        }

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    # Detect file data availability
    sample = commits[0] if commits else {}
    has_files = bool(sample.get("files_changed"))
    data_note = "" if has_files else "NOTE: File change lists are not available. Skip the Large Commits section.\n\n"

    batch_size = 20
    section_docs = []

    for i in range(0, len(commits), batch_size):
        batch = commits[i:i + batch_size]
        prompt = (data_note
                  + f"Repository: {repo_ref}\n"
                  f"Commits {i + 1}–{i + len(batch)} of {len(commits)}:\n"
                  + json.dumps(batch, indent=2))
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You audited {len(commits)} commits from {repo_ref} in batches. "
            "Merge the batch audits into one cohesive report. Recalculate the overall "
            "compliance percentage and grade across all commits. De-duplicate violations. "
            "Keep the same section structure.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    summary = f"Commit hygiene audit for {len(commits)} commits ({repo_ref})."
    result = {
        "markdown": markdown,
        "summary": summary,
    }
    add_history(conn, job_id=job_id, feature="commit_hygiene", source_ref=repo_ref,
                language=None, summary=summary)
    return result
