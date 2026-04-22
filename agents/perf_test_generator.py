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
# Developed: 22nd April 2026

"""F6 — Performance / Load Test Script Generator.

Mode detection (spec vs. requirements) runs first. Framework auto-pick
drives one Strands LLM call with a framework-specific prompt;
tools.load_profile_builder supplies fixed load constants so the LLM
does not hallucinate timings.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.openapi_parser import parse, extract_endpoints, OpenAPIParseError
from tools.load_profile_builder import build_profile
from db.queries.history import add_history

_CACHE_KEY = "perf_test_generator"

_METADATA_PATHS = {"/health", "/healthz", "/metrics", "/livez", "/readyz",
                   "/ready", "/live", "/status"}

_YAML_SNIFF = re.compile(r"^\s*(openapi|swagger)\s*:", re.IGNORECASE | re.MULTILINE)


def _detect_mode(file_path: str, content: str, custom_prompt: str | None) -> str:
    """Return 'spec' or 'requirements'."""
    if custom_prompt:
        if "__mode__requirements\n" in custom_prompt:
            return "requirements"
        if "__openapi_spec__\n" in custom_prompt:
            return "spec"
    ext = os.path.splitext(file_path)[1].lower()
    head = (content or "")[:1024]
    if ext in (".yaml", ".yml") and _YAML_SNIFF.search(head):
        return "spec"
    if ext == ".json" and ('"openapi"' in head or '"swagger"' in head):
        return "spec"
    return "requirements"


_GATLING_LANGS = {"java", "scala", "gatling"}


def _pick_framework(language: str | None) -> str:
    """Return 'gatling' or 'jmeter'."""
    if language and language.strip().lower() in _GATLING_LANGS:
        return "gatling"
    return "jmeter"


_JMETER_SYSTEM = """You are a performance engineer. Produce a COMPLETE, runnable Apache JMeter 5.x test plan (.jmx XML) for the API below.

Mandatory structure:
- <jmeterTestPlan version="1.2" properties="5.0"> root with <hashTree> children
- Exactly one TestPlan
- Exactly one ThreadGroup with:
    * num_threads      = {virtual_users}
    * ramp_time        = {ramp_up_seconds}
    * duration         = {steady_state_seconds}
    * scheduler        = true
- One TransactionController per endpoint
- One HTTPSamplerProxy per endpoint inside its TransactionController, using ${{baseUrl}} via a User Defined Variables block
- One ResponseAssertion per sampler checking response code starts with "2"
- One ConstantTimer with delay = {think_time_ms}
- SummaryReport and ViewResultsTree listeners attached at TestPlan level

Do not include any endpoint whose path is in: {metadata_paths}.

Return ONLY the complete plan wrapped in a single ```xml fenced block.

Endpoints:
{endpoint_table}

Title: {title}
"""

_GATLING_SYSTEM = """You are a performance engineer. Produce a COMPLETE, runnable Gatling 3.x Simulation.scala for the API below.

Mandatory structure:
- package-less file, class `LoadTest extends Simulation`
- `val httpProtocol = http.baseUrl("${{baseUrl}}")` — do NOT inline a real URL
- One `scenario("LoadTest")` chaining exec(http(...)) for every endpoint
- `.check(status.is(200))` or `.check(status.in(200 to 299))` per call
- `setUp(scn.inject(rampUsersPerSec(1) to ({target_rps}) during ({ramp_up_seconds} seconds)).protocols(httpProtocol))`
- `.maxDuration({steady_state_seconds} seconds)` on the setUp
- Insert `pause({think_time_ms} milliseconds)` between calls

Do not include any endpoint whose path is in: {metadata_paths}.

Return ONLY the complete Scala file wrapped in a single ```scala fenced block.

Endpoints:
{endpoint_table}

