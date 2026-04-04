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
