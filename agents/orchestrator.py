# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

import os
import traceback
from datetime import datetime
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
from agents.dependency_analysis import run_dependency_analysis
from agents.code_complexity import run_code_complexity
from agents.test_coverage import run_test_coverage
from agents.duplication_detection import run_duplication_detection
from agents.performance_analysis import run_performance_analysis
from agents.type_safety import run_type_safety
from agents.architecture_mapper import run_architecture_mapper
from agents.license_compliance import run_license_compliance
from agents.change_impact import run_change_impact
from agents.refactoring_advisor import run_refactoring_advisor
from agents.api_doc_generator import run_api_doc_generator
from agents.doxygen_agent import run_doxygen
from agents.c_test_generator import run_c_test_generator
from agents.secret_scan import run_secret_scan
from agents.threat_model import run_threat_model
from agents.report_per_file import generate_per_file_report
from agents.report_consolidated import generate_consolidated_report
from tools.fetch_local import fetch_local_file
from tools.fetch_github import fetch_github_file
from tools.fetch_gitea import fetch_gitea_file
from tools.language_detect import detect_language
from tools.python_html_converter import convert_md_to_html
from tools.secret_scanner import scan_secrets
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
            template_category, agent_key, kwargs.get("custom_prompt"),
            language=kwargs.get("language"),
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
                            custom_prompt, template_category=None,
                            phase0_results=None, threat_model_mode=None) -> dict:
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
    phase1 = [f for f in ("bug_analysis", "static_analysis", "code_flow", "requirement",
                          "dependency_analysis", "code_complexity", "test_coverage",
                          "duplication_detection", "performance_analysis", "type_safety",
                          "architecture_mapper", "license_compliance", "change_impact",
                          "doxygen", "c_test_generator")
              if f in feat_set]

    if phase1:
        _emit(conn, job_id, "phase", message="Phase 1 — Foundation")

    standalone = {
        "bug_analysis":          run_bug_analysis,
        "static_analysis":       run_static_analysis,
        "code_flow":             run_code_flow,
        "requirement":           run_requirement_analysis,
        "dependency_analysis":   run_dependency_analysis,
        "code_complexity":       run_code_complexity,
        "test_coverage":         run_test_coverage,
        "duplication_detection": run_duplication_detection,
        "performance_analysis":  run_performance_analysis,
        "type_safety":           run_type_safety,
        "architecture_mapper":   run_architecture_mapper,
        "license_compliance":    run_license_compliance,
        "change_impact":         run_change_impact,
        "doxygen":               run_doxygen,
        "c_test_generator":      run_c_test_generator,
    }

    for feat in phase1:
        file_results[feat] = _run_agent(conn, job_id, feat, standalone[feat],
                                        file_path, common, template_category)

    # ── Phase 2: context-aware agents ─────────────────────────────────────────
    phase2 = [f for f in ("code_design", "mermaid", "refactoring_advisor", "api_doc_generator")
              if f in feat_set]
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

    if "refactoring_advisor" in feat_set:
        file_results["refactoring_advisor"] = _run_agent(
            conn, job_id, "refactoring_advisor", run_refactoring_advisor, file_path,
            {**common,
             "complexity_results":  file_results.get("code_complexity"),
             "static_results":      file_results.get("static_analysis"),
             "duplication_results": file_results.get("duplication_detection")},
            template_category,
        )

    if "api_doc_generator" in feat_set:
        file_results["api_doc_generator"] = _run_agent(
            conn, job_id, "api_doc_generator", run_api_doc_generator, file_path,
            {**common, "flow_context": file_results.get("code_flow")},
            template_category,
        )

    # ── Phase 3: synthesis agents ─────────────────────────────────────────────
    phase3 = [f for f in ("comment_generator", "secret_scan") if f in feat_set]
    if phase3:
        _emit(conn, job_id, "phase", message="Phase 3 — Synthesis")

    if "comment_generator" in feat_set:
        # comment_generator doesn't use raw content — pass filtered common
        common_no_content = {k: v for k, v in common.items() if k != "content"}
        file_results["comment_generator"] = _run_agent(
            conn, job_id, "comment_generator", run_comment_generation, file_path,
            {**common_no_content,
             "bug_results":    file_results.get("bug_analysis"),
             "static_results": file_results.get("static_analysis")},
            template_category,
        )

    if "secret_scan" in feat_set:
        file_results["secret_scan"] = _run_agent(
            conn, job_id, "secret_scan", run_secret_scan, file_path,
            {**common,
             "phase0_findings": (phase0_results or {}).get(file_path, {}).get("secrets_found", []),
             "static_results": file_results.get("static_analysis")},
            template_category,
        )

    # ── Phase 4: threat model ────────────────────────────────────────────
    if "threat_model" in feat_set:
        _emit(conn, job_id, "phase", message="Phase 4 — Threat Model")
        file_results["threat_model"] = _run_agent(
            conn, job_id, "threat_model", run_threat_model, file_path,
            {**common,
             "threat_model_mode": threat_model_mode,
             "bug_results": file_results.get("bug_analysis"),
             "static_results": file_results.get("static_analysis"),
             "secret_results": file_results.get("secret_scan"),
             "dependency_results": file_results.get("dependency_analysis")},
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


def _generate_reports(conn, job_id, per_file_data, features, language,
                      reports_dir, emit_fn) -> list[str]:
    """Phase 2: generate per-file and consolidated reports.
    Returns list of written file paths."""
    s = get_settings()
    written = []

    if not s.report_per_file and not s.report_consolidated:
        return written

    os.makedirs(reports_dir, exist_ok=True)
    per_file_dir = os.path.join(reports_dir, "per_file")
    per_file_reports = []

    # ── Per-file reports ─────────────────────────────────────────────────
    if s.report_per_file:
        os.makedirs(per_file_dir, exist_ok=True)
        for file_path, file_results in per_file_data:
            basename = os.path.basename(file_path) or "report"
            name_stem = os.path.splitext(basename)[0]
            emit_fn(conn, job_id, "report_start", agent="report_per_file",
                    file_path=file_path, message=f"Generating report for {basename}")

            md_content = generate_per_file_report(file_path, file_results, language)
            per_file_reports.append(md_content)

            if s.report_format_md:
                md_path = os.path.join(per_file_dir, f"{name_stem}.md")
                with open(md_path, "w", encoding="utf-8") as fh:
                    fh.write(md_content)
                written.append(md_path)

            if s.report_format_html:
                html_path = os.path.join(per_file_dir, f"{name_stem}.html")
                html_content = convert_md_to_html(md_content, title=f"Report — {basename}")
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(html_content)
                written.append(html_path)

            emit_fn(conn, job_id, "report_complete", agent="report_per_file",
                    file_path=file_path, message=f"Report saved for {basename}")

    # ── Consolidated report ──────────────────────────────────────────────
    if s.report_consolidated and per_file_data:
        emit_fn(conn, job_id, "report_start", agent="report_consolidated",
                message="Generating consolidated report")

        all_results = {fp: fr for fp, fr in per_file_data}
        file_paths = [fp for fp, _ in per_file_data]

        md_content = generate_consolidated_report(
            per_file_reports=per_file_reports,
            all_results=all_results,
            file_paths=file_paths,
            features=[f for f in features if f != "commit_analysis"],
            language=language,
            mode=s.consolidated_mode,
        )

        if s.report_format_md:
            md_path = os.path.join(reports_dir, "consolidated_report.md")
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(md_content)
            written.append(md_path)

        if s.report_format_html:
            html_path = os.path.join(reports_dir, "consolidated_report.html")
            html_content = convert_md_to_html(md_content, title="Consolidated Analysis Report")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            written.append(html_path)

        emit_fn(conn, job_id, "report_complete", agent="report_consolidated",
                message=f"Consolidated report saved ({len(file_paths)} files)")

    return written


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

        # ── Phase 0: Pre-flight secret scan ──────────────────────────────
        s = get_settings()
        feat_set = set(features)
        phase0_results = {}
        if "secret_scan" in feat_set:
            _emit(conn, job_id, "phase", message="Phase 0 — Secret Pre-flight")
            for file_info in files:
                scan = scan_secrets(file_info["content"], mode=s.secret_scan_mode)
                phase0_results[file_info["file_path"]] = scan
                if scan["secrets_found"]:
                    _emit(conn, job_id, "start", agent="secret_scan_preflight",
                          file_path=file_info["file_path"],
                          message=f"{len(scan['secrets_found'])} secret(s) detected")
                if scan["action_taken"] == "redact":
                    file_info["content"] = scan["code"]
                elif scan["action_taken"] == "block" and scan["secrets_found"]:
                    results["secret_scan_preflight"] = scan
                    save_job_results(conn, job_id, results)
                    update_job_status(conn, job_id, "blocked")
                    return results

        if len(files) == 1:
            # ── Single file ───────────────────────────────────────────────
            effective_lang = language or detect_language(files[0]["file_path"])
            results = _run_features_for_file(
                conn, job_id, files[0], features, effective_lang, custom_prompt,
                template_category,
                phase0_results=phase0_results,
                threat_model_mode=job.get("threat_model_mode"),
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
                    phase0_results=phase0_results,
                    threat_model_mode=job.get("threat_model_mode"),
                )
                per_file.append((file_info["file_path"], file_results))
            results = _merge_multi_file_results(per_file, features)

        save_job_results(conn, job_id, results)
        update_job_status(conn, job_id, "completed")

        # ── Phase 2: Report generation ───────────────────────────────────
        if len(files) == 1:
            _per_file_data = [(files[0]["file_path"], results)]
        else:
            _per_file_data = per_file

        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = os.path.join("Reports", ts)
            saved = _generate_reports(
                conn, job_id, _per_file_data, features,
                language or detect_language(files[0]["file_path"]),
                reports_dir, _emit,
            )
            if saved:
                _emit(conn, job_id, "report_complete",
                      message=f"Saved {len(saved)} report file(s) to Reports/")
        except Exception:
            pass  # non-critical — don't fail the job

    except Exception as e:
        results["error"] = str(e)
        traceback.print_exc()
        save_job_results(conn, job_id, results)
        update_job_status(conn, job_id, "failed")

    return results
