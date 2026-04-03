import concurrent.futures
import duckdb
from db.queries.jobs import get_job, update_job_status
from agents.bug_analysis import run_bug_analysis
from agents.code_design import run_code_design
from agents.code_flow import run_code_flow
from agents.mermaid import run_mermaid
from agents.requirement import run_requirement_analysis
from agents.static_analysis import run_static_analysis
from agents.comment_generator import run_comment_generation
from agents.commit_analysis import run_commit_analysis
from tools.fetch_local import fetch_local_file
from tools.fetch_github import fetch_github_file
from tools.fetch_gitea import fetch_gitea_file
from config.settings import get_settings


def _fetch_content(job: dict) -> tuple[str, str]:
    """Fetch file content and return (content, file_hash)."""
    s = get_settings()
    source_type = job["source_type"]
    source_ref = job["source_ref"]

    if source_type == "local":
        result = fetch_local_file(source_ref)
    elif source_type == "github":
        # source_ref format: "owner/repo::branch::path"
        parts = source_ref.split("::")
        result = fetch_github_file(repo=parts[0], file_path=parts[2],
                                   branch=parts[1], token=s.github_token)
    elif source_type == "gitea":
        # source_ref format: "owner/repo::branch::path"
        parts = source_ref.split("::")
        result = fetch_gitea_file(gitea_url=s.gitea_url, repo=parts[0],
                                  file_path=parts[2], branch=parts[1],
                                  token=s.gitea_token)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    if "error" in result:
        raise RuntimeError(result["error"])
    return result["content"], result["file_hash"]


def run_analysis(conn: duckdb.DuckDBPyConnection, job_id: str) -> dict:
    """
    Orchestrate all selected features for a job.
    Independent features run in parallel; dependent features run after.
    Returns dict of {feature_name: result}.
    """
    job = get_job(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    update_job_status(conn, job_id, "running")
    features = job["features"] or []
    language = job.get("language")
    custom_prompt = job.get("custom_prompt")
    results = {}

    # Built here so mocks in tests can patch individual agent functions
    independent_features = {
        "bug_analysis": run_bug_analysis,
        "code_design": run_code_design,
        "code_flow": run_code_flow,
        "requirement": run_requirement_analysis,
        "static_analysis": run_static_analysis,
    }

    try:
        content, file_hash = _fetch_content(job)
        source_ref = job["source_ref"]
        common_kwargs = dict(conn=conn, job_id=job_id, file_path=source_ref,
                             content=content, file_hash=file_hash,
                             language=language, custom_prompt=custom_prompt)

        # Run independent features in parallel
        independent = [f for f in features if f in independent_features]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(independent_features[f], **common_kwargs): f
                for f in independent
            }
            for future in concurrent.futures.as_completed(futures):
                feature = futures[future]
                try:
                    results[feature] = future.result()
                except Exception as e:
                    results[feature] = {"error": str(e)}

        # Mermaid: reuse code_flow if available
        if "mermaid" in features:
            mermaid_kwargs = dict(conn=conn, job_id=job_id, file_path=source_ref,
                                  content=content, file_hash=file_hash,
                                  language=language, custom_prompt=custom_prompt,
                                  flow_context=results.get("code_flow"))
            results["mermaid"] = run_mermaid(**mermaid_kwargs)

        # CommentGenerator: reuse bug + static results
        if "comment_generator" in features:
            results["comment_generator"] = run_comment_generation(
                conn=conn, job_id=job_id, file_path=source_ref,
                file_hash=file_hash, language=language, custom_prompt=custom_prompt,
                bug_results=results.get("bug_analysis"),
                static_results=results.get("static_analysis"),
            )

        update_job_status(conn, job_id, "completed")
    except Exception as e:
        update_job_status(conn, job_id, "failed")
        results["error"] = str(e)

    return results
