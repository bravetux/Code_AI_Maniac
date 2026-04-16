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

from tools.run_linter import run_linter


def test_run_linter_python_clean(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\nprint(x)\n")
    result = run_linter(str(f), language="Python")
    assert "findings" in result
    assert isinstance(result["findings"], list)


def test_run_linter_python_with_issue(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("import os\nx=1\n")  # unused import, spacing issue
    result = run_linter(str(f), language="Python")
    assert "findings" in result


def test_run_linter_unknown_language(tmp_path):
    f = tmp_path / "file.cobol"
    f.write_text("IDENTIFICATION DIVISION.\n")
    result = run_linter(str(f), language="COBOL")
    assert result["findings"] == []
    assert result["skipped"] is True