Title: {title}
"""

_STORY_NOTE = "\n\n(Requirements mode — no formal OpenAPI spec provided. Invent plausible REST paths consistent with the story.)"


def _endpoint_table(endpoints: list[dict]) -> str:
    lines = []
    for ep in endpoints:
        lines.append(f"- {ep['method']} {ep['path']}")
    return "\n".join(lines) or "(no endpoints — derive from narrative)"


def _filter_metadata(endpoints: list[dict]) -> list[dict]:
    return [ep for ep in endpoints if ep["path"] not in _METADATA_PATHS]


def _extract_code_block(text: str, fence: str) -> str:
    pat = rf"```{re.escape(fence)}\s*\n(.*?)```"
    m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_perf_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    mode = _detect_mode(file_path, content, custom_prompt)
    framework = _pick_framework(language)

    title = "api"
    endpoints: list[dict] = []
    if mode == "spec":
        if custom_prompt and "__openapi_spec__\n" in custom_prompt:
            spec_body = custom_prompt.split("__openapi_spec__\n", 1)[1]
        else:
            spec_body = content
        try:
            spec = parse(spec_body)
        except OpenAPIParseError as exc:
            return {
                "markdown": f"## Perf/Load Test Generator — error\n\n{exc}",
                "summary": f"F6 error: {exc}",
                "output_path": None,
            }
        title = (spec.get("info") or {}).get("title") or title
        endpoints = _filter_metadata(extract_endpoints(spec))

    profile = build_profile(num_endpoints=max(len(endpoints), 3), target="medium")

    if framework == "gatling":
        system = _GATLING_SYSTEM.format(
            virtual_users=profile["virtual_users"],
            ramp_up_seconds=profile["ramp_up_seconds"],
            steady_state_seconds=profile["steady_state_seconds"],
            think_time_ms=profile["think_time_ms"],
            target_rps=profile["target_rps"],
            metadata_paths=", ".join(sorted(_METADATA_PATHS)),
            endpoint_table=_endpoint_table(endpoints),
            title=title,
        )
    else:
        system = _JMETER_SYSTEM.format(
            virtual_users=profile["virtual_users"],
            ramp_up_seconds=profile["ramp_up_seconds"],
            steady_state_seconds=profile["steady_state_seconds"],
            think_time_ms=profile["think_time_ms"],
            target_rps=profile["target_rps"],
            metadata_paths=", ".join(sorted(_METADATA_PATHS)),
            endpoint_table=_endpoint_table(endpoints),
            title=title,
        )

    if mode == "requirements":
        system += _STORY_NOTE

    try:
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, system))
        user_prompt = (
            "Generate the performance test plan now using the endpoint list above."
            if mode == "spec"
            else f"Generate the performance test plan for this narrative:\n\n{content}"
        )
        raw = str(agent(user_prompt))
    except Exception as exc:  # pragma: no cover — network/LLM failure path
        return {
            "markdown": f"## Perf/Load Test Generator — error\n\n{exc}",
            "summary": f"F6 error: LLM invocation failed: {exc}",
            "output_path": None,
        }

    fence = "scala" if framework == "gatling" else "xml"
    body = _extract_code_block(raw, fence)

    ok = bool(body.strip())
    if framework == "jmeter" and "<jmeterTestPlan" not in body:
        ok = False
    if framework == "gatling" and "Simulation" not in body:
        ok = False

    if not ok:
        return {
            "markdown": "## Perf/Load Test Generator — LLM output empty/invalid",
            "summary": f"F6 error: LLM returned empty or invalid {framework} content",
            "output_path": None,
        }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "perf_tests")
    os.makedirs(out_dir, exist_ok=True)
    suffix = "Simulation.scala" if framework == "gatling" else "plan.jmx"
    output_path = os.path.join(out_dir, suffix)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(body)

    md_parts = [
        f"## Perf/Load Test Generator — `{title}`",
        f"- **Mode:** {mode}",
        f"- **Framework:** {framework}",
        f"- **Endpoints:** {len(endpoints)}" + (" (from narrative)" if mode == "requirements" else ""),
        f"- **Load profile:** {profile['virtual_users']} VUs, "
        f"{profile['ramp_up_seconds']}s ramp, "
        f"{profile['steady_state_seconds']}s steady, "
        f"{profile['think_time_ms']}ms think, "
        f"~{profile['target_rps']} rps",
        f"- **Output:** `{output_path}`",
        f"\n### Generated plan\n\n```{fence}\n{body}\n```",
    ]
    markdown = "\n".join(md_parts)
    summary = f"Generated {framework} plan ({mode} mode) for {len(endpoints) or 'story-derived'} endpoints."

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": output_path,
        "framework": framework,
        "mode": mode,
        "profile": profile,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
