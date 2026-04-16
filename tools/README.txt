Both files are created and working:

  - md2html.bat — Batch wrapper with argument validation, Python detection, and usage help
  - tools/md_to_html.py — The converter using only Python stdlib (html, re, pathlib)

  Supported Markdown features:
  - Headings (h1-h6), bold, italic, inline code
  - Fenced code blocks with language class
  - Tables (with header detection)
  - Ordered/unordered lists
  - Blockquotes, horizontal rules
  - Links and images
  - GitHub-style CSS styling

  Usage:
  md2html.bat <input.md> [output.html]
  md2html.bat docs\effort.md                  # -> docs\effort.html
  md2html.bat docs\effort.md report.html      # -> report.html
