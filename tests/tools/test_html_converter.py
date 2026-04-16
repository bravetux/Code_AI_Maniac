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

import pytest
from tools.python_html_converter import convert_md_to_html, convert_file


_SAMPLE_MD = """\
# Test Report

## Section One

Some paragraph text with **bold** and `code`.

```python
def hello():
    print("hi")
```

## Section Two

- Item 1
- Item 2
"""


def test_returns_complete_html():
    html = convert_md_to_html(_SAMPLE_MD, title="Test")
    assert "<!DOCTYPE html>" in html
    assert "<title>Test</title>" in html
    assert "</html>" in html


def test_contains_converted_content():
    html = convert_md_to_html(_SAMPLE_MD)
    assert "<h1" in html
    assert "Section One" in html
    assert "Section Two" in html
    assert "<strong>bold</strong>" in html
    assert "<code>" in html


def test_has_syntax_highlighting():
    html = convert_md_to_html(_SAMPLE_MD)
    # Pygments wraps code in a highlight div or pre with class
    assert "highlight" in html or "codehilite" in html


def test_has_sidebar_toc():
    html = convert_md_to_html(_SAMPLE_MD)
    assert "toc" in html.lower() or "sidebar" in html.lower()


def test_is_self_contained():
    """All CSS/JS should be inline — no external references."""
    html = convert_md_to_html(_SAMPLE_MD)
    assert '<link rel="stylesheet" href="http' not in html
    assert '<script src="http' not in html


def test_convert_file(tmp_path):
    md_file = tmp_path / "report.md"
    html_file = tmp_path / "report.html"
    md_file.write_text(_SAMPLE_MD, encoding="utf-8")

    convert_file(str(md_file), str(html_file))

    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Section One" in content


def test_collapsible_sections():
    html = convert_md_to_html(_SAMPLE_MD)
    # Should have some mechanism for collapsible sections (details/summary or JS)
    assert "details" in html.lower() or "collapsible" in html.lower() or "toggle" in html.lower()


def test_print_friendly():
    html = convert_md_to_html(_SAMPLE_MD)
    assert "@media print" in html
