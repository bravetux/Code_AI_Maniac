"""
Standalone Markdown-to-HTML converter.

Produces a self-contained, professional HTML document with:
  - Sidebar table of contents with scroll-spy
  - Collapsible h2 sections (details/summary)
  - Syntax highlighting via Pygments (monokai)
  - Print-friendly @media print CSS
  - No external dependencies in the output

Public API
----------
  convert_md_to_html(md_content, title="") -> str
  convert_file(input_path, output_path) -> None

CLI
---
  python tools/python_html_converter.py input.md output.html
"""

from __future__ import annotations

import re
import sys

import markdown
from pygments.formatters import HtmlFormatter


# ---------------------------------------------------------------------------
# Pygments CSS (monokai style, scoped to .codehilite)
# ---------------------------------------------------------------------------
_PYGMENTS_CSS = HtmlFormatter(style="monokai").get_style_defs(".codehilite")

# ---------------------------------------------------------------------------
# Inline CSS
# ---------------------------------------------------------------------------
_CSS = f"""
:root {{
  --bg: #f8f9fa;
  --surface: #ffffff;
  --sidebar-bg: #1e1e2e;
  --sidebar-text: #cdd6f4;
  --sidebar-active: #89b4fa;
  --sidebar-hover: #313244;
  --accent: #4f46e5;
  --text: #1f2937;
  --text-muted: #6b7280;
  --border: #e5e7eb;
  --code-bg: #282a36;
  --sidebar-width: 280px;
  --header-h: 56px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 16px;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg);
}}

/* ── Sidebar ── */
#sidebar {{
  position: fixed;
  top: 0; left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  overflow-y: auto;
  z-index: 100;
  display: flex;
  flex-direction: column;
}}

#sidebar-header {{
  padding: 20px 20px 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #585b70;
  border-bottom: 1px solid #313244;
  flex-shrink: 0;
}}

#toc {{
  padding: 12px 0;
  flex: 1;
}}

#toc a {{
  display: block;
  padding: 5px 20px;
  font-size: 13.5px;
  color: var(--sidebar-text);
  text-decoration: none;
  border-left: 3px solid transparent;
  transition: background .15s, border-color .15s, color .15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

#toc a:hover {{
  background: var(--sidebar-hover);
  color: #fff;
}}

#toc a.active {{
  border-left-color: var(--sidebar-active);
  color: var(--sidebar-active);
  background: rgba(137, 180, 250, .08);
}}

#toc a.toc-h2 {{ padding-left: 20px; font-weight: 600; }}
#toc a.toc-h3 {{ padding-left: 36px; font-size: 12.5px; }}
#toc a.toc-h4 {{ padding-left: 52px; font-size: 12px; color: #a6adc8; }}

/* ── Main content ── */
#main {{
  margin-left: var(--sidebar-width);
  min-height: 100vh;
  padding: 48px 56px 80px;
  max-width: calc(var(--sidebar-width) + 860px);
}}

/* ── Typography ── */
h1, h2, h3, h4, h5, h6 {{
  font-weight: 700;
  line-height: 1.3;
  margin-top: 2rem;
  margin-bottom: .75rem;
  color: #111827;
}}

h1 {{ font-size: 2rem; border-bottom: 2px solid var(--accent); padding-bottom: .4rem; }}
h2 {{ font-size: 1.5rem; }}
h3 {{ font-size: 1.2rem; }}

p {{ margin-bottom: 1rem; }}

a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

ul, ol {{ padding-left: 1.75rem; margin-bottom: 1rem; }}
li {{ margin-bottom: .25rem; }}

table {{
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1.5rem;
  font-size: .9rem;
}}
th, td {{ border: 1px solid var(--border); padding: 8px 12px; text-align: left; }}
th {{ background: #f3f4f6; font-weight: 600; }}
tr:nth-child(even) {{ background: #fafafa; }}

blockquote {{
  border-left: 4px solid var(--accent);
  margin: 1rem 0;
  padding: .5rem 1rem;
  color: var(--text-muted);
  background: #f0f0ff;
  border-radius: 0 4px 4px 0;
}}

code {{
  font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
  font-size: .875em;
  background: #f3f4f6;
  padding: .1em .35em;
  border-radius: 3px;
  color: #be185d;
}}

/* ── Code blocks (Pygments) ── */
.codehilite {{
  margin: 1.25rem 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}}

.codehilite pre {{
  margin: 0;
  padding: 1rem 1.25rem;
  overflow-x: auto;
  font-size: .85rem;
  line-height: 1.6;
  background: var(--code-bg) !important;
  color: #f8f8f2;
}}

/* ── Collapsible h2 sections ── */
details.section {{
  margin-bottom: 1.5rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
}}

details.section > summary {{
  cursor: pointer;
  padding: 14px 20px;
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 10px;
  user-select: none;
  background: #fafafa;
  border-bottom: 1px solid transparent;
  transition: background .15s;
}}

details.section > summary:hover {{ background: #f3f4f6; }}
details.section[open] > summary {{ border-bottom-color: var(--border); }}

details.section > summary::before {{
  content: '▶';
  font-size: .7em;
  color: var(--accent);
  transition: transform .2s;
  flex-shrink: 0;
}}
details.section[open] > summary::before {{ transform: rotate(90deg); }}

.section-body {{
  padding: 20px 24px;
}}

/* ── Pygments ── */
{_PYGMENTS_CSS}

/* ── Print ── */
@media print {{
  #sidebar {{ display: none !important; }}
  #main {{ margin-left: 0; padding: 20px; max-width: 100%; }}
  details.section {{ border: none; box-shadow: none; }}
  details.section > summary {{ display: none; }}
  .section-body {{ display: block !important; padding: 0; }}
  .codehilite {{ box-shadow: none; }}
  a {{ color: inherit; }}
}}

/* ── Responsive ── */
@media (max-width: 768px) {{
  #sidebar {{ transform: translateX(-100%); }}
  #main {{ margin-left: 0; padding: 24px 20px; }}
}}
"""

