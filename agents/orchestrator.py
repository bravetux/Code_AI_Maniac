import traceback
import duckdb
from db.queries.jobs import get_job, update_job_status, save_job_results
from db.queries.job_events import add_event
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
from tools.language_detect import detect_language
from config.settings import get_settings
from config.prompt_templates import apply_template


def _fetch_files(job: dict) -> list[dict]:
    """
    Return a list of file dicts, each with keys:
        file_path, content, file_hash
    For local multi-file source_ref (paths joined by '::') returns one entry per file.
    For GitHub/Gitea always returns exactly one entry.
    """
    s = get_settings()
    source_type = job["source_type"]
    source_ref  = job["source_ref"]

    if source_type == "local":
        # Multi-file: paths joined by '::'
        paths = source_ref.split("::") if "::" in source_ref else [source_ref]
        files = []
        errors = []
        for p in paths:
            r = fetch_local_file(p)
            if "error" in r:
                errors.append(r["error"])
            else:
                files.append({"file_path": p, "content": r["content"],
                               "file_hash": r["file_hash"]})
        if errors and not files:
            raise RuntimeError("; ".join(errors))
        if errors:
            # Some files failed — surface as a warning but continue with successful ones
            print(f"[WARN] Could not read {len(errors)} file(s): {errors[:3]}")
        return files

    elif source_type == "github":
        parts  = source_ref.split("::")   # owner/repo :: branch :: path
        token  = s.github_token
        try:
            import streamlit as st
            token = st.session_state.get("github_token_override", token)
        except Exception:
            pass
        result = fetch_github_file(repo=parts[0], file_path=parts[2],
                                   branch=parts[1], token=token or None)
        if "error" in result:
            raise RuntimeError(result["error"])
        return [{"file_path": parts[2], "content": result["content"],
                 "file_hash": result["file_hash"]}]

    elif source_type == "gitea":
        parts  = source_ref.split("::")   # owner/repo :: branch :: path
        result = fetch_gitea_file(gitea_url=s.gitea_url, repo=parts[0],
                                  file_path=parts[2], branch=parts[1],
                                  token=s.gitea_token)
        if "error" in result:
            raise RuntimeError(result["error"])
        return [{"file_path": parts[2], "content": result["content"],
                 "file_hash": result["file_hash"]}]

    else:
        raise ValueError(f"Unknown source type: {source_type}")


def _emit(conn, job_id, event_type, agent=None, file_path=None, message=None):
    """Fire-and-forget event; never raises so agent failures stay isolated."""
    try:
        add_event(conn, job_id, event_type, agent=agent,
                  file_path=file_path, message=message)
    except Exception:
        pass


def _run_agent(conn, job_id, agent_key, fn, file_path, kwargs,
               template_category=None) -> dict:
    """Run a single agent, emit start/cached/complete/error events, return result."""
    if template_category:
        kwargs = dict(kwargs)
        kwargs["custom_prompt"] = apply_template(
            template_category, agent_key, kwargs.get("custom_prompt")
        )
    _emit(conn, job_id, "start", agent=agent_key, file_path=file_path)
    try:
        result = fn(**kwargs)
        if result.get("_from_cache"):
            _emit(conn, job_id, "cached", agent=agent_key, file_path=file_path,
                  message=result.get("summary", ""))
        else:
            _emit(conn, job_id, "complete", agent=agent_key, file_path=file_path,
                  message=result.get("summary", ""))
        return result
    except Exception as e:
        _emit(conn, job_id, "error", agent=agent_key, file_path=file_path,
              message=str(e)[:120])
        return {"error": str(e)}


