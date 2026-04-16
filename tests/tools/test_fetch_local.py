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
from tools.fetch_local import fetch_local_file, fetch_multiple_local_files, scan_folder_recursive


def test_fetch_entire_file(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("line1\nline2\nline3\n")
    result = fetch_local_file(str(f))
    assert result["content"] == "line1\nline2\nline3\n"
    assert result["total_lines"] == 3
    assert result["file_path"] == str(f)


def test_fetch_line_range(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("\n".join(f"line{i}" for i in range(1, 11)) + "\n")
    result = fetch_local_file(str(f), start_line=3, end_line=5)
    assert result["content"] == "line3\nline4\nline5\n"
    assert result["start_line"] == 3
    assert result["end_line"] == 5


def test_fetch_missing_file():
    result = fetch_local_file("/nonexistent/path.py")
    assert "error" in result


def test_fetch_multiple_files(tmp_path):
    files = []
    for i in range(3):
        f = tmp_path / f"file{i}.py"
        f.write_text(f"# file {i}\n")
        files.append(str(f))
    results = fetch_multiple_local_files(files)
    assert len(results) == 3
    assert all("content" in r for r in results)


def test_scan_folder_recursive_all_files(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "b.js").write_text("let x = 1;")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("y = 2")
    # hidden file and __pycache__ should be excluded
    (tmp_path / ".hidden.py").write_text("hidden")
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "mod.pyc").write_text("bytecode")

    found = scan_folder_recursive(str(tmp_path))
    names = [os.path.basename(p) for p in found]
    assert "a.py" in names
    assert "b.js" in names
    assert "c.py" in names
    assert ".hidden.py" not in names
    assert "mod.pyc" not in names


def test_scan_folder_recursive_extension_filter(tmp_path):
    (tmp_path / "main.py").write_text("pass")
    (tmp_path / "style.css").write_text("body {}")
    (tmp_path / "readme.md").write_text("# Readme")

    found = scan_folder_recursive(str(tmp_path), extensions=["py"])
    names = [os.path.basename(p) for p in found]
    assert names == ["main.py"]


def test_scan_folder_recursive_nonexistent():
    found = scan_folder_recursive("/nonexistent/folder")
    assert found == []


def test_scan_folder_recursive_respects_limit(tmp_path):
    for i in range(10):
        (tmp_path / f"file{i}.py").write_text(f"x = {i}")
    found = scan_folder_recursive(str(tmp_path))
    assert len(found) == 10  # scan returns all; caller enforces limit
