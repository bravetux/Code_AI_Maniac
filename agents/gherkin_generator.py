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

"""F3 — BDD / Gherkin Feature File Generator.

Shares the spec-ingestion pipeline with F2. Emits two outputs:
- `.feature` file in Cucumber syntax
- `.robot` suite in Robot Framework syntax
"""

import os
import re
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.spec_fetcher import fetch_spec, SpecFetchError
from db.queries.history import add_history

_CACHE_KEY = "gherkin_generator"


_SYSTEM_PROMPT = """You are a BDD specialist. Given a user story or requirement,
generate BOTH:

1. A Cucumber `.feature` file with:
   - Feature heading
   - Background section when shared preconditions exist
   - One Scenario per acceptance criterion (happy path)
   - Scenario Outline with Examples table when the behaviour is data-driven
   - Additional Scenarios for key negative cases
   - Tags such as @smoke, @regression, @negative, @nfr where appropriate

2. A Robot Framework `.robot` test suite that mirrors the same scenarios
   using *** Settings ***, *** Variables ***, *** Test Cases ***, and
   *** Keywords *** sections. Use SeleniumLibrary-style keywords when the
   story is UI-facing, RequestsLibrary-style when it is API-facing.

Return EXACTLY two fenced blocks, in this order and with these exact fence tags:

```gherkin
<complete .feature file>
```

```robotframework
<complete .robot file>
```

Do not include any other prose.
"""


def _extract_block(text: str, fence: str) -> str:
    m = re.search(rf"```{re.escape(fence)}\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def run_gherkin_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                          file_path: str, content: str, file_hash: str,
                          language: str | None, custom_prompt: str | None,
                          **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    try:
        spec = fetch_spec(content)
    except SpecFetchError as e:
        raise RuntimeError(f"Spec fetch failed: {e}")

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    prompt = (f"Generate Gherkin and Robot Framework tests for:\n\n"
              f"Title: {spec['title']}\n"
              f"Source: {spec['source']} (provider={spec['provider']})\n\n"
              f"---\n{spec['body']}\n---")
    raw = str(agent(prompt))

    feature = _extract_block(raw, "gherkin") or _extract_block(raw, "feature")
    robot = _extract_block(raw, "robotframework") or _extract_block(raw, "robot")

    if not feature and not robot:
        # Fallback: treat the whole response as the feature file.
        feature = raw.strip()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "bdd")
    os.makedirs(out_dir, exist_ok=True)
    label = (os.path.basename(file_path) or "story").replace("/", "_")[:80] or "story"
    label = re.sub(r"[^\w\-]+", "_", label).strip("_") or "story"

    feature_path = os.path.join(out_dir, f"{label}.feature")
    robot_path = os.path.join(out_dir, f"{label}.robot")
    if feature:
        with open(feature_path, "w", encoding="utf-8") as fh:
            fh.write(feature)
    if robot:
        with open(robot_path, "w", encoding="utf-8") as fh:
            fh.write(robot)

    scenario_count = len(re.findall(r"^\s*Scenario( Outline)?:", feature or "", re.MULTILINE))

    md_parts = [
        f"## Gherkin / BDD — {spec.get('title', 'story')}",
        f"- **Provider:** {spec['provider']}",
        f"- **Source:** `{spec['source']}`",
        f"- **Scenarios:** {scenario_count}",
        f"- **Saved:** `{feature_path}`, `{robot_path}`\n",
    ]
    if feature:
        md_parts += ["### `.feature`", f"```gherkin\n{feature}\n```"]
    if robot:
        md_parts += ["### `.robot`", f"```robotframework\n{robot}\n```"]

    markdown = "\n".join(md_parts)
    summary = f"Generated {scenario_count} scenario(s) + Robot suite from {spec['provider']} story."

    result = {
        "markdown": markdown,
        "summary": summary,
        "feature_file": feature,
        "robot_file": robot,
        "feature_path": feature_path,
        "robot_path": robot_path,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
