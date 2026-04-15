"""Doxygen CLI wrapper — generates a minimal Doxyfile and runs doxygen."""

import os
import subprocess


_DOXYFILE_TEMPLATE = """\
PROJECT_NAME           = "{project_name}"
OUTPUT_DIRECTORY       = "{output_dir}"
INPUT                  = "{source_dir}"
RECURSIVE              = YES
FILE_PATTERNS          = *.c *.h *.cpp *.hpp *.cc *.hh *.cxx *.hxx *.cs
EXTRACT_ALL            = YES
EXTRACT_PRIVATE        = YES
EXTRACT_STATIC         = YES
GENERATE_HTML          = YES
GENERATE_LATEX         = NO
HTML_OUTPUT            = html
HAVE_DOT               = NO
QUIET                  = YES
WARN_IF_UNDOCUMENTED   = NO
OPTIMIZE_OUTPUT_FOR_C  = YES
"""


def generate_doxyfile(source_dir: str, output_dir: str,
                      project_name: str = "Project") -> str:
    """Write a minimal Doxyfile into *output_dir* and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    doxyfile_path = os.path.join(output_dir, "Doxyfile")
    content = _DOXYFILE_TEMPLATE.format(
        project_name=project_name,
        output_dir=output_dir.replace("\\", "/"),
        source_dir=source_dir.replace("\\", "/"),
    )
    with open(doxyfile_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return doxyfile_path


def run_doxygen_tool(source_dir: str, output_dir: str,
                     project_name: str = "Project") -> dict:
    """Generate a Doxyfile, run ``doxygen``, and return the result.

    Returns
    -------
    dict with keys:
        success      : bool
        output_path  : str   — path to generated html/index.html (if success)
        error        : str   — error message (if failed)
    """
    doxyfile_path = generate_doxyfile(source_dir, output_dir, project_name)
    try:
        result = subprocess.run(
            ["doxygen", doxyfile_path],
            capture_output=True, text=True, timeout=120,
        )
        html_index = os.path.join(output_dir, "html", "index.html")
        if result.returncode == 0 and os.path.exists(html_index):
            return {"success": True, "output_path": html_index, "error": ""}
        return {
            "success": False,
            "output_path": "",
            "error": result.stderr[:500] if result.stderr else "Doxygen returned non-zero but no stderr",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output_path": "",
            "error": "doxygen is not installed. Install it from https://www.doxygen.nl/download.html",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output_path": "",
            "error": "doxygen timed out after 120 seconds",
        }
