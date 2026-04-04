import html as _html
import streamlit as st
import streamlit.components.v1 as components


def render_mermaid(mermaid_source: str) -> None:
    """Render a Mermaid diagram using an HTML component."""
    if not mermaid_source:
        st.warning("No diagram source available.")
        return

    # Source code — always visible, no expander
    st.markdown("**Mermaid Source**")
    st.code(mermaid_source, language="text")

    # Rendered diagram — collapsible, pinned to mermaid@10 (stable API)
    # mermaid@11 removed the old callback render() API; startOnLoad is the
    # reliable cross-version approach that works with all v10+ releases.
    with st.expander("View rendered diagram", expanded=True):
        safe = _html.escape(mermaid_source)
        diagram_html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:8px;background:white;">
<div class="mermaid">
{safe}
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
    mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
</script>
</body>
</html>"""
        components.html(diagram_html, height=500, scrolling=True)