def _run_features_for_file(conn, job_id, file_info, features, language,
                            custom_prompt, template_category=None) -> dict:
    """Run all applicable features on a single file. Returns {feature: result}."""
    file_path  = file_info["file_path"]
    content    = file_info["content"]
    file_hash  = file_info["file_hash"]
    file_results = {}

    common = dict(conn=conn, job_id=job_id, file_path=file_path,
                  content=content, file_hash=file_hash,
                  language=language, custom_prompt=custom_prompt)

    feat_set = set(features)

    # ── Phase 1: foundation agents (no dependencies) ──────────────────────────
    phase1 = [f for f in ("bug_analysis", "static_analysis", "code_flow", "requirement")
              if f in feat_set]

    if phase1:
        _emit(conn, job_id, "phase", message="Phase 1 — Foundation")

    standalone = {
        "bug_analysis":    run_bug_analysis,
        "static_analysis": run_static_analysis,
        "code_flow":       run_code_flow,
        "requirement":     run_requirement_analysis,
    }

    for feat in phase1:
        file_results[feat] = _run_agent(conn, job_id, feat, standalone[feat],
                                        file_path, common, template_category)

    # ── Phase 2: context-aware agents ─────────────────────────────────────────
    phase2 = [f for f in ("code_design", "mermaid") if f in feat_set]
    if phase2:
        _emit(conn, job_id, "phase", message="Phase 2 — Context-Aware")

    if "code_design" in feat_set:
        file_results["code_design"] = _run_agent(
            conn, job_id, "code_design", run_code_design, file_path,
            {**common,
             "bug_results":    file_results.get("bug_analysis"),
             "static_results": file_results.get("static_analysis")},
            template_category,
        )

    if "mermaid" in feat_set:
        file_results["mermaid"] = _run_agent(
            conn, job_id, "mermaid", run_mermaid, file_path,
            {**common, "flow_context": file_results.get("code_flow")},
            template_category,
        )

    # ── Phase 3: synthesis agents ─────────────────────────────────────────────
    if "comment_generator" in feat_set:
        _emit(conn, job_id, "phase", message="Phase 3 — Synthesis")
        # comment_generator doesn't use raw content — pass filtered common
        common_no_content = {k: v for k, v in common.items() if k != "content"}
        file_results["comment_generator"] = _run_agent(
            conn, job_id, "comment_generator", run_comment_generation, file_path,
            {**common_no_content,
             "bug_results":    file_results.get("bug_analysis"),
             "static_results": file_results.get("static_analysis")},
            template_category,
        )

    return file_results


def _merge_multi_file_results(per_file: list[tuple[str, dict]],
                               features: list[str]) -> dict:
    """
    Combine per-file results into a single results dict.
    Each feature gets: {"_multi_file": True, "files": {path: result, ...}, "summary": "..."}
    """
    merged = {}
    for feature in features:
        if feature == "commit_analysis":
            continue  # not file-based
        files_data = {}
        for file_path, file_results in per_file:
            if feature in file_results:
                files_data[file_path] = file_results[feature]
        if files_data:
            merged[feature] = {
                "_multi_file": True,
                "files": files_data,
                "summary": f"{len(files_data)} file(s) analysed.",
            }
    return merged


def run_analysis(conn: duckdb.DuckDBPyConnection, job_id: str) -> dict:
    """
    Orchestrate all selected features for a job.
    Handles single-file and multi-file source refs.
    Returns dict of {feature_name: result}.
    """
    job = get_job(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    update_job_status(conn, job_id, "running")

    enabled  = get_settings().enabled_agent_set
    features = [f for f in (job["features"] or []) if f in enabled]
    language = job.get("language")
    custom_prompt = job.get("custom_prompt")
    template_category = job.get("template_category")
    results  = {}

    try:
        _emit(conn, job_id, "fetch", message="Fetching source files...")
        files = _fetch_files(job)
        fnames = ", ".join(f["file_path"].split("/")[-1] for f in files[:3])
        _emit(conn, job_id, "fetch",
              message=f"Loaded {len(files)} file(s) — {fnames}"
                      + (" …" if len(files) > 3 else ""))

        if len(files) == 1:
            # ── Single file ───────────────────────────────────────────────
            effective_lang = language or detect_language(files[0]["file_path"])
            results = _run_features_for_file(
                conn, job_id, files[0], features, effective_lang, custom_prompt,
                template_category,
            )
        else:
            # ── Multiple files ────────────────────────────────────────────
            per_file: list[tuple[str, dict]] = []
            for file_info in files:
                # Auto-detect per file — different files in a folder may differ
                effective_lang = language or detect_language(file_info["file_path"])
                file_results = _run_features_for_file(
                    conn, job_id, file_info, features, effective_lang, custom_prompt,
                    template_category,
                )
                per_file.append((file_info["file_path"], file_results))
            results = _merge_multi_file_results(per_file, features)

        save_job_results(conn, job_id, results)
        update_job_status(conn, job_id, "completed")

    except Exception as e:
        results["error"] = str(e)
        traceback.print_exc()
        save_job_results(conn, job_id, results)
        update_job_status(conn, job_id, "failed")

    return results