# ---------------------------------------------------------------------------
# Inline JavaScript
# ---------------------------------------------------------------------------
_JS = """
(function () {
  // Build sidebar TOC from headings in the main content
  var mainEl = document.getElementById('main');
  var tocEl  = document.getElementById('toc');
  if (!mainEl || !tocEl) return;

  // Collect headings (skip h1 — that's the page title)
  var headings = mainEl.querySelectorAll('h2, h3, h4');
  var tocLinks = [];

  headings.forEach(function (h) {
    if (!h.id) {
      h.id = h.textContent.trim()
              .toLowerCase()
              .replace(/[^\\w\\s-]/g, '')
              .replace(/\\s+/g, '-');
    }
    var a = document.createElement('a');
    a.href = '#' + h.id;
    a.textContent = h.textContent;
    a.className = 'toc-' + h.tagName.toLowerCase();
    tocEl.appendChild(a);
    tocLinks.push({ el: h, link: a });
  });

  // Scroll-spy
  var scrollTimer;
  window.addEventListener('scroll', function () {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(function () {
      var scrollY = window.scrollY + 80;
      var active = null;
      for (var i = 0; i < tocLinks.length; i++) {
        if (tocLinks[i].el.offsetTop <= scrollY) {
          active = tocLinks[i].link;
        }
      }
      tocLinks.forEach(function (t) { t.link.classList.remove('active'); });
      if (active) active.classList.add('active');
    }, 50);
  }, { passive: true });

  // Open all details by default (toggle with sidebar link click)
  document.querySelectorAll('details.section').forEach(function (d) {
    d.setAttribute('open', '');
  });
})();
"""

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<nav id="sidebar">
  <div id="sidebar-header">Table of Contents</div>
  <div id="toc"></div>
</nav>
<main id="main">
{body}
</main>
<script>
{js}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Core conversion logic
# ---------------------------------------------------------------------------

def _wrap_h2_sections(html: str) -> str:
    """
    Wrap content between consecutive <h2> tags in collapsible <details> elements.
    Content before the first <h2> is left as-is.
    """
    # Split on h2 open tags, keeping the delimiter
    parts = re.split(r'(<h2[^>]*>)', html)

    if len(parts) <= 1:
        # No h2 headings — nothing to wrap
        return html

    result = [parts[0]]  # content before first h2

    i = 1
    while i < len(parts):
        h2_tag = parts[i]          # e.g. <h2 id="...">
        rest   = parts[i + 1] if i + 1 < len(parts) else ""

        # The h2 element ends at </h2>
        end_idx = rest.find("</h2>")
        if end_idx == -1:
            # Malformed — just append verbatim
            result.append(h2_tag + rest)
            i += 2
            continue

        h2_inner = rest[:end_idx]           # text inside <h2>…</h2>
        after_h2 = rest[end_idx + 5:]       # content after </h2>

        # Body of this section = everything up to the next h2 tag (or end)
        # Since we split on h2 open tags, `after_h2` runs until parts[i+2]
        # which is the next h2 open tag (or doesn't exist).
        section_body = after_h2

        # Extract id from original h2 tag if present
        id_match = re.search(r'id="([^"]*)"', h2_tag)
        section_id = id_match.group(1) if id_match else re.sub(r'[^\w-]', '', h2_inner.lower().replace(' ', '-'))

        result.append(
            f'<details class="section" id="section-{section_id}">\n'
            f'<summary>{h2_inner}</summary>\n'
            f'<div class="section-body">\n{section_body}\n</div>\n'
            f'</details>\n'
        )
        i += 2

    return "".join(result)


def convert_md_to_html(md_content: str, title: str = "") -> str:
    """
    Convert Markdown text to a complete, self-contained HTML document.

    Parameters
    ----------
    md_content : str
        Raw Markdown source.
    title : str, optional
        HTML document title.  If empty, the first H1 in the content is used.

    Returns
    -------
    str
        Full HTML document string.
    """
    # Configure markdown with desired extensions
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "smarty",
            "nl2br",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "codehilite",
                "guess_lang": True,
                "linenums": False,
            },
            "toc": {
                "permalink": False,
                "toc_depth": "2-4",
            },
        },
    )

    body_html = md.convert(md_content)

    # Auto-extract title from first H1 if not provided
    if not title:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", body_html, re.DOTALL | re.IGNORECASE)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

    if not title:
        title = "Report"

    # Wrap h2 blocks in collapsible details/summary
    body_html = _wrap_h2_sections(body_html)

    html = _HTML_TEMPLATE.format(
        title=title,
        css=_CSS,
        body=body_html,
        js=_JS,
    )

    return html


def convert_file(input_path: str, output_path: str) -> None:
    """
    Read a Markdown file and write a complete HTML file.

    Parameters
    ----------
    input_path : str
        Path to the source `.md` file.
    output_path : str
        Path where the `.html` file will be written.
    """
    with open(input_path, encoding="utf-8") as fh:
        md_content = fh.read()

    html = convert_md_to_html(md_content)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/python_html_converter.py input.md output.html", file=sys.stderr)
        sys.exit(1)

    convert_file(sys.argv[1], sys.argv[2])
    print(f"Written: {sys.argv[2]}")
