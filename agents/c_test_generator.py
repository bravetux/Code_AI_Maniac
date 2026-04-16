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
from db.queries.history import add_history

_CACHE_KEY = "c_test_generator"

_SYSTEM_PROMPT = """You are a C/Python integration testing expert.
Given C source code, generate a complete Python pytest test file that uses `ctypes`
to load the compiled shared library and test every public function.

Follow these rules:

1. Start with a build instruction comment:
   # Build: gcc -shared -fPIC -o <name>.so <name>.c
   # Windows: cl /LD <name>.c /Fe<name>.dll

2. Import section:
   import pytest
   import ctypes
   import os
   from ctypes import c_int, c_float, c_double, c_char_p, c_void_p, POINTER, Structure, ...

3. Library loading:
   _LIB_PATH = os.path.join(os.path.dirname(__file__), '..', '<name>.so')
   _lib = ctypes.CDLL(_LIB_PATH)

4. For EVERY public function, define type-safe bindings:
   _lib.<func>.argtypes = [c_int, c_int]
   _lib.<func>.restype = c_int

5. For structs, define ctypes.Structure subclasses with _fields_.

6. Generate one test class per public function:
   class TestFunctionName:
       def test_happy_path(self): ...
       def test_boundary_values(self): ...
       def test_negative_input(self): ...
       def test_zero_input(self): ...
       def test_large_input(self): ...
       def test_null_pointer(self): ...  # if applicable
       def test_error_return(self): ...  # if function has error codes

7. For pointer parameters:
   - Create and pass ctypes pointers
   - Test NULL pointer handling
   - Test buffer overflow scenarios where relevant

8. For string parameters:
   - Use c_char_p with b"string" byte literals
   - Test empty strings, long strings, special characters

9. Include a conftest.py-style fixture if the library needs setup:
   @pytest.fixture(scope="module")
   def lib():
       return ctypes.CDLL(...)

10. Add a __main__ block:
    if __name__ == "__main__":
        pytest.main([__file__, "-v"])

Generate thorough tests — aim for 3-8 test methods per function depending on complexity.
Include comments explaining what each test validates.

Return the COMPLETE test file wrapped in a single code fence:
```python
<complete test file>
```
"""


def _extract_python_block(text: str) -> str:
    """Extract the first Python code fence from the LLM response."""
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: try any code fence
    match = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def run_c_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                         file_path: str, content: str, file_hash: str,
                         language: str | None, custom_prompt: str | None,
                         **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    prompt = (f"Generate a Python pytest + ctypes test file for this C code:\n\n"
              f"File: {file_path}\n\n```c\n{content}\n```")
    raw_response = str(agent(prompt))
    test_code = _extract_python_block(raw_response)

    # ── Save test file to Reports/ ───────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = os.path.join("Reports", ts, "c_tests")
    os.makedirs(test_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(file_path) or "source")[0]
    test_filename = f"test_{base_name}.py"
    test_path = os.path.join(test_dir, test_filename)
    with open(test_path, "w", encoding="utf-8") as fh:
        fh.write(test_code)

    # ── Count test methods for summary ───────────────────────────────────
    test_count = len(re.findall(r"def test_", test_code))

    # ── Build markdown ───────────────────────────────────────────────────
    md_parts = [
        f"## C Test Generator — `{os.path.basename(file_path)}`\n",
        f"Generated **{test_count}** test cases using `pytest` + `ctypes`.\n",
        f"Test file saved to: `{test_path}`\n",
        "### Generated Test File\n",
        f"```python\n{test_code}\n```",
    ]
    markdown = "\n".join(md_parts)
    summary = f"Generated {test_count} pytest+ctypes tests for {os.path.basename(file_path)}."

    result = {
        "markdown": markdown,
        "summary": summary,
        "test_code": test_code,
        "output_path": test_path,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
