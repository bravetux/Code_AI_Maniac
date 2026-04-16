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

"""
Markdown-to-HTML converter using only Python standard library.

Usage:
    python tools/md_to_html.py <input.md> [output.html]

If output is omitted, writes to <input_stem>.html in the same directory.
"""

import html
import re
import sys
from pathlib import Path


def _escape(text: str) -> str:
    return html.escape(text)


def _inline(text: str) -> str:
    """Apply inline formatting: bold, italic, code, links, images."""
    t = _escape(text)
    # images (before links so ![alt](src) isn't caught by link regex)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', t)
    # links
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    # bold
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"__(.+?)__", r"<strong>\1</strong>", t)
    # italic
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"_(.+?)_", r"<em>\1</em>", t)
    # inline code
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


CSS = """\
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 920px; margin: 2rem auto; padding: 0 1.5rem;
    line-height: 1.6; color: #24292e; background: #fff;
}
h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5em; margin-bottom: 0.5em;
    border-bottom: 1px solid #eaecef; padding-bottom: 0.3em;
}
h1 { font-size: 2em; } h2 { font-size: 1.5em; } h3 { font-size: 1.25em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #dfe2e5; padding: 6px 13px; text-align: left; }
th { background: #f6f8fa; font-weight: 600; }
tr:nth-child(even) { background: #f6f8fa; }
pre { background: #f6f8fa; border-radius: 6px; padding: 16px; overflow-x: auto; }
code { font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 85%; }
pre code { font-size: 100%; }
blockquote { border-left: 4px solid #dfe2e5; padding: 0 1em; color: #6a737d; margin: 1em 0; }
a { color: #0366d6; text-decoration: none; } a:hover { text-decoration: underline; }
hr { border: 0; border-top: 1px solid #eaecef; margin: 1.5em 0; }
ul, ol { padding-left: 2em; } li { margin: 0.25em 0; }
strong { font-weight: 600; } em { font-style: italic; }
p { margin: 0.5em 0; }
"""


def convert(md_text: str, title: str = "Document") -> str:
    lines = md_text.split("\n")
    out: list[str] = []
    in_code = False
    in_table = False
    in_list = False
    list_tag = "ul"

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{list_tag}>")
            in_list = False

    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</table>")
            in_table = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- fenced code blocks ---
        if stripped.startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                close_list()
                close_table()
                lang = stripped[3:].strip()
                cls = f' class="language-{lang}"' if lang else ""
                out.append(f"<pre><code{cls}>")
                in_code = True
            i += 1
            continue

        if in_code:
            out.append(_escape(line))
            i += 1
            continue

        # --- tables ---
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # separator row
            if all(re.match(r"^[-:]+$", c) for c in cells):
                i += 1
                continue
            close_list()
            if not in_table:
                out.append("<table>")
                tag = "th"
                in_table = True
            else:
                tag = "td"
            row = "<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>"
            out.append(row)
            i += 1
            continue
        else:
            close_table()

        # --- headings ---
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            close_list()
            lvl = len(heading.group(1))
            txt = heading.group(2)
            out.append(f"<h{lvl}>{_inline(txt)}</h{lvl}>")
            i += 1
            continue

        # --- blockquote ---
        if stripped.startswith("> "):
            close_list()
            bq_lines = [stripped[2:]]
            while i + 1 < len(lines) and lines[i + 1].strip().startswith("> "):
                i += 1
                bq_lines.append(lines[i].strip()[2:])
            out.append("<blockquote><p>" + " ".join(_inline(l) for l in bq_lines) + "</p></blockquote>")
            i += 1
            continue

        # --- horizontal rule ---
        if stripped in ("---", "***", "___"):
            close_list()
            out.append("<hr>")
            i += 1
            continue

        # --- list items ---
        li_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)$", line)
        if li_match:
            lt = "ol" if re.match(r"\d+\.", li_match.group(2)) else "ul"
            if not in_list:
                list_tag = lt
                out.append(f"<{lt}>")
                in_list = True
            out.append(f"<li>{_inline(li_match.group(3))}</li>")
            i += 1
            continue
        else:
            close_list()

        # --- blank line ---
        if stripped == "":
            i += 1
            continue

        # --- paragraph ---
        out.append(f"<p>{_inline(stripped)}</p>")
        i += 1

    # close any open blocks
    if in_code:
        out.append("</code></pre>")
    close_table()
    close_list()

    body = "\n".join(out)
    return (
        f"<!DOCTYPE html>\n"
        f'<html lang="en">\n<head>\n'
        f'<meta charset="UTF-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{_escape(title)}</title>\n"
        f"<style>\n{CSS}</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>"
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python md_to_html.py <input.md> [output.html]")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"[ERROR] File not found: {src}")
        sys.exit(1)

    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")

    md_text = src.read_text(encoding="utf-8")
    html_out = convert(md_text, title=src.stem)
    dst.write_text(html_out, encoding="utf-8")
    print(f"[OK] {src} -> {dst}")


if __name__ == "__main__":
    main()
