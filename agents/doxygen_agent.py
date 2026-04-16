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
import re
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.run_doxygen import run_doxygen_tool
from db.queries.history import add_history

_CACHE_KEY = "doxygen"

_SYSTEM_PROMPT = """You are a senior C/C++ developer and documentation expert.
Your task is to add Doxygen-format documentation headers to every documentable
symbol in the provided source code.

Rules:
1. Add a @file block at the very top of the file with @brief, @author, and @date.
2. Add a documentation block before every:
   - Function / method definition or declaration
   - Struct / class / union / enum definition
   - Typedef
   - Important macros (#define)
3. Use the standard Doxygen comment style:
   /**
    * @brief  Short description.
    *
    * Detailed description (if warranted).
    *
    * @param  name  Description of parameter.
    * @return Description of return value.
    */
4. Use these tags where appropriate:
   @brief, @param, @return, @retval, @note, @warning, @see, @todo,
   @pre, @post, @throws, @deprecated
5. For structs/classes, document each member field with ///< inline comments
   or a preceding /** @brief */ block.
6. DO NOT change any existing code — only INSERT comment blocks.
   The original code must remain byte-for-byte identical.
7. DO NOT add comments to #include lines, blank lines, or trivial things.
8. Return the COMPLETE file content with all your added documentation.
   Do not truncate, summarise, or use ellipsis.

Return the full annotated source code wrapped in a single code fence:
```c
<complete file with doxygen comments>
```
"""


def _extract_code_block(text: str) -> str:
    """Extract the first code fence from the LLM response."""
    pattern = r"```(?:c|cpp|h|hpp|cs|cxx)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: if no code fence, return the raw text
    return text.strip()


def run_doxygen(conn: duckdb.DuckDBPyConnection, job_id: str,
                file_path: str, content: str, file_hash: str,
                language: str | None, custom_prompt: str | None,
                **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = (f"Add Doxygen documentation headers to this code{lang_hint}:\n\n"
              f"File: {file_path}\n\n```\n{content}\n```")
    raw_response = str(agent(prompt))
    annotated_code = _extract_code_block(raw_response)

    # ── Save annotated source to Reports/ ────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.join("Reports", ts, "doxygen")
    source_dir = os.path.join(base_dir, "sources")
    os.makedirs(source_dir, exist_ok=True)

    filename = os.path.basename(file_path) or "source.c"
    annotated_path = os.path.join(source_dir, filename)
    with open(annotated_path, "w", encoding="utf-8") as fh:
        fh.write(annotated_code)

    # ── Run doxygen CLI ──────────────────────────────────────────────────
    project_name = os.path.splitext(filename)[0]
    doxy_result = run_doxygen_tool(source_dir, base_dir, project_name)

    # ── Build markdown result ────────────────────────────────────────────
    md_parts = [f"## Doxygen Documentation — `{filename}`\n"]

    if doxy_result["success"]:
        html_path = doxy_result["output_path"].replace("\\", "/")
        md_parts.append(f"Doxygen HTML generated at: `{html_path}`\n")
    elif doxy_result["error"]:
        md_parts.append(f"**Doxygen CLI:** {doxy_result['error']}\n")

    md_parts.append(f"Annotated source saved to: `{annotated_path}`\n")
    md_parts.append("### Annotated Source\n")
    md_parts.append(f"```c\n{annotated_code}\n```")

    markdown = "\n".join(md_parts)
    summary = f"Added Doxygen headers to {filename}."
    if doxy_result["success"]:
        summary += " HTML docs generated."

    result = {
        "markdown": markdown,
        "summary": summary,
        "annotated_code": annotated_code,
        "doxygen_output_path": doxy_result.get("output_path", ""),
        "doxygen_ran": doxy_result["success"],
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
