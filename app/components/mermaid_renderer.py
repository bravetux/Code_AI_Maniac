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

import streamlit as st
import streamlit.components.v1 as components


def render_mermaid(mermaid_source: str) -> None:
    """Render a Mermaid diagram using an HTML component."""
    if not mermaid_source:
        st.warning("No diagram source available.")
        return

    # Source code — always visible
    st.markdown("**Mermaid Source**")
    st.code(mermaid_source, language="text")

    with st.expander("View rendered diagram", expanded=True):
        # Escape for a JS template literal: backslashes first, then backticks,
        # then template-expression openers.  html.escape() is NOT used here
        # because the source goes into a JS string, not into HTML text content.
        escaped = (
            mermaid_source
            .replace("\\", "\\\\")
            .replace("`",  "\\`")
            .replace("${", "\\${")
        )
        diagram_html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{ margin: 0; padding: 8px; background: white; }}
  #mermaid-output svg {{ max-width: 100%; height: auto; }}
  #mermaid-error {{ color: #c0392b; font-family: monospace; font-size: 12px;
                    white-space: pre-wrap; padding: 8px;
                    background: #fdf0ed; border-radius: 4px; }}
</style>
</head>
<body>
<div id="mermaid-output"></div>
<div id="mermaid-error"></div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
(async function () {{
    mermaid.initialize({{ startOnLoad: false, theme: 'default', securityLevel: 'loose' }});
    try {{
        const {{ svg }} = await mermaid.render('mermaid-graph', `{escaped}`);
        document.getElementById('mermaid-output').innerHTML = svg;
    }} catch (err) {{
        document.getElementById('mermaid-error').textContent =
            'Diagram syntax error:\\n' + err.message;
    }}
}})();
</script>
</body>
</html>"""
        components.html(diagram_html, height=500, scrolling=True)
