import subprocess
import json

try:
    from strands import tool
except ImportError:
    def tool(f): return f


@tool
def run_linter(file_path: str, language: str) -> dict:
    """Run static linters on a file. Returns findings list."""
    lang = language.lower().strip()

    if lang in ("python", "py"):
        return _run_flake8(file_path)
    elif lang in ("javascript", "js", "typescript", "ts"):
        return _run_eslint(file_path)
    else:
        return {"findings": [], "skipped": True, "reason": f"No linter for {language}"}


def _run_flake8(file_path: str) -> dict:
    try:
        result = subprocess.run(
            ["flake8", file_path],
            capture_output=True, text=True, timeout=30
        )
        findings = []
        for line in result.stdout.strip().splitlines():
            # flake8 default format: path:line:col: code message
            parts = line.split(":")
            if len(parts) >= 4:
                findings.append({
                    "line": int(parts[1]) if parts[1].strip().isdigit() else 0,
                    "col": int(parts[2]) if parts[2].strip().isdigit() else 0,
                    "code": parts[3].strip().split()[0] if parts[3].strip() else "",
                    "message": ":".join(parts[3:]).strip(),
                    "tool": "flake8",
                })
        return {"findings": findings, "skipped": False}
    except FileNotFoundError:
        return {"findings": [], "skipped": True, "reason": "flake8 not installed"}
    except subprocess.TimeoutExpired:
        return {"findings": [], "skipped": True, "reason": "linter timed out"}


def _run_eslint(file_path: str) -> dict:
    try:
        result = subprocess.run(
            ["eslint", "--format=json", file_path],
            capture_output=True, text=True, timeout=30
        )
        raw = json.loads(result.stdout or "[]")
        findings = []
        for file_result in raw:
            for msg in file_result.get("messages", []):
                findings.append({
                    "line": msg.get("line", 0),
                    "col": msg.get("column", 0),
                    "code": msg.get("ruleId", ""),
                    "message": msg.get("message", ""),
                    "tool": "eslint",
                })
        return {"findings": findings, "skipped": False}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"findings": [], "skipped": True, "reason": "eslint not installed or parse error"}
    except subprocess.TimeoutExpired:
        return {"findings": [], "skipped": True, "reason": "linter timed out"}
