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

    # Rendered diagram — collapsible so it doesn't force a fixed-height gap
    with st.expander("View rendered diagram", expanded=True):
        escaped = mermaid_source.replace("`", "\\`").replace("$", "\\$")
        html = f"""
        <div id="mermaid-diagram"></div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{ startOnLoad: false, theme: 'default' }});
            mermaid.render('mermaid-svg', `{escaped}`, function(svgCode) {{
                document.getElementById('mermaid-diagram').innerHTML = svgCode;
            }});
        </script>
        """
        components.html(html, height=500, scrolling=True)
