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

"""F1 — Multi-language Unit Test Generator.

Extends the C test generator pattern to Python, JavaScript, TypeScript, Java,
.NET (C#), Kotlin, Swift, and ABAP. A per-language framework map picks the
idiomatic test framework. Reuses fetch/cache/history without modifying them.
"""

import os
import re
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "unit_test_generator"


# Language → (framework, test-file suffix, fence tag, idiomatic conventions)
_LANG_MAP: dict[str, dict] = {
    "python":     {"framework": "pytest",          "suffix": "test_{stem}.py",   "fence": "python",     "mock": "unittest.mock"},
    "javascript": {"framework": "Jest",            "suffix": "{stem}.test.js",   "fence": "javascript", "mock": "jest.mock"},
    "typescript": {"framework": "Jest + ts-jest",  "suffix": "{stem}.test.ts",   "fence": "typescript", "mock": "jest.mock"},
    "java":       {"framework": "JUnit 5 + Mockito","suffix": "{Stem}Test.java", "fence": "java",       "mock": "Mockito"},
    "kotlin":     {"framework": "JUnit 5 + MockK", "suffix": "{Stem}Test.kt",    "fence": "kotlin",     "mock": "MockK"},
    "csharp":     {"framework": "xUnit + Moq",     "suffix": "{Stem}Tests.cs",   "fence": "csharp",     "mock": "Moq"},
    "c#":         {"framework": "xUnit + Moq",     "suffix": "{Stem}Tests.cs",   "fence": "csharp",     "mock": "Moq"},
    ".net":       {"framework": "xUnit + Moq",     "suffix": "{Stem}Tests.cs",   "fence": "csharp",     "mock": "Moq"},
    "swift":      {"framework": "XCTest",          "suffix": "{Stem}Tests.swift","fence": "swift",      "mock": "protocol-based doubles"},
    "abap":       {"framework": "ABAP Unit",       "suffix": "z{stem}_test.abap","fence": "abap",       "mock": "Test Double Framework"},
    "go":         {"framework": "testing + testify","suffix": "{stem}_test.go",  "fence": "go",         "mock": "testify/mock"},
    "ruby":       {"framework": "RSpec",           "suffix": "{stem}_spec.rb",   "fence": "ruby",       "mock": "RSpec doubles"},
    "php":        {"framework": "PHPUnit",         "suffix": "{Stem}Test.php",   "fence": "php",        "mock": "PHPUnit mocks"},
}


_SYSTEM_PROMPT_TEMPLATE = """You are a senior test engineer specialising in {language} with deep expertise in {framework}.

Generate a COMPLETE, runnable test file for the provided source code. Follow these rules:

1. Pick the idiomatic layout for {framework}. Use standard imports, fixtures/setup, and teardown where appropriate.
2. For every public function / method / class, produce multiple test cases:
   - happy path
   - boundary values (min, max, empty, zero)
   - negative / invalid input
   - error propagation and exception handling
   - null / None / undefined where the language permits it
3. Parameterise where the framework supports it (pytest.mark.parametrize, JUnit @ParameterizedTest, xUnit [Theory], Jest .each, etc.).
4. Mock external collaborators (DB, HTTP, filesystem, time) using {mock_library}. Keep tests hermetic and fast.
5. Prefer AAA (Arrange / Act / Assert) structure and name tests after the behaviour they verify.
6. Do NOT invent module/file paths — import from the same package as the source file. If the import path is ambiguous, leave a single TODO comment at the top.
7. Keep dependencies minimal — only what the framework itself needs.
8. Add brief comments where the intent of the assertion isn't obvious from the code.

Return ONLY the complete test file, wrapped in a single fenced block:
```{fence}
<complete test file here>
```
"""


def _build_system_prompt(language: str) -> tuple[str, dict]:
    key = (language or "").strip().lower()
    meta = _LANG_MAP.get(key) or _LANG_MAP.get(key.replace(" ", ""))
    if meta is None:
        # Sensible fallback — let the model pick the framework.
        meta = {"framework": "the idiomatic unit-test framework",
                "suffix": "{stem}_test.txt",
                "fence": key or "text",
                "mock": "the idiomatic mocking library"}
    prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        language=language or "the source language",
        framework=meta["framework"],
        mock_library=meta["mock"],
        fence=meta["fence"],
    )
    return prompt, meta


def _extract_code_block(text: str, fence: str) -> str:
    pat = rf"```{re.escape(fence)}\s*\n(.*?)```"
    m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _format_suffix(suffix: str, basename: str) -> str:
    stem = os.path.splitext(basename or "source")[0] or "source"
    # Pascal-case for {Stem}; lower for {stem}
    pascal = "".join(p[:1].upper() + p[1:] for p in re.split(r"[_\-\s]+", stem) if p) or stem
    return suffix.replace("{stem}", stem).replace("{Stem}", pascal)


def run_unit_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    base_prompt, meta = _build_system_prompt(language or "")
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, base_prompt))

    prompt = (f"Generate a {meta['framework']} test file for this source:\n\n"
              f"File: {file_path}\nLanguage: {language or 'auto'}\n\n"
              f"```\n{content}\n```")
    raw = str(agent(prompt))
    test_code = _extract_code_block(raw, meta["fence"])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = os.path.join("Reports", ts, "unit_tests")
    os.makedirs(test_dir, exist_ok=True)

    basename = os.path.basename(file_path) or "source"
    test_filename = _format_suffix(meta["suffix"], basename)
    test_path = os.path.join(test_dir, test_filename)
    with open(test_path, "w", encoding="utf-8") as fh:
        fh.write(test_code)

    # Rough test-case count across common frameworks.
    patterns = [
        r"\bdef\s+test_",            # pytest / unittest
        r"@Test\b",                  # JUnit
        r"\[Fact\]|\[Theory\]",      # xUnit
        r"\bit\s*\(",                # Jest / Mocha / RSpec
        r"\btest\s*\(",              # Jest test()
        r"\bfunc\s+Test[A-Z]",       # Go
        r"\bMETHOD\s+test_",         # ABAP Unit
    ]
    test_count = sum(len(re.findall(p, test_code)) for p in patterns)

    md_parts = [
        f"## Unit Test Generator — `{basename}`\n",
        f"- **Language:** {language or 'auto-detected'}",
        f"- **Framework:** {meta['framework']}",
        f"- **Mocking:** {meta['mock']}",
        f"- **Test cases generated:** {test_count or 'n/a'}",
        f"- **Saved to:** `{test_path}`\n",
        "### Generated Test File",
        f"```{meta['fence']}\n{test_code}\n```",
    ]
    markdown = "\n".join(md_parts)
    summary = (f"Generated {test_count} {meta['framework']} test(s) for "
               f"{basename}." if test_count
               else f"Generated {meta['framework']} tests for {basename}.")

    result = {
        "markdown": markdown,
        "summary": summary,
        "test_code": test_code,
        "output_path": test_path,
        "framework": meta["framework"],
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
