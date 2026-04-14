"""Phase 0 pre-flight secret scanner.

Pure regex-based — no LLM calls.  Scans source code for hardcoded
credentials, API keys, tokens, private keys, and connection strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Pattern definitions ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class SecretPattern:
    name: str
    regex: re.Pattern
    confidence: str  # "high" or "medium"


# Placeholder values that look like secrets but aren't real.
# Match only when the entire matched value IS a recognisable placeholder phrase.
# We deliberately avoid matching substrings so real keys that contain common
# words (e.g. "EXAMPLE" in AWS canonical test keys) are not suppressed.
_PLACEHOLDER_RE = re.compile(
    r"^(?:"
    r"your[_\-]?(?:api[_\-]?key|token|secret|password)(?:[_\-]here)?|"
    r"CHANGE[_\-]?ME|TODO|FIXME|x{3,}|placeholder|"
    r"insert[_\-]here|replace[_\-]?me|dummy|"
    r"test[_\-]?(?:key|token|secret)|"
    r"sample[_\-]?(?:key|token|secret)|"
    r"<[^>]+>|\$\{[^}]+\}"
    r")$",
    re.IGNORECASE,
)

PATTERNS: list[SecretPattern] = [
    SecretPattern(
        name="aws_access_key",
        regex=re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
        confidence="high",
    ),
    SecretPattern(
        name="aws_secret_key",
        regex=re.compile(
            r"""(?:aws_secret_access_key|aws_secret|secret_key)\s*[=:]\s*["']([A-Za-z0-9/+=]{40})["']""",
            re.IGNORECASE,
        ),
        confidence="high",
    ),
    SecretPattern(
        name="generic_secret",
        regex=re.compile(
            r"""(?:^|\b)(?:secret|credential)\s*[=:]\s*["']([A-Za-z0-9/+=]{20,})["']""",
            re.IGNORECASE,
        ),
        confidence="medium",
    ),
    SecretPattern(
        name="private_key",
        regex=re.compile(r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PGP)\s+PRIVATE KEY-----"),
        confidence="high",
    ),
    SecretPattern(
        name="github_token",
        regex=re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{34,}"),
        confidence="high",
    ),
    SecretPattern(
        name="gitlab_token",
        regex=re.compile(r"glpat-[A-Za-z0-9\-_]{20,}"),
        confidence="high",
    ),
    SecretPattern(
        name="jwt_token",
        regex=re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-+/=]{10,}"),
        confidence="high",
    ),
    SecretPattern(
        name="connection_string",
        regex=re.compile(
            r"(?:postgresql|mysql|mongodb|redis|amqp|mssql)://[^\s\"']+:[^\s\"']+@[^\s\"']+",
            re.IGNORECASE,
        ),
        confidence="high",
    ),
    SecretPattern(
        name="hardcoded_password",
        regex=re.compile(
            r"""(?:password|passwd|pwd)\s*[=:]\s*["']([^"']{8,})["']""",
            re.IGNORECASE,
        ),
        confidence="medium",
    ),
    SecretPattern(
        name="generic_api_key",
        regex=re.compile(
            r"""(?:api[_-]?key|apikey|api[_-]?secret|access[_-]?token|auth[_-]?token|secret[_-]?key)\s*[=:]\s*["']([A-Za-z0-9_\-/+=]{20,})["']""",
            re.IGNORECASE,
        ),
        confidence="medium",
    ),
    SecretPattern(
        name="bearer_token",
        regex=re.compile(
            r"""(?:authorization|bearer)\s*[=:]\s*["']Bearer\s+([A-Za-z0-9_\-/.+=]{20,})["']""",
            re.IGNORECASE,
        ),
        confidence="medium",
    ),
    SecretPattern(
        name="azure_key",
        regex=re.compile(
            r"""(?:azure|subscription)[_-]?(?:key|secret|token)\s*[=:]\s*["']([A-Za-z0-9+/=]{20,})["']""",
            re.IGNORECASE,
        ),
        confidence="medium",
    ),
    SecretPattern(
        name="gcp_service_account",
        regex=re.compile(r'"type"\s*:\s*"service_account"'),
        confidence="high",
    ),
]


# ── Core scan function ───────────────────────────────────────────────────────

def _mask_value(value: str) -> str:
    """Partially mask a secret value for safe display."""
    if len(value) <= 8:
        return value[:2] + "..." + value[-1:]
    return value[:4] + "..." + value[-4:]


def _is_placeholder(value: str) -> bool:
    """Check if a matched value looks like a placeholder, not a real secret."""
    return bool(_PLACEHOLDER_RE.search(value))


def scan_secrets(code: str, mode: str = "warn") -> dict:
    """Scan source code for hardcoded secrets.

    Args:
        code: Source code to scan.
        mode: One of "block", "redact", "warn".

    Returns:
        dict with keys: secrets_found, action_taken, code
    """
    lines = code.splitlines()
    secrets_found: list[dict] = []

    for line_num, line_text in enumerate(lines, start=1):
        for pattern in PATTERNS:
            for match in pattern.regex.finditer(line_text):
                matched_str = match.group(1) if match.lastindex else match.group(0)

                # Skip placeholder values
                if _is_placeholder(matched_str):
                    continue

                secrets_found.append({
                    "line": line_num,
                    "type": pattern.name,
                    "match": _mask_value(matched_str),
                    "confidence": pattern.confidence,
                    "context": line_text.strip(),
                })

    # Apply mode
    if mode == "block":
        return {
            "secrets_found": secrets_found,
            "action_taken": "block",
            "code": "" if secrets_found else code,
        }

    if mode == "redact" and secrets_found:
        redacted_code = code
        for secret in secrets_found:
            # Re-find the full match on the original line to replace it
            line_idx = secret["line"] - 1
            original_line = lines[line_idx]
            for p in PATTERNS:
                if p.name == secret["type"]:
                    redacted_line = p.regex.sub(
                        f"[REDACTED-{secret['type']}]", original_line
                    )
                    redacted_code = redacted_code.replace(original_line, redacted_line, 1)
                    break
        return {
            "secrets_found": secrets_found,
            "action_taken": "redact",
            "code": redacted_code,
        }

    # mode == "warn" (default)
    return {
        "secrets_found": secrets_found,
        "action_taken": "warn",
        "code": code,
    }
