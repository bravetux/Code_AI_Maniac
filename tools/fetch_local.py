import hashlib
import os

try:
    from strands import tool
except ImportError:
    def tool(f): return f


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


@tool
def fetch_local_file(file_path: str, start_line: int | None = None,
                     end_line: int | None = None) -> dict:
    """Read a local source file, optionally restricted to a line range."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "file_path": file_path}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total_lines = len(lines)
        full_content = "".join(lines)
        file_hash = _file_hash(full_content)
        if start_line is not None and end_line is not None:
            content = "".join(lines[start_line - 1:end_line])
        else:
            content = full_content
            start_line = 1
            end_line = total_lines
        return {
            "file_path": file_path,
            "content": content,
            "total_lines": total_lines,
            "start_line": start_line,
            "end_line": end_line,
            "file_hash": file_hash,
            "extension": os.path.splitext(file_path)[1].lstrip("."),
        }
    except Exception as e:
        return {"error": str(e), "file_path": file_path}


def fetch_multiple_local_files(file_paths: list[str],
                                start_line: int | None = None,
                                end_line: int | None = None) -> list[dict]:
    return [fetch_local_file(fp, start_line, end_line) for fp in file_paths]


def scan_folder_recursive(folder_path: str,
                           extensions: list[str] | None = None) -> list[str]:
    """
    Walk a folder recursively and return sorted file paths.

    Args:
        folder_path: Root directory to scan.
        extensions:  If given, only include files whose extension (without dot,
                     case-insensitive) is in this list.  None means all files.

    Returns:
        Sorted list of absolute file paths (directories and hidden files excluded).
    """
    if not os.path.isdir(folder_path):
        return []

    allowed = {e.lower().lstrip(".") for e in extensions} if extensions else None
    found: list[str] = []

    for root, dirs, files in os.walk(folder_path):
        # Skip hidden directories (e.g. .git, .venv, __pycache__)
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for name in sorted(files):
            if name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            if allowed is None or ext in allowed:
                found.append(os.path.join(root, name))

    return sorted(found)
