import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a technical writer preparing release notes from a git commit history.

Your job is to transform raw commit messages into polished, user-facing release notes that a
product team or end-users would read. Do NOT simply reformat the commit messages — synthesise
them into meaningful, grouped release notes.

Return your output in markdown with these sections:

# Release Notes

## Highlights
A short (2-4 bullet) executive summary of the most important changes in this release.

## New Features
Features or capabilities that were added. Group related commits into a single bullet.
Skip this section if there are none.

## Improvements
Enhancements to existing functionality, performance improvements, UX polish, refactors
that improve developer experience. Skip if none.

## Bug Fixes
Bugs that were fixed. Describe what was broken and that it is now resolved.
Skip if none.

## Breaking Changes
Any changes that could break existing workflows, APIs, or configurations.
Skip if none.

## Other Changes
Documentation updates, dependency bumps, CI/CD changes, chores, and anything
that doesn't fit the categories above. Skip if none.

Guidelines:
- Write from the user's perspective, not the developer's
- Each bullet should be one clear sentence
- Group related commits into a single bullet rather than listing each commit separately
- Omit commit SHAs from the notes (they are implementation details)
- Use past tense ("Added", "Fixed", "Improved")
- If a commit message is unclear, make a reasonable inference from context
- Be concise — release notes should be scannable"""


def run_release_notes(conn: duckdb.DuckDBPyConnection, job_id: str,
                      repo_ref: str, commits: list[dict],
                      custom_prompt: str | None) -> dict:
    if not commits:
        return {
            "markdown": "No commits provided for release notes.",
            "summary": "No commits to process.",
        }

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    batch_size = 30
    section_docs = []

    for i in range(0, len(commits), batch_size):
        batch = commits[i:i + batch_size]
        prompt = (f"Repository: {repo_ref}\n"
                  f"Commits {i + 1}–{i + len(batch)} of {len(commits)}:\n"
                  + json.dumps(batch, indent=2))
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You produced partial release notes for {len(commits)} commits from {repo_ref} "
            "in batches. Merge the partial notes below into a single, cohesive set of release "
            "notes. De-duplicate items that appear in multiple batches and keep the same section "
            "structure.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    summary = f"Generated release notes from {len(commits)} commits ({repo_ref})."
    result = {
        "markdown": markdown,
        "summary": summary,
    }
    add_history(conn, job_id=job_id, feature="release_notes", source_ref=repo_ref,
                language=None, summary=summary)
    return result
