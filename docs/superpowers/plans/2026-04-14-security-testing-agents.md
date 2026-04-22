# Security Testing Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Security Testing section to AI Arena with pre-flight secret scanning, multi-ecosystem dependency analysis (SCA), AI-powered deep secret detection, and STRIDE/attacker threat modeling.

**Architecture:** Four components woven into the existing orchestrator pipeline — Phase 0 (regex secret gate), Phase 1 (SCA alongside foundation agents), Phase 3 (deep secret scan in synthesis), Phase 4 (threat model consuming all prior findings). A separate UI section groups security features apart from code analysis.

**Tech Stack:** Python 3.11+, Strands Agents, Amazon Bedrock, httpx (for OSV/NVD/GitHub Advisory APIs), regex, DuckDB (existing cache/history), Streamlit

---

### Task 1: Settings & Agent Registry

**Files:**
- Modify: `config/settings.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for new settings**

Add to `tests/test_config.py`:

```python
# ── Security testing settings ────────────────────────────────────────────────

def test_secret_scan_mode_default(test_settings):
    assert test_settings.secret_scan_mode == "warn"


def test_secret_scan_mode_custom(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("SECRET_SCAN_MODE", "block")
    get_settings.cache_clear()
    s = get_settings()
    assert s.secret_scan_mode == "block"
    get_settings.cache_clear()


def test_secret_scan_mode_invalid():
    from config.settings import Settings
    with pytest.raises(ValidationError):
        Settings(secret_scan_mode="invalid")


def test_sca_cve_backend_default(test_settings):
    assert test_settings.sca_cve_backend == "osv_llm"


def test_sca_cve_backend_custom(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("SCA_CVE_BACKEND", "nvd")
    get_settings.cache_clear()
    s = get_settings()
    assert s.sca_cve_backend == "nvd"
    get_settings.cache_clear()


def test_sca_cve_backend_invalid():
    from config.settings import Settings
    with pytest.raises(ValidationError):
        Settings(sca_cve_backend="invalid")


def test_sca_auto_discover_default(test_settings):
    assert test_settings.sca_auto_discover is True


def test_sca_auto_discover_toggle(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("SCA_AUTO_DISCOVER", "false")
    get_settings.cache_clear()
    s = get_settings()
    assert s.sca_auto_discover is False
    get_settings.cache_clear()


def test_nvd_api_key_default(test_settings):
    assert test_settings.nvd_api_key == ""


def test_all_agents_includes_security(test_settings):
    from config.settings import ALL_AGENTS
    assert "secret_scan" in ALL_AGENTS
    assert "dependency_analysis" in ALL_AGENTS
    assert "threat_model" in ALL_AGENTS


def test_enabled_agents_security_subset(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("ENABLED_AGENTS", "secret_scan,threat_model")
    get_settings.cache_clear()
    s = get_settings()
    assert s.enabled_agent_set == frozenset({"secret_scan", "threat_model"})
    get_settings.cache_clear()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v -k "secret_scan or sca_ or nvd_ or all_agents_includes_security or enabled_agents_security"`
Expected: FAIL — settings fields and agent keys don't exist yet

- [ ] **Step 3: Add security settings and agent keys to config/settings.py**

In `config/settings.py`, add three agent keys to `ALL_AGENTS`:

```python
ALL_AGENTS: frozenset[str] = frozenset({
    "bug_analysis",
    "code_design",
    "code_flow",
    "mermaid",
    "requirement",
    "static_analysis",
    "comment_generator",
    "commit_analysis",
    "secret_scan",
    "dependency_analysis",
    "threat_model",
})
```

Add new fields to the `Settings` class, after the report generation block:

```python
    # ── Security testing ─────────────────────────────────────────────────────
    secret_scan_mode: str = Field(default="warn", pattern=r"^(block|redact|warn)$")
    sca_cve_backend: str = Field(default="osv_llm", pattern=r"^(osv|nvd|github|llm|osv_llm)$")
    sca_auto_discover: bool = True
    nvd_api_key: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add config/settings.py tests/test_config.py
git commit -m "feat: add security testing settings and agent registry keys"
```

---

### Task 2: Pre-flight Secret Scanner Tool (Phase 0)

**Files:**
- Create: `tools/secret_scanner.py`
- Create: `tests/tools/test_secret_scanner.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_secret_scanner.py`:

```python
import pytest
from tools.secret_scanner import scan_secrets


# ── Detection tests ──────────────────────────────────────────────────────────

def test_detect_aws_access_key():
    code = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) == 1
    assert result["secrets_found"][0]["type"] == "aws_access_key"
    assert result["secrets_found"][0]["line"] == 1
    assert result["secrets_found"][0]["confidence"] == "high"


def test_detect_aws_secret_key():
    code = 'secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    found_types = [s["type"] for s in result["secrets_found"]]
    assert "aws_secret_key" in found_types or "generic_secret" in found_types


def test_detect_generic_api_key():
    code = 'API_KEY = "sk-1234567890abcdef1234567890abcdef"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1


def test_detect_private_key():
    code = '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ...\n-----END RSA PRIVATE KEY-----\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "private_key"


def test_detect_connection_string():
    code = 'db_url = "postgresql://user:p4ssw0rd@localhost:5432/mydb"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "connection_string"


def test_detect_jwt_token():
    code = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "jwt_token"


def test_detect_github_token():
    code = 'GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "github_token"


def test_detect_password_assignment():
    code = 'password = "super_secret_123"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "hardcoded_password"


def test_no_false_positive_on_clean_code():
    code = 'x = 1\nprint("hello world")\ndef add(a, b):\n    return a + b\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) == 0


def test_no_false_positive_on_placeholder():
    code = 'API_KEY = "your-api-key-here"\npassword = "CHANGE_ME"\n'
    result = scan_secrets(code, mode="warn")
    # Placeholders should not trigger (or be low confidence)
    high_conf = [s for s in result["secrets_found"] if s["confidence"] == "high"]
    assert len(high_conf) == 0


# ── Mode tests ───────────────────────────────────────────────────────────────

def test_mode_warn_returns_original_code():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="warn")
    assert result["action_taken"] == "warn"
    assert result["code"] == code


def test_mode_redact_replaces_secrets():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="redact")
    assert result["action_taken"] == "redact"
    assert "AKIAIOSFODNN7EXAMPLE" not in result["code"]
    assert "[REDACTED-" in result["code"]


def test_mode_block_returns_findings_and_no_code():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="block")
    assert result["action_taken"] == "block"
    assert len(result["secrets_found"]) >= 1
    assert result["code"] == ""


def test_mode_block_returns_original_when_clean():
    code = 'x = 1\n'
    result = scan_secrets(code, mode="block")
    assert result["action_taken"] == "block"
    assert result["code"] == code
    assert len(result["secrets_found"]) == 0


# ── Masking tests ────────────────────────────────────────────────────────────

def test_match_field_is_partially_masked():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="warn")
    match_val = result["secrets_found"][0]["match"]
    assert "AKIA" in match_val  # prefix visible
    assert "EXAMPLE" not in match_val or "..." in match_val or "X" in match_val
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_secret_scanner.py -v`
Expected: FAIL — module `tools.secret_scanner` does not exist

- [ ] **Step 3: Implement the secret scanner tool**

Create `tools/secret_scanner.py`:

```python
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


# Placeholder values that look like secrets but aren't real
_PLACEHOLDER_RE = re.compile(
    r"(your[_-]?(api[_-]?key|token|secret|password)|"
    r"CHANGE[_-]?ME|TODO|FIXME|xxx+|placeholder|example|"
    r"insert[_-]?here|replace[_-]?me|dummy|test[_-]?key|sample)",
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
        name="private_key",
        regex=re.compile(r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PGP)\s+PRIVATE KEY-----"),
        confidence="high",
    ),
    SecretPattern(
        name="github_token",
        regex=re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}"),
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_secret_scanner.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add tools/secret_scanner.py tests/tools/test_secret_scanner.py
git commit -m "feat: add pre-flight regex secret scanner tool"
```

---

### Task 3: Dependency Parser Tool

**Files:**
- Create: `tools/dependency_parser.py`
- Create: `tests/tools/test_dependency_parser.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_dependency_parser.py`:

```python
import pytest
from tools.dependency_parser import parse_dependency_file, detect_dep_files


# ── Python ───────────────────────────────────────────────────────────────────

def test_parse_requirements_txt():
    content = "requests==2.25.1\nflask>=2.0.0\nboto3\nnumpy==1.21.0\n"
    result = parse_dependency_file("requirements.txt", content)
    assert result["ecosystem"] == "PyPI"
    assert len(result["packages"]) == 4
    req = next(p for p in result["packages"] if p["name"] == "requests")
    assert req["version"] == "2.25.1"
    boto = next(p for p in result["packages"] if p["name"] == "boto3")
    assert boto["version"] is None  # unpinned


def test_parse_requirements_txt_with_comments():
    content = "# Core deps\nrequests==2.25.1\n  # another comment\n-e git+https://...\n"
    result = parse_dependency_file("requirements.txt", content)
    assert len(result["packages"]) == 1
    assert result["packages"][0]["name"] == "requests"


def test_parse_pyproject_toml():
    content = '''
[project]
dependencies = [
    "requests>=2.25.1",
    "flask==2.0.0",
]
'''
    result = parse_dependency_file("pyproject.toml", content)
    assert result["ecosystem"] == "PyPI"
    assert len(result["packages"]) == 2


# ── JavaScript ───────────────────────────────────────────────────────────────

def test_parse_package_json():
    content = '''{
  "dependencies": {"express": "^4.18.0", "lodash": "4.17.21"},
  "devDependencies": {"jest": "^29.0.0"}
}'''
    result = parse_dependency_file("package.json", content)
    assert result["ecosystem"] == "npm"
    assert len(result["packages"]) == 3


# ── Java ─────────────────────────────────────────────────────────────────────

def test_parse_pom_xml():
    content = '''<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>5.3.20</version>
    </dependency>
  </dependencies>
</project>'''
    result = parse_dependency_file("pom.xml", content)
    assert result["ecosystem"] == "Maven"
    assert len(result["packages"]) == 1
    assert result["packages"][0]["name"] == "org.springframework:spring-core"
    assert result["packages"][0]["version"] == "5.3.20"


def test_parse_build_gradle():
    content = """dependencies {
    implementation 'org.springframework:spring-core:5.3.20'
    testImplementation "junit:junit:4.13.2"
}"""
    result = parse_dependency_file("build.gradle", content)
    assert result["ecosystem"] == "Maven"
    assert len(result["packages"]) == 2


# ── C# ───────────────────────────────────────────────────────────────────────

def test_parse_csproj():
    content = '''<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    <PackageReference Include="Serilog" Version="3.0.0" />
  </ItemGroup>
</Project>'''
    result = parse_dependency_file("MyApp.csproj", content)
    assert result["ecosystem"] == "NuGet"
    assert len(result["packages"]) == 2


# ── Go ───────────────────────────────────────────────────────────────────────

def test_parse_go_mod():
    content = """module example.com/myapp

go 1.21

require (
\tgithub.com/gin-gonic/gin v1.9.1
\tgolang.org/x/net v0.15.0
)"""
    result = parse_dependency_file("go.mod", content)
    assert result["ecosystem"] == "Go"
    assert len(result["packages"]) == 2
    gin = next(p for p in result["packages"] if "gin" in p["name"])
    assert gin["version"] == "v1.9.1"


# ── Rust ─────────────────────────────────────────────────────────────────────

def test_parse_cargo_toml():
    content = '''[dependencies]
serde = "1.0"
tokio = { version = "1.32", features = ["full"] }
'''
    result = parse_dependency_file("Cargo.toml", content)
    assert result["ecosystem"] == "crates.io"
    assert len(result["packages"]) == 2


# ── C/C++ ────────────────────────────────────────────────────────────────────

def test_parse_conanfile_txt():
    content = """[requires]
boost/1.82.0
openssl/3.1.1
"""
    result = parse_dependency_file("conanfile.txt", content)
    assert result["ecosystem"] == "conan"
    assert len(result["packages"]) == 2


def test_parse_vcpkg_json():
    content = '''{
  "dependencies": ["zlib", "openssl", "boost-filesystem"]
}'''
    result = parse_dependency_file("vcpkg.json", content)
    assert result["ecosystem"] == "vcpkg"
    assert len(result["packages"]) == 3


# ── Unknown file ─────────────────────────────────────────────────────────────

def test_parse_unknown_file():
    result = parse_dependency_file("unknown.xyz", "something")
    assert result["ecosystem"] == "unknown"
    assert result["packages"] == []


# ── Auto-discovery ───────────────────────────────────────────────────────────

def test_detect_dep_files_in_directory(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.25.1\n")
    (tmp_path / "package.json").write_text('{"dependencies":{}}\n')
    (tmp_path / "main.py").write_text("print('hello')\n")  # not a dep file
    found = detect_dep_files(str(tmp_path))
    filenames = [f.split("/")[-1].split("\\")[-1] for f in found]
    assert "requirements.txt" in filenames
    assert "package.json" in filenames
    assert "main.py" not in filenames


def test_detect_dep_files_empty_dir(tmp_path):
    found = detect_dep_files(str(tmp_path))
    assert found == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_dependency_parser.py -v`
Expected: FAIL — module does not exist

- [ ] **Step 3: Implement the dependency parser**

Create `tools/dependency_parser.py`:

```python
"""Multi-ecosystem dependency file parser.

Extracts package names and version constraints from dependency files
for Python, JavaScript, Java, C#, Go, Rust, and C/C++ ecosystems.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET


# ── Known dependency file basenames for auto-discovery ───────────────────────

_DEP_FILENAMES: set[str] = {
    "requirements.txt", "pyproject.toml", "setup.cfg", "Pipfile",
    "package.json", "package-lock.json", "yarn.lock",
    "pom.xml", "build.gradle",
    "CMakeLists.txt", "conanfile.txt", "vcpkg.json",
    "packages.config", "Directory.Packages.props",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
}

_DEP_EXTENSIONS: set[str] = {".csproj"}


def detect_dep_files(directory: str) -> list[str]:
    """Find known dependency files in a directory (non-recursive)."""
    found = []
    try:
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if not os.path.isfile(full):
                continue
            if entry in _DEP_FILENAMES:
                found.append(full)
            elif os.path.splitext(entry)[1] in _DEP_EXTENSIONS:
                found.append(full)
    except OSError:
        pass
    return sorted(found)


# ── Dispatcher ───────────────────────────────────────────────────────────────

def parse_dependency_file(filename: str, content: str) -> dict:
    """Parse a dependency file and return structured package list.

    Returns:
        {"ecosystem": str, "packages": [{"name": str, "version": str|None}]}
    """
    basename = os.path.basename(filename)
    ext = os.path.splitext(basename)[1]

    if basename == "requirements.txt":
        return _parse_requirements_txt(content)
    if basename == "pyproject.toml":
        return _parse_pyproject_toml(content)
    if basename in ("setup.cfg", "Pipfile"):
        return _parse_generic_python(content)
    if basename == "package.json":
        return _parse_package_json(content)
    if basename == "pom.xml":
        return _parse_pom_xml(content)
    if basename == "build.gradle":
        return _parse_build_gradle(content)
    if ext == ".csproj" or basename == "packages.config" or basename == "Directory.Packages.props":
        return _parse_csproj(content)
    if basename == "go.mod":
        return _parse_go_mod(content)
    if basename == "Cargo.toml":
        return _parse_cargo_toml(content)
    if basename == "conanfile.txt":
        return _parse_conanfile_txt(content)
    if basename == "vcpkg.json":
        return _parse_vcpkg_json(content)

    return {"ecosystem": "unknown", "packages": []}


# ── Python ───────────────────────────────────────────────────────────────────

def _parse_requirements_txt(content: str) -> dict:
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Handle: package==1.0, package>=1.0, package~=1.0, package
        m = re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*(?:[=!<>~]=*\s*(.+?))?$", line)
        if m:
            name = re.sub(r"\[.*\]", "", m.group(1))  # strip extras
            version = m.group(2) if m.group(2) else None
            packages.append({"name": name, "version": version})
    return {"ecosystem": "PyPI", "packages": packages}


def _parse_pyproject_toml(content: str) -> dict:
    packages = []
    # Simple regex extraction from dependencies array
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies") and "=" in stripped:
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                in_deps = False
                continue
            m = re.match(r'["\']([A-Za-z0-9_.\-]+)\s*(?:[=!<>~]=*\s*(.+?))?["\']', stripped)
            if m:
                packages.append({"name": m.group(1), "version": m.group(2)})
    return {"ecosystem": "PyPI", "packages": packages}


def _parse_generic_python(content: str) -> dict:
    # Minimal fallback for setup.cfg / Pipfile
    packages = []
    for line in content.splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*[=<>!~]", line)
        if m:
            packages.append({"name": m.group(1), "version": None})
    return {"ecosystem": "PyPI", "packages": packages}


# ── JavaScript ───────────────────────────────────────────────────────────────

def _parse_package_json(content: str) -> dict:
    packages = []
    try:
        data = json.loads(content)
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in data.get(section, {}).items():
                # Strip semver prefixes (^, ~, >=)
                clean = re.sub(r"^[\^~>=<]+", "", version) if version else None
                packages.append({"name": name, "version": clean})
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"ecosystem": "npm", "packages": packages}


# ── Java ─────────────────────────────────────────────────────────────────────

def _parse_pom_xml(content: str) -> dict:
    packages = []
    try:
        # Strip namespace for simpler parsing
        clean = re.sub(r'\sxmlns="[^"]*"', "", content, count=1)
        root = ET.fromstring(clean)
        for dep in root.iter("dependency"):
            gid = dep.findtext("groupId", "")
            aid = dep.findtext("artifactId", "")
            ver = dep.findtext("version")
            if gid and aid:
                packages.append({"name": f"{gid}:{aid}", "version": ver})
    except ET.ParseError:
        pass
    return {"ecosystem": "Maven", "packages": packages}


def _parse_build_gradle(content: str) -> dict:
    packages = []
    # Match: implementation 'group:artifact:version' or "group:artifact:version"
    for m in re.finditer(r"""(?:implementation|api|compile|testImplementation|runtimeOnly)\s+['"]([^:'"]+):([^:'"]+):([^'"]+)['"]""", content):
        packages.append({
            "name": f"{m.group(1)}:{m.group(2)}",
            "version": m.group(3),
        })
    return {"ecosystem": "Maven", "packages": packages}


# ── C# ───────────────────────────────────────────────────────────────────────

def _parse_csproj(content: str) -> dict:
    packages = []
    try:
        root = ET.fromstring(content)
        for ref in root.iter("PackageReference"):
            name = ref.get("Include")
            version = ref.get("Version")
            if name:
                packages.append({"name": name, "version": version})
    except ET.ParseError:
        pass
    return {"ecosystem": "NuGet", "packages": packages}


# ── Go ───────────────────────────────────────────────────────────────────────

def _parse_go_mod(content: str) -> dict:
    packages = []
    in_require = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require (") or stripped == "require (":
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if in_require:
            parts = stripped.split()
            if len(parts) >= 2:
                packages.append({"name": parts[0], "version": parts[1]})
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 3:
                packages.append({"name": parts[1], "version": parts[2]})
    return {"ecosystem": "Go", "packages": packages}


# ── Rust ─────────────────────────────────────────────────────────────────────

def _parse_cargo_toml(content: str) -> dict:
    packages = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
            continue
        if in_deps and "=" in stripped:
            # serde = "1.0" or tokio = { version = "1.32", ... }
            m = re.match(r'^(\S+)\s*=\s*"([^"]+)"', stripped)
            if m:
                packages.append({"name": m.group(1), "version": m.group(2)})
            else:
                m = re.match(r'^(\S+)\s*=\s*\{.*version\s*=\s*"([^"]+)"', stripped)
                if m:
                    packages.append({"name": m.group(1), "version": m.group(2)})
    return {"ecosystem": "crates.io", "packages": packages}


# ── C/C++ ────────────────────────────────────────────────────────────────────

def _parse_conanfile_txt(content: str) -> dict:
    packages = []
    in_requires = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[requires]":
            in_requires = True
            continue
        if stripped.startswith("[") and in_requires:
            in_requires = False
            continue
        if in_requires and "/" in stripped:
            parts = stripped.split("/", 1)
            packages.append({"name": parts[0], "version": parts[1] if len(parts) > 1 else None})
    return {"ecosystem": "conan", "packages": packages}


def _parse_vcpkg_json(content: str) -> dict:
    packages = []
    try:
        data = json.loads(content)
        for dep in data.get("dependencies", []):
            if isinstance(dep, str):
                packages.append({"name": dep, "version": None})
            elif isinstance(dep, dict):
                packages.append({"name": dep.get("name", ""), "version": dep.get("version-string")})
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"ecosystem": "vcpkg", "packages": packages}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_dependency_parser.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add tools/dependency_parser.py tests/tools/test_dependency_parser.py
git commit -m "feat: add multi-ecosystem dependency file parser"
```

---

### Task 4: CVE Backend System

**Files:**
- Create: `tools/cve_backends/__init__.py`
- Create: `tools/cve_backends/osv.py`
- Create: `tools/cve_backends/nvd.py`
- Create: `tools/cve_backends/github_advisory.py`
- Create: `tools/cve_backends/llm_only.py`
- Create: `tools/cve_backends/hybrid.py`
- Create: `tests/tools/test_cve_backends.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_cve_backends.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from tools.cve_backends import get_backend, lookup_vulnerabilities
from tools.cve_backends.osv import lookup_osv
from tools.cve_backends.nvd import lookup_nvd
from tools.cve_backends.github_advisory import lookup_github
from tools.cve_backends.llm_only import lookup_llm
from tools.cve_backends.hybrid import lookup_hybrid


# ── Backend registry ─────────────────────────────────────────────────────────

def test_get_backend_osv():
    fn = get_backend("osv")
    assert fn is lookup_osv


def test_get_backend_nvd():
    fn = get_backend("nvd")
    assert fn is lookup_nvd


def test_get_backend_github():
    fn = get_backend("github")
    assert fn is lookup_github


def test_get_backend_llm():
    fn = get_backend("llm")
    assert fn is lookup_llm


def test_get_backend_osv_llm():
    fn = get_backend("osv_llm")
    assert fn is lookup_hybrid


def test_get_backend_invalid():
    with pytest.raises(ValueError, match="Unknown CVE backend"):
        get_backend("invalid")


# ── OSV backend ──────────────────────────────────────────────────────────────

def test_osv_lookup_with_mock(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulns": [
            {
                "id": "GHSA-xxxx-xxxx-xxxx",
                "summary": "Test vulnerability",
                "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"}],
                "affected": [{"ranges": [{"events": [{"fixed": "2.31.0"}]}]}],
            }
        ]
    }

    with patch("tools.cve_backends.osv.httpx.post", return_value=mock_response):
        results = lookup_osv([{"name": "requests", "version": "2.25.1", "ecosystem": "PyPI"}])

    assert len(results) == 1
    assert results[0]["package"] == "requests"
    assert len(results[0]["vulnerabilities"]) == 1
    assert results[0]["vulnerabilities"][0]["cve_id"] == "GHSA-xxxx-xxxx-xxxx"


def test_osv_lookup_no_vulns(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"vulns": []}

    with patch("tools.cve_backends.osv.httpx.post", return_value=mock_response):
        results = lookup_osv([{"name": "safe-pkg", "version": "1.0.0", "ecosystem": "PyPI"}])

    assert len(results) == 1
    assert results[0]["vulnerabilities"] == []


def test_osv_lookup_api_error(monkeypatch):
    with patch("tools.cve_backends.osv.httpx.post", side_effect=Exception("network error")):
        results = lookup_osv([{"name": "requests", "version": "2.25.1", "ecosystem": "PyPI"}])

    assert len(results) == 1
    assert results[0]["vulnerabilities"] == []
    assert "error" in results[0]


# ── Dispatcher ───────────────────────────────────────────────────────────────

def test_lookup_vulnerabilities_dispatches():
    packages = [{"name": "requests", "version": "2.25.1", "ecosystem": "PyPI"}]
    with patch("tools.cve_backends.osv.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"vulns": []}
        mock_post.return_value = mock_resp
        results = lookup_vulnerabilities(packages, backend="osv")

    assert len(results) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_cve_backends.py -v`
Expected: FAIL — modules don't exist

- [ ] **Step 3: Implement the CVE backend registry**

Create `tools/cve_backends/__init__.py`:

```python
"""CVE backend system — pluggable vulnerability lookup backends."""

from __future__ import annotations

from typing import Callable

from tools.cve_backends.osv import lookup_osv
from tools.cve_backends.nvd import lookup_nvd
from tools.cve_backends.github_advisory import lookup_github
from tools.cve_backends.llm_only import lookup_llm
from tools.cve_backends.hybrid import lookup_hybrid

_BACKENDS: dict[str, Callable] = {
    "osv": lookup_osv,
    "nvd": lookup_nvd,
    "github": lookup_github,
    "llm": lookup_llm,
    "osv_llm": lookup_hybrid,
}


def get_backend(name: str) -> Callable:
    """Return the lookup function for the named backend."""
    if name not in _BACKENDS:
        raise ValueError(f"Unknown CVE backend: {name!r}. Valid: {list(_BACKENDS)}")
    return _BACKENDS[name]


def lookup_vulnerabilities(packages: list[dict], backend: str = "osv_llm") -> list[dict]:
    """Look up vulnerabilities for a list of packages using the named backend.

    Each package dict should have: name, version, ecosystem.
    Returns list of dicts: {package, version, ecosystem, vulnerabilities: [...]}
    """
    fn = get_backend(backend)
    return fn(packages)
```

- [ ] **Step 4: Implement OSV backend**

Create `tools/cve_backends/osv.py`:

```python
"""OSV.dev API backend — free, no API key, covers all ecosystems."""

from __future__ import annotations

import httpx

_OSV_URL = "https://api.osv.dev/v1/query"

# Map our ecosystem names to OSV ecosystem names
_ECOSYSTEM_MAP = {
    "PyPI": "PyPI",
    "npm": "npm",
    "Maven": "Maven",
    "NuGet": "NuGet",
    "Go": "Go",
    "crates.io": "crates.io",
    "conan": "ConanCenter",
    "vcpkg": None,  # not in OSV
}


def _severity_from_cvss(severity_list: list[dict]) -> str:
    """Extract a simple severity string from OSV severity data."""
    for entry in severity_list:
        score_str = entry.get("score", "")
        # Try to extract numeric CVSS score
        if "CVSS" in score_str:
            # Parse base score from vector like CVSS:3.1/.../...
            parts = score_str.split("/")
            for p in parts:
                if p.replace(".", "").replace("-", "").isdigit():
                    try:
                        score = float(p)
                        if score >= 9.0:
                            return "critical"
                        if score >= 7.0:
                            return "major"
                        return "minor"
                    except ValueError:
                        continue
    return "major"  # default when severity can't be parsed


def _extract_fixed_version(affected: list[dict]) -> str | None:
    """Extract the earliest fixed version from affected ranges."""
    for aff in affected:
        for rng in aff.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    return event["fixed"]
    return None


def lookup_osv(packages: list[dict]) -> list[dict]:
    """Query OSV.dev for each package. Returns per-package vulnerability data."""
    results = []
    for pkg in packages:
        ecosystem = _ECOSYSTEM_MAP.get(pkg.get("ecosystem", ""), pkg.get("ecosystem"))
        version = pkg.get("version")
        vulns = []
        error = None

        if ecosystem and version:
            try:
                resp = httpx.post(
                    _OSV_URL,
                    json={"package": {"name": pkg["name"], "ecosystem": ecosystem},
                          "version": version},
                    timeout=15,
                )
                if resp.status_code == 200:
                    for v in resp.json().get("vulns", []):
                        vulns.append({
                            "cve_id": v.get("id", ""),
                            "summary": v.get("summary", ""),
                            "severity": _severity_from_cvss(v.get("severity", [])),
                            "fixed_in": _extract_fixed_version(v.get("affected", [])),
                            "source": "osv",
                        })
            except Exception as e:
                error = str(e)

        entry = {
            "package": pkg["name"],
            "version": version,
            "ecosystem": pkg.get("ecosystem", ""),
            "vulnerabilities": vulns,
        }
        if error:
            entry["error"] = error
        results.append(entry)

    return results
```

- [ ] **Step 5: Implement NVD backend**

Create `tools/cve_backends/nvd.py`:

```python
"""NVD (National Vulnerability Database) API backend.

Requires NVD_API_KEY for reasonable rate limits.
"""

from __future__ import annotations

import httpx

_NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def lookup_nvd(packages: list[dict], api_key: str | None = None) -> list[dict]:
    """Query NVD for each package by keyword search.

    Note: NVD uses CPE identifiers, not package names directly.
    This performs a keyword-based search which may have false positives.
    """
    if api_key is None:
        from config.settings import get_settings
        api_key = get_settings().nvd_api_key or None

    headers = {}
    if api_key:
        headers["apiKey"] = api_key

    results = []
    for pkg in packages:
        vulns = []
        error = None
        try:
            resp = httpx.get(
                _NVD_URL,
                params={"keywordSearch": pkg["name"], "resultsPerPage": 10},
                headers=headers,
                timeout=20,
            )
            if resp.status_code == 200:
                for item in resp.json().get("vulnerabilities", []):
                    cve = item.get("cve", {})
                    cve_id = cve.get("id", "")
                    desc_list = cve.get("descriptions", [])
                    summary = next(
                        (d["value"] for d in desc_list if d.get("lang") == "en"),
                        "",
                    )
                    # Extract CVSS severity
                    metrics = cve.get("metrics", {})
                    severity = "major"
                    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        metric_list = metrics.get(key, [])
                        if metric_list:
                            base_score = metric_list[0].get("cvssData", {}).get("baseScore", 0)
                            if base_score >= 9.0:
                                severity = "critical"
                            elif base_score >= 7.0:
                                severity = "major"
                            else:
                                severity = "minor"
                            break
                    vulns.append({
                        "cve_id": cve_id,
                        "summary": summary[:200],
                        "severity": severity,
                        "fixed_in": None,
                        "source": "nvd",
                    })
            elif resp.status_code == 403:
                error = "NVD API key required or rate limit exceeded"
        except Exception as e:
            error = str(e)

        entry = {
            "package": pkg["name"],
            "version": pkg.get("version"),
            "ecosystem": pkg.get("ecosystem", ""),
            "vulnerabilities": vulns,
        }
        if error:
            entry["error"] = error
        results.append(entry)

    return results
```

- [ ] **Step 6: Implement GitHub Advisory backend**

Create `tools/cve_backends/github_advisory.py`:

```python
"""GitHub Advisory Database backend.

Uses the existing GITHUB_TOKEN from settings.
"""

from __future__ import annotations

import httpx

_GHSA_GRAPHQL = "https://api.github.com/graphql"

# Map our ecosystems to GitHub SecurityAdvisoryEcosystem enum
_ECO_MAP = {
    "PyPI": "PIP",
    "npm": "NPM",
    "Maven": "MAVEN",
    "NuGet": "NUGET",
    "Go": "GO",
    "crates.io": "RUST",
}

_QUERY = """
query($ecosystem: SecurityAdvisoryEcosystem, $package: String!) {
  securityVulnerabilities(
    first: 10
    ecosystem: $ecosystem
    package: $package
  ) {
    nodes {
      advisory { ghsaId summary severity }
      firstPatchedVersion { identifier }
      vulnerableVersionRange
    }
  }
}
"""

_SEVERITY_MAP = {"CRITICAL": "critical", "HIGH": "major", "MODERATE": "major", "LOW": "minor"}


def lookup_github(packages: list[dict], token: str | None = None) -> list[dict]:
    """Query GitHub Advisory Database via GraphQL."""
    if token is None:
        from config.settings import get_settings
        token = get_settings().github_token

    if not token:
        return [{
            "package": p["name"],
            "version": p.get("version"),
            "ecosystem": p.get("ecosystem", ""),
            "vulnerabilities": [],
            "error": "GITHUB_TOKEN required for GitHub Advisory backend",
        } for p in packages]

    headers = {"Authorization": f"bearer {token}"}
    results = []

    for pkg in packages:
        vulns = []
        error = None
        ecosystem = _ECO_MAP.get(pkg.get("ecosystem", ""))

        if ecosystem:
            try:
                resp = httpx.post(
                    _GHSA_GRAPHQL,
                    json={"query": _QUERY, "variables": {
                        "ecosystem": ecosystem, "package": pkg["name"],
                    }},
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    nodes = data.get("securityVulnerabilities", {}).get("nodes", [])
                    for node in nodes:
                        adv = node.get("advisory", {})
                        vulns.append({
                            "cve_id": adv.get("ghsaId", ""),
                            "summary": adv.get("summary", ""),
                            "severity": _SEVERITY_MAP.get(adv.get("severity", ""), "major"),
                            "fixed_in": (node.get("firstPatchedVersion") or {}).get("identifier"),
                            "source": "github",
                        })
                else:
                    error = f"GitHub API returned {resp.status_code}"
            except Exception as e:
                error = str(e)
        else:
            error = f"Ecosystem {pkg.get('ecosystem')} not supported by GitHub Advisory DB"

        entry = {
            "package": pkg["name"],
            "version": pkg.get("version"),
            "ecosystem": pkg.get("ecosystem", ""),
            "vulnerabilities": vulns,
        }
        if error:
            entry["error"] = error
        results.append(entry)

    return results
```

- [ ] **Step 7: Implement LLM-only backend**

Create `tools/cve_backends/llm_only.py`:

```python
"""LLM-only CVE assessment backend.

Uses Bedrock to assess dependency risks from training knowledge.
No live CVE data — severity and CVE IDs may be approximate.
"""

from __future__ import annotations

import json

from agents._bedrock import make_bedrock_model, parse_json_response
from strands import Agent

_SYSTEM_PROMPT = """You are a software security expert assessing dependency risks.

For each package and version provided, assess known vulnerabilities from your training data.

Return a JSON object:
{
  "assessments": [
    {
      "package": "<package name>",
      "version": "<version>",
      "vulnerabilities": [
        {
          "cve_id": "<CVE or advisory ID if known, otherwise 'LLM-assessment'>",
          "summary": "<description of the vulnerability>",
          "severity": "<critical|major|minor>",
          "fixed_in": "<version that fixes it, if known>"
        }
      ]
    }
  ]
}

If you are not aware of any vulnerabilities for a package version, return an empty vulnerabilities list.
Be conservative — only report vulnerabilities you are confident about."""


def lookup_llm(packages: list[dict]) -> list[dict]:
    """Assess package vulnerabilities using LLM knowledge."""
    if not packages:
        return []

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)

    pkg_list = "\n".join(
        f"- {p['name']} {p.get('version', 'unknown')} ({p.get('ecosystem', 'unknown')})"
        for p in packages
    )
    prompt = f"Assess the following dependencies for known vulnerabilities:\n\n{pkg_list}"

    raw = str(agent(prompt))

    try:
        parsed = parse_json_response(raw)
        assessments = {a["package"]: a for a in parsed.get("assessments", [])}
    except (json.JSONDecodeError, ValueError, KeyError):
        assessments = {}

    results = []
    for pkg in packages:
        assessment = assessments.get(pkg["name"], {})
        vulns = []
        for v in assessment.get("vulnerabilities", []):
            vulns.append({
                "cve_id": v.get("cve_id", "LLM-assessment"),
                "summary": v.get("summary", ""),
                "severity": v.get("severity", "major"),
                "fixed_in": v.get("fixed_in"),
                "source": "llm",
            })
        results.append({
            "package": pkg["name"],
            "version": pkg.get("version"),
            "ecosystem": pkg.get("ecosystem", ""),
            "vulnerabilities": vulns,
        })

    return results
```

- [ ] **Step 8: Implement hybrid (OSV + LLM) backend**

Create `tools/cve_backends/hybrid.py`:

```python
"""Hybrid backend — OSV.dev for real CVE data + LLM for risk assessment.

Default backend (osv_llm). Queries OSV first, then passes findings
to Bedrock for prioritization and remediation context.
"""

from __future__ import annotations

import json

from tools.cve_backends.osv import lookup_osv
from agents._bedrock import make_bedrock_model, parse_json_response
from strands import Agent

_SYSTEM_PROMPT = """You are a software security expert. You will receive a list of
dependencies with their known CVE data from the OSV database.

For each vulnerability, provide:
1. A risk assessment in the context of the package's typical use
2. Whether the vulnerability is likely exploitable
3. Recommended remediation priority

Also identify any packages that have NO CVEs from the database but which
you know from your training data to have notable security concerns.

Return a JSON object:
{
  "enrichments": [
    {
      "package": "<name>",
      "risk_context": "<how this vulnerability typically manifests>",
      "exploitability": "<high|medium|low>",
      "remediation_priority": "<immediate|soon|low>"
    }
  ],
  "additional_concerns": [
    {
      "package": "<name>",
      "cve_id": "LLM-assessment",
      "summary": "<concern>",
      "severity": "<critical|major|minor>",
      "fixed_in": "<version if known>"
    }
  ]
}"""


def lookup_hybrid(packages: list[dict]) -> list[dict]:
    """OSV lookup + LLM enrichment."""
    # Step 1: Get real CVE data from OSV
    osv_results = lookup_osv(packages)

    # Step 2: Enrich with LLM
    try:
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)

        summary_lines = []
        for r in osv_results:
            vuln_count = len(r["vulnerabilities"])
            summary_lines.append(
                f"- {r['package']} {r.get('version', '?')} ({r.get('ecosystem', '?')}): "
                f"{vuln_count} known CVE(s)"
                + (f" — {', '.join(v['cve_id'] for v in r['vulnerabilities'][:3])}"
                   if vuln_count > 0 else "")
            )

        prompt = f"Assess these dependencies and their CVE findings:\n\n" + "\n".join(summary_lines)
        raw = str(agent(prompt))
        parsed = parse_json_response(raw)

        # Merge enrichments into OSV results
        enrichments = {e["package"]: e for e in parsed.get("enrichments", [])}
        for r in osv_results:
            enrichment = enrichments.get(r["package"])
            if enrichment:
                r["risk_context"] = enrichment.get("risk_context", "")
                r["exploitability"] = enrichment.get("exploitability", "")
                r["remediation_priority"] = enrichment.get("remediation_priority", "")

        # Add LLM-discovered additional concerns
        additional = parsed.get("additional_concerns", [])
        pkg_map = {r["package"]: r for r in osv_results}
        for concern in additional:
            pkg_name = concern.get("package", "")
            if pkg_name in pkg_map:
                pkg_map[pkg_name]["vulnerabilities"].append({
                    "cve_id": concern.get("cve_id", "LLM-assessment"),
                    "summary": concern.get("summary", ""),
                    "severity": concern.get("severity", "major"),
                    "fixed_in": concern.get("fixed_in"),
                    "source": "llm",
                })

    except Exception:
        # LLM enrichment is best-effort — OSV data still returned
        pass

    return osv_results
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `pytest tests/tools/test_cve_backends.py -v`
Expected: ALL PASS

- [ ] **Step 10: Commit**

```bash
git add tools/cve_backends/ tests/tools/test_cve_backends.py
git commit -m "feat: add pluggable CVE backend system with 5 backends"
```

---

### Task 5: SCA / Dependency Analysis Agent

**Files:**
- Create: `agents/dependency_analysis.py`
- Create: `tests/agents/test_dependency_analysis.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_dependency_analysis.py`:

```python
import json
from unittest.mock import patch, MagicMock
from agents.dependency_analysis import run_dependency_analysis


SAMPLE_REQUIREMENTS = "requests==2.25.1\nflask>=2.0.0\n"

MOCK_CVE_RESULTS = [
    {
        "package": "requests",
        "version": "2.25.1",
        "ecosystem": "PyPI",
        "vulnerabilities": [
            {
                "cve_id": "CVE-2023-32681",
                "summary": "Unintended leak of Proxy-Authorization header",
                "severity": "major",
                "fixed_in": "2.31.0",
                "source": "osv",
            }
        ],
    },
    {
        "package": "flask",
        "version": "2.0.0",
        "ecosystem": "PyPI",
        "vulnerabilities": [],
    },
]

MOCK_LLM_RESPONSE = json.dumps({
    "risk_summary": "1 vulnerable dependency found. requests has a known proxy header leak.",
    "remediation": "Upgrade requests to 2.31.0 or later.",
})


def test_run_dependency_analysis_structured_result(test_db):
    with patch("agents.dependency_analysis.lookup_vulnerabilities", return_value=MOCK_CVE_RESULTS), \
         patch("agents.dependency_analysis.Agent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_LLM_RESPONSE
        mock_agent_cls.return_value = mock_agent

        result = run_dependency_analysis(
            conn=test_db,
            job_id="test-job-1",
            file_path="requirements.txt",
            content=SAMPLE_REQUIREMENTS,
            file_hash="fakehash",
            language="Python",
            custom_prompt=None,
        )

    assert "dependencies" in result
    assert len(result["dependencies"]) == 2
    vuln_pkg = next(d for d in result["dependencies"] if d["package"] == "requests")
    assert len(vuln_pkg["vulnerabilities"]) == 1
    assert "summary" in result


def test_run_dependency_analysis_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="requirements.txt",
                        language="Python", features=["dependency_analysis"])
    cached = {"dependencies": [], "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="dependency_analysis:v1",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached)

    with patch("agents.dependency_analysis.Agent") as mock_cls:
        result = run_dependency_analysis(
            conn=test_db, job_id=job_id,
            file_path="requirements.txt", content="requests==2.25.1",
            file_hash="cached_hash", language="Python", custom_prompt=None,
        )
        mock_cls.assert_not_called()

    assert result["summary"] == "from cache"


def test_run_dependency_analysis_no_dep_file(test_db):
    """Running on a non-dependency file returns empty results."""
    result = run_dependency_analysis(
        conn=test_db,
        job_id="test-job-2",
        file_path="main.py",
        content="print('hello')",
        file_hash="nondep",
        language="Python",
        custom_prompt=None,
    )
    assert result["dependencies"] == []
    assert "No dependency file" in result["summary"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agents/test_dependency_analysis.py -v`
Expected: FAIL — module does not exist

- [ ] **Step 3: Implement the dependency analysis agent**

Create `agents/dependency_analysis.py`:

```python
"""SCA / Dependency Analysis agent — Phase 1.

Two-layer approach:
  Layer 1: Parse dependency file (tools/dependency_parser.py)
  Layer 2: CVE lookup + LLM risk assessment (tools/cve_backends/)
"""

from __future__ import annotations

import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.dependency_parser import parse_dependency_file
from tools.cve_backends import lookup_vulnerabilities
from tools.cache import check_cache, write_cache
from db.queries.history import add_history
from config.settings import get_settings

_SYSTEM_PROMPT = """You are a software supply chain security expert.

You will receive a list of dependencies with their known vulnerability data.
Provide:
1. A prioritized risk summary — which vulnerabilities matter most and why
2. A remediation plan — concrete upgrade steps ordered by priority
3. Assessment of overall supply chain health

Return a JSON object:
{
  "risk_summary": "<prioritized assessment of the most critical findings>",
  "remediation": "<concrete upgrade/migration plan>",
  "summary": "<one sentence count: X dependencies scanned, Y vulnerable, Z outdated>"
}"""

_CACHE_KEY = "dependency_analysis:v1"

# File basenames that are dependency files
_DEP_BASENAMES = {
    "requirements.txt", "pyproject.toml", "setup.cfg", "Pipfile",
    "package.json", "package-lock.json", "yarn.lock",
    "pom.xml", "build.gradle",
    "CMakeLists.txt", "conanfile.txt", "vcpkg.json",
    "packages.config", "Directory.Packages.props",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
}
_DEP_EXTENSIONS = {".csproj"}


def _is_dep_file(file_path: str) -> bool:
    """Check if a file path looks like a dependency file."""
    import os
    basename = os.path.basename(file_path)
    ext = os.path.splitext(basename)[1]
    return basename in _DEP_BASENAMES or ext in _DEP_EXTENSIONS


def run_dependency_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None,
                            custom_prompt: str | None) -> dict:
    """Run SCA on a dependency file."""
    # Skip non-dependency files
    if not _is_dep_file(file_path):
        return {
            "dependencies": [],
            "risk_summary": "",
            "remediation": "",
            "summary": "No dependency file detected — SCA skipped.",
        }

    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    s = get_settings()

    # Layer 1: Parse dependency file
    parsed = parse_dependency_file(file_path, content)
    packages = parsed.get("packages", [])

    if not packages:
        result = {
            "dependencies": [],
            "risk_summary": "No packages found in dependency file.",
            "remediation": "",
            "summary": "0 dependencies found.",
        }
        write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                    file_hash=file_hash, language=language,
                    custom_prompt=custom_prompt, result=result)
        return result

    # Add ecosystem to each package for CVE lookup
    ecosystem = parsed.get("ecosystem", "unknown")
    for pkg in packages:
        pkg.setdefault("ecosystem", ecosystem)

    # Layer 2: CVE lookup
    cve_results = lookup_vulnerabilities(packages, backend=s.sca_cve_backend)

    # Layer 3: LLM risk assessment
    vulnerable_count = sum(1 for r in cve_results if r.get("vulnerabilities"))
    risk_summary = ""
    remediation = ""

    if s.sca_cve_backend != "llm":
        # Only call LLM for summary if not already using llm-only backend
        try:
            model = make_bedrock_model()
            agent = Agent(model=model,
                          system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))
            dep_summary = json.dumps(cve_results, indent=2, default=str)
            raw = str(agent(f"Assess these dependency scan results:\n\n{dep_summary}"))
            parsed_resp = parse_json_response(raw)
            risk_summary = parsed_resp.get("risk_summary", "")
            remediation = parsed_resp.get("remediation", "")
        except Exception:
            risk_summary = f"{vulnerable_count} vulnerable package(s) found."
            remediation = ""

    result = {
        "dependencies": cve_results,
        "risk_summary": risk_summary,
        "remediation": remediation,
        "summary": (f"{len(packages)} dependencies scanned, "
                    f"{vulnerable_count} vulnerable."),
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="dependency_analysis",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_dependency_analysis.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/dependency_analysis.py tests/agents/test_dependency_analysis.py
git commit -m "feat: add SCA dependency analysis agent"
```

---

### Task 6: Deep Secret Scanner Agent (Phase 3)

**Files:**
- Create: `agents/secret_scan.py`
- Create: `tests/agents/test_secret_scan.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_secret_scan.py`:

```python
import json
from unittest.mock import patch, MagicMock
from agents.secret_scan import run_secret_scan

SAMPLE_CODE = '''
import os
config = {
    "db_password": base64.b64decode("c3VwZXJfc2VjcmV0"),
    "api_key": os.getenv("API_KEY", "sk-fallback-1234567890abcdef"),
}
'''

PHASE0_FINDINGS = [
    {"line": 4, "type": "generic_api_key", "match": "sk-f...cdef",
     "confidence": "medium", "context": 'api_key": os.getenv(...)'}
]

MOCK_RESPONSE = json.dumps({
    "secrets": [
        {
            "line": 3,
            "type": "encoded_credential",
            "severity": "critical",
            "description": "Base64-encoded password assigned to config dict",
            "evidence": "base64.b64decode('c3Vw...') decodes to a password",
            "recommendation": "Use a secrets manager",
            "false_positive_risk": "low",
        }
    ],
    "phase0_validation": [
        {
            "line": 4,
            "phase0_type": "generic_api_key",
            "verdict": "confirmed",
            "reason": "Hardcoded fallback value in getenv call",
        }
    ],
    "narrative": "Code contains encoded secrets and hardcoded fallbacks.",
    "summary": "1 secret found, 1 Phase 0 finding confirmed.",
})


def test_run_secret_scan_structured_result(test_db):
    with patch("agents.secret_scan.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_secret_scan(
            conn=test_db,
            job_id="test-job-1",
            file_path="config.py",
            content=SAMPLE_CODE,
            file_hash="fakehash",
            language="Python",
            custom_prompt=None,
            phase0_findings=PHASE0_FINDINGS,
            static_results=None,
        )

    assert "secrets" in result
    assert len(result["secrets"]) == 1
    assert result["secrets"][0]["severity"] == "critical"
    assert "phase0_validation" in result
    assert result["phase0_validation"][0]["verdict"] == "confirmed"


def test_run_secret_scan_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="f.py",
                        language="Python", features=["secret_scan"])
    cached = {"secrets": [], "phase0_validation": [],
              "narrative": "", "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="secret_scan:v1",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached)

    with patch("agents.secret_scan.Agent") as mock_cls:
        result = run_secret_scan(
            conn=test_db, job_id=job_id,
            file_path="f.py", content="x = 1",
            file_hash="cached_hash", language="Python",
            custom_prompt=None, phase0_findings=[], static_results=None,
        )
        mock_cls.assert_not_called()

    assert result["summary"] == "from cache"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agents/test_secret_scan.py -v`
Expected: FAIL — module does not exist

- [ ] **Step 3: Implement the deep secret scan agent**

Create `agents/secret_scan.py`:

```python
"""Deep Secret Scanner agent — Phase 3 (synthesis).

AI-powered detection of secrets that regex-based scanning misses:
encoded credentials, split secrets, hardcoded fallbacks, etc.
"""

from __future__ import annotations

import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a secrets detection specialist performing deep analysis.

You will receive source code along with:
- Phase 0 regex findings (secrets already detected by pattern matching)
- Static analysis results (security issues already flagged)

Your job is to find what regex and static analysis MISSED:
- Base64/hex-encoded secrets
- Secrets assembled across multiple variables (key = prefix + suffix)
- Secrets in string formatting or interpolation
- Hardcoded encryption keys or salts
- Secrets in comments or docstrings
- Environment variable fallbacks to hardcoded values: os.getenv("KEY", "actual-secret")
- Config values that look like placeholders but are actually real credentials

Also validate Phase 0 regex findings — confirm or dismiss each as a false positive.

Return a JSON object:
{
  "secrets": [
    {
      "line": <integer>,
      "type": "<encoded_credential|split_secret|hardcoded_fallback|embedded_key|comment_secret>",
      "severity": "<critical|major|minor>",
      "description": "<what the secret is and why it's a risk>",
      "evidence": "<the suspicious code pattern — mask the actual secret value>",
      "recommendation": "<specific remediation step>",
      "false_positive_risk": "<low|medium|high>"
    }
  ],
  "phase0_validation": [
    {
      "line": <integer>,
      "phase0_type": "<type from Phase 0>",
      "verdict": "<confirmed|false_positive>",
      "reason": "<why you confirm or dismiss this finding>"
    }
  ],
  "narrative": "<overall secrets hygiene assessment>",
  "summary": "<one sentence count>"
}

If no additional secrets are found, return empty lists. Always validate Phase 0 findings."""

_CACHE_KEY = "secret_scan:v1"


def run_secret_scan(conn: duckdb.DuckDBPyConnection, job_id: str,
                    file_path: str, content: str, file_hash: str,
                    language: str | None, custom_prompt: str | None,
                    phase0_findings: list[dict] | None = None,
                    static_results: dict | None = None) -> dict:
    """Run AI-powered deep secret detection."""
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_secrets = []
    all_validations = []
    narratives = []

    # Build context from prior phases
    phase0_ctx = json.dumps(phase0_findings or [], indent=2)
    static_ctx = ""
    if static_results:
        static_security = [
            f for f in static_results.get("semantic_findings", [])
            if f.get("category") == "security"
        ]
        if static_security:
            static_ctx = f"\nStatic analysis security findings: {json.dumps(static_security, indent=2)}"

    for chunk in chunks:
        prompt = (
            f"Language: {language or 'detect from code'}\n"
            f"File: {file_path}\n"
            f"Phase 0 regex findings: {phase0_ctx}\n"
            f"{static_ctx}\n\n"
            f"Source code (lines {chunk['start_line']}-{chunk['end_line']}):\n"
            f"{chunk['content']}"
        )
        raw = str(agent(prompt))
        try:
            parsed = parse_json_response(raw)
            all_secrets.extend(parsed.get("secrets", []))
            all_validations.extend(parsed.get("phase0_validation", []))
            if parsed.get("narrative"):
                narratives.append(parsed["narrative"])
        except (json.JSONDecodeError, ValueError):
            narratives.append(raw)

    # Deduplicate by (line, type)
    seen = set()
    deduped = []
    for secret in all_secrets:
        key = (secret.get("line"), secret.get("type"))
        if key not in seen:
            seen.add(key)
            deduped.append(secret)

    confirmed = sum(1 for v in all_validations if v.get("verdict") == "confirmed")
    dismissed = sum(1 for v in all_validations if v.get("verdict") == "false_positive")

    result = {
        "secrets": deduped,
        "phase0_validation": all_validations,
        "narrative": "\n\n".join(narratives) if narratives else "",
        "summary": (
            f"{len(deduped)} secret(s) found"
            + (f", {confirmed} Phase 0 confirmed" if confirmed else "")
            + (f", {dismissed} dismissed" if dismissed else "")
            + "."
        ),
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="secret_scan",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_secret_scan.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/secret_scan.py tests/agents/test_secret_scan.py
git commit -m "feat: add AI-powered deep secret scanner agent"
```

---

### Task 7: Threat Model Agent (Phase 4)

**Files:**
- Create: `agents/threat_model.py`
- Create: `tests/agents/test_threat_model.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_threat_model.py`:

```python
import json
from unittest.mock import patch, MagicMock
from agents.threat_model import run_threat_model

SAMPLE_CODE = '''
from flask import Flask, request
app = Flask(__name__)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    token = create_jwt(username)
    return {"token": token}
'''

MOCK_FORMAL_RESPONSE = json.dumps({
    "mode": "formal",
    "trust_boundaries": [
        {"id": "TB-1", "description": "User input to login handler",
         "components": ["login()"]}
    ],
    "attack_surface": [
        {"entry_point": "POST /login", "exposure": "public",
         "data_handled": "credentials"}
    ],
    "stride_analysis": [
        {
            "id": "T-001",
            "category": "Spoofing",
            "asset": "user session",
            "threat": "Credential stuffing attack",
            "attack_vector": "Automated POST to /login",
            "likelihood": "high",
            "impact": "high",
            "risk_score": "critical",
            "existing_mitigation": "None observed",
            "recommended_mitigation": "Add rate limiting and CAPTCHA",
            "related_findings": [],
        }
    ],
    "data_flow_mermaid": "flowchart LR\n  User-->|POST /login|Server",
    "summary": "1 threat identified: 1 critical",
})

MOCK_ATTACKER_RESPONSE = json.dumps({
    "mode": "attacker",
    "executive_summary": "Login endpoint is vulnerable to credential attacks.",
    "attack_scenarios": [
        {
            "id": "A-001",
            "title": "Credential stuffing via /login",
            "stride_category": "Spoofing",
            "risk_score": "critical",
            "narrative": "Attacker uses leaked credential lists...",
            "prerequisites": "Public endpoint access",
            "impact": "Full account takeover",
            "proof_of_concept": "for cred in leaked_list: post('/login', cred)",
            "mitigation": "Rate limiting, account lockout, CAPTCHA",
            "related_findings": [],
        }
    ],
    "priority_ranking": ["A-001"],
    "summary": "1 attack scenario identified, 1 critical.",
})


def test_run_threat_model_formal_mode(test_db):
    with patch("agents.threat_model.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_FORMAL_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_threat_model(
            conn=test_db, job_id="test-job-1",
            file_path="app.py", content=SAMPLE_CODE,
            file_hash="fakehash", language="Python",
            custom_prompt=None, threat_model_mode="formal",
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )

    assert result["mode"] == "formal"
    assert "stride_analysis" in result
    assert len(result["stride_analysis"]) == 1
    assert result["stride_analysis"][0]["category"] == "Spoofing"


def test_run_threat_model_attacker_mode(test_db):
    with patch("agents.threat_model.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_ATTACKER_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_threat_model(
            conn=test_db, job_id="test-job-1",
            file_path="app.py", content=SAMPLE_CODE,
            file_hash="fakehash", language="Python",
            custom_prompt=None, threat_model_mode="attacker",
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )

    assert result["mode"] == "attacker"
    assert "attack_scenarios" in result
    assert len(result["attack_scenarios"]) == 1


def test_run_threat_model_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="f.py",
                        language="Python", features=["threat_model"])
    cached = {"mode": "formal", "stride_analysis": [],
              "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="threat_model:v1",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached)

    with patch("agents.threat_model.Agent") as mock_cls:
        result = run_threat_model(
            conn=test_db, job_id=job_id,
            file_path="f.py", content="x=1",
            file_hash="cached_hash", language="Python",
            custom_prompt=None, threat_model_mode="formal",
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )
        mock_cls.assert_not_called()

    assert result["summary"] == "from cache"


def test_run_threat_model_default_mode_is_formal(test_db):
    with patch("agents.threat_model.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_FORMAL_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_threat_model(
            conn=test_db, job_id="test-job-1",
            file_path="app.py", content=SAMPLE_CODE,
            file_hash="fakehash2", language="Python",
            custom_prompt=None, threat_model_mode=None,
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )

    assert result["mode"] == "formal"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agents/test_threat_model.py -v`
Expected: FAIL — module does not exist

- [ ] **Step 3: Implement the threat model agent**

Create `agents/threat_model.py`:

```python
"""SAST / Threat Model agent — Phase 4.

Produces formal STRIDE threat models or attacker-narrative reports.
Consumes findings from all prior phases for maximum context.
"""

from __future__ import annotations

import hashlib
import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_FORMAL_PROMPT = """You are a security architect performing a formal threat model using STRIDE methodology.

You will receive source code and findings from prior analysis agents (bugs, static analysis,
secret scan, dependency analysis). Use ALL of this context to produce a comprehensive threat model.

Analyze the code for:
- Trust boundaries between components
- Attack surface (entry points, data inputs, external interfaces)
- STRIDE threats: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege

For each threat, cross-reference with prior findings when relevant.

Return a JSON object:
{
  "mode": "formal",
  "trust_boundaries": [
    {"id": "TB-N", "description": "<boundary description>", "components": ["<function/class names>"]}
  ],
  "attack_surface": [
    {"entry_point": "<endpoint/function>", "exposure": "<public|internal|authenticated>", "data_handled": "<what data>"}
  ],
  "stride_analysis": [
    {
      "id": "T-NNN",
      "category": "<Spoofing|Tampering|Repudiation|Information Disclosure|Denial of Service|Elevation of Privilege>",
      "asset": "<what is threatened>",
      "threat": "<threat description>",
      "attack_vector": "<how an attacker exploits this>",
      "likelihood": "<high|medium|low>",
      "impact": "<high|medium|low>",
      "risk_score": "<critical|major|minor>",
      "existing_mitigation": "<what defenses exist>",
      "recommended_mitigation": "<what to add>",
      "related_findings": ["<agent:detail>"]
    }
  ],
  "data_flow_mermaid": "<Mermaid flowchart source showing data flow and trust boundaries>",
  "summary": "<count of threats by severity>"
}"""

_ATTACKER_PROMPT = """You are a penetration tester writing an attack assessment report.

Think like a malicious hacker. You will receive source code and findings from prior analysis
agents. Your goal is to identify realistic attack scenarios and explain how to exploit them.

For each scenario, write a clear narrative: how would an attacker discover this, exploit it,
and what damage could they cause? Include proof-of-concept pseudocode where relevant.

Return a JSON object:
{
  "mode": "attacker",
  "executive_summary": "<2-3 sentence overall risk posture>",
  "attack_scenarios": [
    {
      "id": "A-NNN",
      "title": "<attack name>",
      "stride_category": "<STRIDE category>",
      "risk_score": "<critical|major|minor>",
      "narrative": "<step-by-step attack story: discovery, exploitation, impact>",
      "prerequisites": "<what attacker needs>",
      "impact": "<business impact>",
      "proof_of_concept": "<pseudocode or exploit description>",
      "mitigation": "<defensive measures>",
      "related_findings": ["<agent:detail>"]
    }
  ],
  "priority_ranking": ["A-NNN", "..."],
  "summary": "<count of scenarios by severity>"
}"""

_CACHE_KEY = "threat_model:v1"


def _upstream_hash(bug_results: dict | None, static_results: dict | None,
                   secret_results: dict | None, dependency_results: dict | None) -> str:
    """Hash upstream results to invalidate cache when inputs change."""
    raw = json.dumps([
        bug_results.get("summary", "") if bug_results else "",
        static_results.get("summary", "") if static_results else "",
        secret_results.get("summary", "") if secret_results else "",
        dependency_results.get("summary", "") if dependency_results else "",
    ], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def run_threat_model(conn: duckdb.DuckDBPyConnection, job_id: str,
                     file_path: str, content: str, file_hash: str,
                     language: str | None, custom_prompt: str | None,
                     threat_model_mode: str | None = None,
                     bug_results: dict | None = None,
                     static_results: dict | None = None,
                     secret_results: dict | None = None,
                     dependency_results: dict | None = None) -> dict:
    """Run STRIDE or attacker-narrative threat modeling."""
    mode = threat_model_mode or "formal"

    # Augment custom_prompt with upstream hash for cache differentiation
    upstream_h = _upstream_hash(bug_results, static_results,
                                secret_results, dependency_results)
    effective_prompt = f"{custom_prompt or ''}|upstream:{upstream_h}|mode:{mode}"

    cached = check_cache(conn, file_hash, _CACHE_KEY, language, effective_prompt)
    if cached:
        return cached

    system_prompt = _FORMAL_PROMPT if mode == "formal" else _ATTACKER_PROMPT
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, system_prompt))

    # Build context from prior phases
    context_parts = []
    if bug_results and bug_results.get("bugs"):
        bug_summary = [
            f"Line {b.get('line', '?')}: [{b.get('severity', '')}] {b.get('description', '')[:100]}"
            for b in bug_results["bugs"][:10]
        ]
        context_parts.append(f"Bug Analysis findings:\n" + "\n".join(bug_summary))

    if static_results and static_results.get("semantic_findings"):
        static_summary = [
            f"Line {f.get('line', '?')}: [{f.get('category', '')}] {f.get('description', '')[:100]}"
            for f in static_results["semantic_findings"][:10]
        ]
        context_parts.append(f"Static Analysis findings:\n" + "\n".join(static_summary))

    if secret_results and secret_results.get("secrets"):
        secret_summary = [
            f"Line {s.get('line', '?')}: [{s.get('type', '')}] {s.get('description', '')[:100]}"
            for s in secret_results["secrets"][:10]
        ]
        context_parts.append(f"Secret Scan findings:\n" + "\n".join(secret_summary))

    if dependency_results and dependency_results.get("dependencies"):
        vuln_deps = [d for d in dependency_results["dependencies"]
                     if d.get("vulnerabilities")]
        if vuln_deps:
            dep_summary = [
                f"{d['package']} {d.get('version', '?')}: {len(d['vulnerabilities'])} CVE(s)"
                for d in vuln_deps[:10]
            ]
            context_parts.append(f"Dependency Analysis findings:\n" + "\n".join(dep_summary))

    prior_context = "\n\n".join(context_parts) if context_parts else "No prior findings."

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_code = "\n".join(c["content"] for c in chunks)

    prompt = (
        f"Language: {language or 'detect from code'}\n"
        f"File: {file_path}\n"
        f"Threat model mode: {mode}\n\n"
        f"Prior agent findings:\n{prior_context}\n\n"
        f"Source code:\n{all_code}"
    )

    raw = str(agent(prompt))

    try:
        result = parse_json_response(raw)
        result["mode"] = mode  # ensure mode is set
    except (json.JSONDecodeError, ValueError):
        result = {
            "mode": mode,
            "summary": "Threat model generation failed — could not parse response.",
            "narrative": raw,
        }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=effective_prompt, result=result)
    add_history(conn, job_id=job_id, feature="threat_model",
                source_ref=file_path, language=language,
                summary=result.get("summary", ""))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_threat_model.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/threat_model.py tests/agents/test_threat_model.py
git commit -m "feat: add STRIDE/attacker threat model agent"
```

---

### Task 8: Orchestrator Integration

**Files:**
- Modify: `agents/orchestrator.py`
- Modify: `tests/agents/test_orchestrator.py`

- [ ] **Step 1: Write failing test for Phase 0 blocking**

Add to `tests/agents/test_orchestrator.py`:

```python
from unittest.mock import patch, MagicMock


def test_orchestrator_phase0_blocks_on_secrets(test_db):
    """When SECRET_SCAN_MODE=block and secrets found, job is blocked."""
    from db.queries.jobs import create_job, get_job
    from agents.orchestrator import run_analysis

    job_id = create_job(test_db, source_type="local", source_ref="secret.py",
                        language="Python",
                        features=["bug_analysis", "secret_scan"])

    scan_result = {
        "secrets_found": [{"line": 1, "type": "aws_access_key",
                           "match": "AKIA...XXXX", "confidence": "high",
                           "context": "key = AKIA..."}],
        "action_taken": "block",
        "code": "",
    }

    with patch("agents.orchestrator.get_settings") as mock_settings, \
         patch("agents.orchestrator.fetch_local_file") as mock_fetch, \
         patch("agents.orchestrator.scan_secrets", return_value=scan_result):
        s = MagicMock()
        s.enabled_agent_set = frozenset({"bug_analysis", "secret_scan"})
        s.secret_scan_mode = "block"
        s.report_per_file = False
        s.report_consolidated = False
        mock_settings.return_value = s
        mock_fetch.return_value = {"content": 'key = "AKIAIOSFODNN7EXAMPLE"',
                                   "file_hash": "h1"}

        results = run_analysis(test_db, job_id)

    assert "secret_scan_preflight" in results
    assert results["secret_scan_preflight"]["action_taken"] == "block"
    job = get_job(test_db, job_id)
    assert job["status"] == "blocked"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_orchestrator.py::test_orchestrator_phase0_blocks_on_secrets -v`
Expected: FAIL

- [ ] **Step 3: Update orchestrator with Phase 0, Phase 1 SCA, Phase 3 secret scan, Phase 4 threat model**

In `agents/orchestrator.py`, add imports at the top:

```python
from tools.secret_scanner import scan_secrets
from agents.dependency_analysis import run_dependency_analysis
from agents.secret_scan import run_secret_scan
from agents.threat_model import run_threat_model
```

Modify `_run_features_for_file` to add security agents to existing phases and add Phase 4. The key changes:

1. **Before the phase loop** in `run_analysis()`, after `_fetch_files()`, add Phase 0:

```python
        # ── Phase 0: Pre-flight secret scan ──────────────────────────────
        phase0_results = {}
        if "secret_scan" in feat_set:
            _emit(conn, job_id, "phase", message="Phase 0 — Secret Pre-flight")
            for file_info in files:
                scan = scan_secrets(file_info["content"], mode=s.secret_scan_mode)
                phase0_results[file_info["file_path"]] = scan
                if scan["secrets_found"]:
                    _emit(conn, job_id, "start", agent="secret_scan_preflight",
                          file_path=file_info["file_path"],
                          message=f"{len(scan['secrets_found'])} secret(s) detected")
                if scan["action_taken"] == "redact":
                    file_info["content"] = scan["code"]
                elif scan["action_taken"] == "block" and scan["secrets_found"]:
                    results["secret_scan_preflight"] = scan
                    save_job_results(conn, job_id, results)
                    update_job_status(conn, job_id, "blocked")
                    return results
```

2. **In Phase 1** of `_run_features_for_file`, add `dependency_analysis` to the standalone agents dict:

```python
    standalone = {
        "bug_analysis":    run_bug_analysis,
        "static_analysis": run_static_analysis,
        "code_flow":       run_code_flow,
        "requirement":     run_requirement_analysis,
        "dependency_analysis": run_dependency_analysis,
    }
```

3. **In Phase 3**, add `secret_scan` after `comment_generator`:

```python
    if "secret_scan" in feat_set:
        file_results["secret_scan"] = _run_agent(
            conn, job_id, "secret_scan", run_secret_scan, file_path,
            {**common,
             "phase0_findings": phase0_results.get(file_path, {}).get("secrets_found", []),
             "static_results": file_results.get("static_analysis")},
            template_category,
        )
```

4. **Add Phase 4** after Phase 3 in `_run_features_for_file`:

```python
    # ── Phase 4: threat model ────────────────────────────────────────────
    if "threat_model" in feat_set:
        _emit(conn, job_id, "phase", message="Phase 4 — Threat Model")
        threat_kwargs = {
            **common,
            "threat_model_mode": threat_model_mode,
            "bug_results": file_results.get("bug_analysis"),
            "static_results": file_results.get("static_analysis"),
            "secret_results": file_results.get("secret_scan"),
            "dependency_results": file_results.get("dependency_analysis"),
        }
        file_results["threat_model"] = _run_agent(
            conn, job_id, "threat_model", run_threat_model, file_path,
            threat_kwargs, template_category,
        )
```

Update `_run_features_for_file` signature to accept `phase0_results` and `threat_model_mode` parameters.

Update `run_analysis` to pass these through.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agents/test_orchestrator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/orchestrator.py tests/agents/test_orchestrator.py
git commit -m "feat: integrate security agents into orchestrator pipeline"
```

---

### Task 9: Security Selector UI Component

**Files:**
- Create: `app/components/security_selector.py`

- [ ] **Step 1: Create the security selector component**

Create `app/components/security_selector.py`:

```python
"""Sidebar Security Testing section — separate from code analysis features."""

import streamlit as st
from config.settings import get_settings, ALL_AGENTS

SECURITY_FEATURES: dict[str, str] = {
    "secret_scan":          "Secret Scan",
    "dependency_analysis":  "Dependency Analysis",
    "threat_model":         "Threat Model",
}

THREAT_MODEL_MODES = ["Formal (STRIDE)", "Attacker Narrative"]
_MODE_MAP = {"Formal (STRIDE)": "formal", "Attacker Narrative": "attacker"}


def render_security_selector() -> dict:
    """Render security testing checkboxes and options.

    Returns dict with: security_features, threat_model_mode
    """
    s = get_settings()
    enabled = s.enabled_agent_set

    # Only show security section if at least one security agent is enabled
    active_security = {k: v for k, v in SECURITY_FEATURES.items() if k in enabled}
    if not active_security:
        return {"security_features": [], "threat_model_mode": "formal"}

    st.divider()
    st.subheader("Security Testing")

    selected = []
    for key, label in active_security.items():
        if st.checkbox(label, key=f"security_{key}"):
            selected.append(key)

    threat_model_mode = "formal"
    if "threat_model" in selected:
        mode_label = st.selectbox("Threat model mode", THREAT_MODEL_MODES,
                                  key="sidebar_threat_model_mode")
        threat_model_mode = _MODE_MAP.get(mode_label, "formal")

    return {
        "security_features": selected,
        "threat_model_mode": threat_model_mode,
    }
```

- [ ] **Step 2: Integrate into the Analysis page sidebar**

In `app/pages/1_Analysis.py`, add the import:

```python
from app.components.security_selector import render_security_selector
```

In the sidebar block, after `feature_config = render_feature_selector(conn)`, add:

```python
    security_config = render_security_selector()
```

Update the `run_clicked` disabled check to include security features:

```python
    all_features = feature_config["features"] + security_config["security_features"]
    run_clicked = st.button("Run Analysis", type="primary",
                            disabled=not source.get("source_ref") or not all_features)
```

Update the `create_job` call to merge security features:

```python
    job_id = create_job(
        conn,
        source_type=source["source_type"],
        source_ref=source["source_ref"],
        language=feature_config["language"] or None,
        features=feature_config["features"] + security_config["security_features"],
        custom_prompt=feature_config["custom_prompt"],
        template_category=feature_config.get("template_category"),
    )
```

Also add security agent labels to `_AGENT_LABELS`:

```python
    "secret_scan":          "Secret Scan",
    "secret_scan_preflight":"Secret Pre-flight",
    "dependency_analysis":  "Dependency Analysis",
    "threat_model":         "Threat Model",
```

- [ ] **Step 3: Commit**

```bash
git add app/components/security_selector.py app/pages/1_Analysis.py
git commit -m "feat: add security testing selector UI component"
```

---

### Task 10: Security Results UI Component

**Files:**
- Create: `app/components/security_results.py`
- Modify: `app/components/result_tabs.py`

- [ ] **Step 1: Create the security results renderer**

Create `app/components/security_results.py`:

```python
"""Security Testing results — separate tab group below analysis results."""

import json
import streamlit as st

SECURITY_LABELS = {
    "secret_scan":         "Secret Scan",
    "dependency_analysis": "Dependency Analysis",
    "threat_model":        "Threat Model",
}

_SEVERITY_ICON = {"critical": "\U0001f534", "major": "\U0001f7e0", "minor": "\U0001f7e1"}
_RISK_ICON = {"high": "\U0001f534", "medium": "\U0001f7e0", "low": "\U0001f7e2"}


def render_preflight_banner(results: dict) -> None:
    """Show Phase 0 pre-flight secret scan warning banner."""
    preflight = results.get("secret_scan_preflight")
    if not preflight:
        return

    secrets = preflight.get("secrets_found", [])
    action = preflight.get("action_taken", "warn")

    if not secrets:
        return

    if action == "block":
        st.error(
            f"**Security Gate: BLOCKED** — {len(secrets)} secret(s) detected. "
            "Analysis halted to prevent credential exposure. Remove secrets and resubmit."
        )
    elif action == "redact":
        st.warning(
            f"**Security Gate: REDACTED** — {len(secrets)} secret(s) detected and redacted "
            "before analysis. Review findings below."
        )
    else:
        st.warning(
            f"**Security Gate: WARNING** — {len(secrets)} secret(s) detected in submitted code. "
            "Analysis proceeded with original code."
        )

    with st.expander(f"Pre-flight findings ({len(secrets)})"):
        for s in secrets:
            icon = _SEVERITY_ICON.get("critical" if s["confidence"] == "high" else "major", "")
            st.markdown(
                f"{icon} **Line {s['line']}** [{s['type']}] — `{s['match']}`"
            )


def render_security_results(results: dict) -> None:
    """Render security testing result tabs."""
    features = [f for f in SECURITY_LABELS if f in results]
    if not features:
        return

    st.divider()
    st.subheader("Security Testing")

    tabs = st.tabs([SECURITY_LABELS[f] for f in features])
    for tab, feature in zip(tabs, features):
        with tab:
            result = results[feature]
            if not isinstance(result, dict):
                st.json(result)
                continue
            if "error" in result:
                st.error(result["error"])
                continue

            # Download buttons
            c1, c2, _ = st.columns([1, 1, 6])
            c1.download_button(
                "\u2b07 JSON", data=json.dumps(result, indent=2, ensure_ascii=False),
                file_name=f"{feature}_result.json", mime="application/json",
                key=f"dl_json_{feature}",
            )
            c2.download_button(
                "\u2b07 MD", data=_to_markdown(feature, result),
                file_name=f"{feature}_result.md", mime="text/markdown",
                key=f"dl_md_{feature}",
            )
            st.divider()

            if feature == "secret_scan":
                _render_secret_scan(result)
            elif feature == "dependency_analysis":
                _render_dependency_analysis(result)
            elif feature == "threat_model":
                _render_threat_model(result)


def _render_secret_scan(result: dict) -> None:
    secrets = result.get("secrets", [])
    validations = result.get("phase0_validation", [])
    narrative = result.get("narrative", "")

    if narrative:
        with st.container(border=True):
            st.markdown("**Assessment**")
            st.markdown(narrative)

    if not secrets and not validations:
        st.success("No additional secrets found.")
        return

    if result.get("summary"):
        st.caption(result["summary"])

    # Group by severity
    critical = [s for s in secrets if s.get("severity") == "critical"]
    major = [s for s in secrets if s.get("severity") == "major"]
    minor = [s for s in secrets if s.get("severity") == "minor"]

    for group, label in [(critical, "Critical"), (major, "Major"), (minor, "Minor")]:
        if not group:
            continue
        st.subheader(f"{_SEVERITY_ICON.get(label.lower(), '')} {label} ({len(group)})")
        for s in group:
            with st.expander(f"Line {s.get('line', '?')} — {s.get('type', '')}"):
                st.markdown(s.get("description", ""))
                if s.get("evidence"):
                    st.code(s["evidence"])
                if s.get("recommendation"):
                    st.markdown(f"**Recommendation:** {s['recommendation']}")
                fp = s.get("false_positive_risk", "")
                if fp:
                    st.caption(f"False positive risk: {fp}")

    if validations:
        st.subheader("Phase 0 Validation")
        for v in validations:
            icon = "\u2705" if v.get("verdict") == "confirmed" else "\u274c"
            st.markdown(
                f"{icon} Line {v.get('line', '?')} [{v.get('phase0_type', '')}] — "
                f"**{v.get('verdict', '')}**: {v.get('reason', '')}"
            )


def _render_dependency_analysis(result: dict) -> None:
    deps = result.get("dependencies", [])
    risk_summary = result.get("risk_summary", "")
    remediation = result.get("remediation", "")

    if result.get("summary"):
        st.caption(result["summary"])

    if risk_summary:
        with st.container(border=True):
            st.markdown("**Risk Summary**")
            st.markdown(risk_summary)

    if not deps:
        st.info("No dependencies found.")
        return

    vuln_deps = [d for d in deps if d.get("vulnerabilities")]
    safe_deps = [d for d in deps if not d.get("vulnerabilities")]

    if vuln_deps:
        st.subheader(f"\U0001f6a8 Vulnerable ({len(vuln_deps)})")
        for d in vuln_deps:
            vuln_count = len(d["vulnerabilities"])
            with st.expander(f"{d['package']} {d.get('version', '?')} — {vuln_count} CVE(s)"):
                for v in d["vulnerabilities"]:
                    icon = _SEVERITY_ICON.get(v.get("severity", "major"), "")
                    st.markdown(
                        f"{icon} **{v.get('cve_id', '')}** [{v.get('severity', '')}] — "
                        f"{v.get('summary', '')}"
                    )
                    if v.get("fixed_in"):
                        st.markdown(f"Fixed in: `{v['fixed_in']}`")
                    st.caption(f"Source: {v.get('source', '')}")

    if safe_deps:
        with st.expander(f"\u2705 No known vulnerabilities ({len(safe_deps)})"):
            for d in safe_deps:
                st.markdown(f"- {d['package']} {d.get('version', '?')} ({d.get('ecosystem', '')})")

    if remediation:
        with st.container(border=True):
            st.markdown("**Remediation Plan**")
            st.markdown(remediation)


def _render_threat_model(result: dict) -> None:
    mode = result.get("mode", "formal")

    if result.get("summary"):
        st.caption(result["summary"])

    if mode == "formal":
        _render_threat_model_formal(result)
    else:
        _render_threat_model_attacker(result)


def _render_threat_model_formal(result: dict) -> None:
    # Trust boundaries
    boundaries = result.get("trust_boundaries", [])
    if boundaries:
        st.subheader("Trust Boundaries")
        for tb in boundaries:
            st.markdown(f"**{tb.get('id', '')}**: {tb.get('description', '')}")
            if tb.get("components"):
                st.caption("Components: " + ", ".join(f"`{c}`" for c in tb["components"]))

    # Attack surface
    surface = result.get("attack_surface", [])
    if surface:
        st.subheader("Attack Surface")
        for entry in surface:
            exposure_icon = _RISK_ICON.get(
                "high" if entry.get("exposure") == "public" else "low", "")
            st.markdown(
                f"{exposure_icon} **{entry.get('entry_point', '')}** "
                f"[{entry.get('exposure', '')}] — {entry.get('data_handled', '')}"
            )

    # STRIDE analysis
    threats = result.get("stride_analysis", [])
    if threats:
        st.subheader(f"STRIDE Threats ({len(threats)})")
        for t in threats:
            icon = _SEVERITY_ICON.get(t.get("risk_score", "minor"), "")
            with st.expander(f"{icon} {t.get('id', '')} [{t.get('category', '')}] — {t.get('threat', '')[:80]}"):
                st.markdown(f"**Asset:** {t.get('asset', '')}")
                st.markdown(f"**Attack vector:** {t.get('attack_vector', '')}")
                st.markdown(f"**Likelihood:** {t.get('likelihood', '')} | **Impact:** {t.get('impact', '')}")
                if t.get("existing_mitigation"):
                    st.markdown(f"**Existing mitigation:** {t['existing_mitigation']}")
                st.markdown(f"**Recommended:** {t.get('recommended_mitigation', '')}")
                if t.get("related_findings"):
                    st.caption("Related: " + ", ".join(t["related_findings"]))

    # Data flow diagram
    mermaid_src = result.get("data_flow_mermaid", "")
    if mermaid_src:
        st.subheader("Data Flow Diagram")
        from app.components.mermaid_renderer import render_mermaid
        render_mermaid(mermaid_src)


def _render_threat_model_attacker(result: dict) -> None:
    exec_summary = result.get("executive_summary", "")
    if exec_summary:
        with st.container(border=True):
            st.markdown("**Executive Summary**")
            st.markdown(exec_summary)

    scenarios = result.get("attack_scenarios", [])
    ranking = result.get("priority_ranking", [])

    if not scenarios:
        st.success("No attack scenarios identified.")
        return

    # Sort by priority ranking if available
    if ranking:
        rank_map = {sid: i for i, sid in enumerate(ranking)}
        scenarios = sorted(scenarios, key=lambda s: rank_map.get(s.get("id", ""), 999))

    st.subheader(f"Attack Scenarios ({len(scenarios)})")
    for s in scenarios:
        icon = _SEVERITY_ICON.get(s.get("risk_score", "minor"), "")
        with st.expander(f"{icon} {s.get('id', '')} — {s.get('title', '')}"):
            st.markdown(f"**STRIDE:** {s.get('stride_category', '')}")
            st.markdown(f"**Prerequisites:** {s.get('prerequisites', '')}")
            st.markdown(s.get("narrative", ""))
            st.markdown(f"**Impact:** {s.get('impact', '')}")
            if s.get("proof_of_concept"):
                st.markdown("**Proof of Concept:**")
                st.code(s["proof_of_concept"])
            st.markdown(f"**Mitigation:** {s.get('mitigation', '')}")
            if s.get("related_findings"):
                st.caption("Related: " + ", ".join(s["related_findings"]))


# ── Markdown export ──────────────────────────────────────────────────────────

def _to_markdown(feature: str, result: dict) -> str:
    label = SECURITY_LABELS.get(feature, feature)
    lines = [f"# {label}", ""]

    if feature == "secret_scan":
        lines.append(result.get("summary", ""))
        for s in result.get("secrets", []):
            lines += [
                f"## Line {s.get('line', '?')} — {s.get('type', '')} [{s.get('severity', '')}]",
                s.get("description", ""),
                f"**Recommendation:** {s.get('recommendation', '')}",
                "",
            ]
    elif feature == "dependency_analysis":
        lines.append(result.get("summary", ""))
        if result.get("risk_summary"):
            lines += ["", "## Risk Summary", result["risk_summary"], ""]
        for d in result.get("dependencies", []):
            if d.get("vulnerabilities"):
                lines.append(f"### {d['package']} {d.get('version', '?')}")
                for v in d["vulnerabilities"]:
                    lines.append(f"- **{v.get('cve_id', '')}** [{v.get('severity', '')}]: {v.get('summary', '')}")
                lines.append("")
        if result.get("remediation"):
            lines += ["## Remediation", result["remediation"]]
    elif feature == "threat_model":
        lines.append(result.get("summary", ""))
        if result.get("mode") == "formal":
            for t in result.get("stride_analysis", []):
                lines += [
                    f"## {t.get('id', '')} [{t.get('category', '')}] — {t.get('threat', '')}",
                    f"**Risk:** {t.get('risk_score', '')} | **Likelihood:** {t.get('likelihood', '')} | **Impact:** {t.get('impact', '')}",
                    f"**Mitigation:** {t.get('recommended_mitigation', '')}",
                    "",
                ]
            if result.get("data_flow_mermaid"):
                lines += ["## Data Flow", "```mermaid", result["data_flow_mermaid"], "```"]
        else:
            if result.get("executive_summary"):
                lines += ["## Executive Summary", result["executive_summary"], ""]
            for s in result.get("attack_scenarios", []):
                lines += [
                    f"## {s.get('id', '')} — {s.get('title', '')}",
                    f"**Risk:** {s.get('risk_score', '')}",
                    s.get("narrative", ""),
                    f"**Mitigation:** {s.get('mitigation', '')}",
                    "",
                ]

    return "\n".join(lines)
```

- [ ] **Step 2: Integrate security results into the Analysis page**

In `app/pages/1_Analysis.py`, add the import:

```python
from app.components.security_results import render_security_results, render_preflight_banner
```

In the `status == "completed"` block, after `render_results(results, ...)`:

```python
        render_preflight_banner(results)
        render_security_results(results)
```

In the `status == "blocked"` handling (add a new elif before "failed"):

```python
elif status == "blocked":
    results = get_job_results(conn, job_id) or {}
    render_preflight_banner(results)
    st.warning("Analysis was blocked by the security pre-flight scanner. "
               "Remove detected secrets and resubmit, or change SECRET_SCAN_MODE in settings.")
    if st.button("Clear and start over"):
        del st.session_state["current_job_id"]
        st.rerun()
```

Also add `"blocked"` to `STATUS_LABEL`:

```python
STATUS_LABEL = {
    "pending":   "Queued...",
    "running":   "Analyzing...",
    "completed": "Complete",
    "failed":    "Failed",
    "blocked":   "Blocked — secrets detected",
}
```

- [ ] **Step 3: Add security report suffixes to result_tabs.py**

In `app/components/result_tabs.py`, add to `_FEATURE_SUFFIX`:

```python
    "secret_scan":          "_secret_scan.md",
    "dependency_analysis":  "_dependency_analysis.md",
    "threat_model":         "_threat_model.md",
```

Add to `FEATURE_LABELS`:

```python
    "secret_scan":         "Secret Scan",
    "dependency_analysis": "Dependency Analysis",
    "threat_model":        "Threat Model",
```

- [ ] **Step 4: Commit**

```bash
git add app/components/security_results.py app/components/security_selector.py app/pages/1_Analysis.py app/components/result_tabs.py
git commit -m "feat: add security testing UI components and page integration"
```

---

### Task 11: Settings Page — Security Section

**Files:**
- Modify: `app/pages/5_Settings.py`

- [ ] **Step 1: Add security settings section**

At the end of `app/pages/5_Settings.py`, before the Database section, add:

```python
# ── Security Testing ──────────────────────────────────────────
st.header("Security Testing")
st.text_input("Secret Scan Mode", value=s.secret_scan_mode, disabled=True,
              help="Set via SECRET_SCAN_MODE in .env. Values: block, redact, warn")
st.text_input("SCA CVE Backend", value=s.sca_cve_backend, disabled=True,
              help="Set via SCA_CVE_BACKEND in .env. Values: osv, nvd, github, llm, osv_llm")
st.text_input("SCA Auto-Discover", value=str(s.sca_auto_discover), disabled=True,
              help="Set via SCA_AUTO_DISCOVER in .env. Auto-discover dependency files from repo")
st.text_input("NVD API Key", value="••••••" if s.nvd_api_key else "(not set)", disabled=True,
              help="Set via NVD_API_KEY in .env. Required for NVD backend")
```

- [ ] **Step 2: Commit**

```bash
git add app/pages/5_Settings.py
git commit -m "feat: add security testing settings to Settings page"
```

---

### Task 12: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add httpx dependency note**

`httpx` is already in `requirements.txt`. No new dependencies needed — the CVE backends use `httpx` (already present), `xml.etree.ElementTree` (stdlib), and `json` (stdlib).

Verify:

Run: `grep httpx requirements.txt`
Expected: `httpx>=0.28.1`

- [ ] **Step 2: Commit (skip if no changes)**

No commit needed — no new dependencies required.

---

### Task 13: End-to-End Smoke Test

**Files:**
- Create: `tests/integration/test_security_flow.py`

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_security_flow.py`:

```python
"""Smoke test for the security testing pipeline."""

import json
from unittest.mock import patch, MagicMock
from db.queries.jobs import create_job, get_job
from agents.orchestrator import run_analysis


SAMPLE_CODE_WITH_SECRET = '''
import os
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
password = os.getenv("DB_PASS", "fallback_secret_123")

def connect():
    return {"host": "db.example.com", "password": password}
'''


def test_full_security_pipeline_warn_mode(test_db, monkeypatch):
    """Full pipeline: Phase 0 warn → Phase 1 (no dep file) → Phase 3 → Phase 4."""
    monkeypatch.setenv("SECRET_SCAN_MODE", "warn")
    monkeypatch.setenv("SCA_CVE_BACKEND", "llm")

    from config.settings import get_settings
    get_settings.cache_clear()

    job_id = create_job(
        test_db,
        source_type="local",
        source_ref="app.py",
        language="Python",
        features=["secret_scan", "threat_model"],
    )

    mock_secret_response = json.dumps({
        "secrets": [{"line": 4, "type": "hardcoded_fallback", "severity": "major",
                      "description": "Hardcoded fallback in getenv",
                      "evidence": "os.getenv(..., 'fallback_secret_123')",
                      "recommendation": "Remove fallback", "false_positive_risk": "low"}],
        "phase0_validation": [{"line": 3, "phase0_type": "aws_access_key",
                               "verdict": "confirmed", "reason": "Real AWS key format"}],
        "narrative": "Secrets found.", "summary": "1 secret, 1 confirmed.",
    })

    mock_threat_response = json.dumps({
        "mode": "formal",
        "trust_boundaries": [],
        "attack_surface": [{"entry_point": "connect()", "exposure": "internal",
                            "data_handled": "credentials"}],
        "stride_analysis": [{"id": "T-001", "category": "Information Disclosure",
                             "asset": "database password", "threat": "Credential exposure",
                             "attack_vector": "Source code access",
                             "likelihood": "high", "impact": "high",
                             "risk_score": "critical",
                             "existing_mitigation": "None",
                             "recommended_mitigation": "Use secrets manager",
                             "related_findings": ["secret_scan:line_3"]}],
        "data_flow_mermaid": "",
        "summary": "1 critical threat.",
    })

    mock_agent = MagicMock()
    mock_agent.side_effect = [mock_secret_response, mock_threat_response]

    with patch("agents.secret_scan.Agent", return_value=mock_agent), \
         patch("agents.threat_model.Agent", return_value=mock_agent), \
         patch("agents.orchestrator.fetch_local_file",
               return_value={"content": SAMPLE_CODE_WITH_SECRET, "file_hash": "test123"}):
        results = run_analysis(test_db, job_id)

    job = get_job(test_db, job_id)
    assert job["status"] == "completed"
    assert "secret_scan" in results or "threat_model" in results
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_security_flow.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: ALL PASS — no regressions

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_security_flow.py
git commit -m "test: add security pipeline integration smoke test"
```

---

### Task 14: Manual UI Verification

- [ ] **Step 1: Start the app**

Run: `streamlit run app/Home.py`

- [ ] **Step 2: Verify security section appears in sidebar**

Navigate to the Analysis page. Below the Features section, confirm:
- "Security Testing" section with divider
- Secret Scan, Dependency Analysis, Threat Model checkboxes
- Threat Model mode dropdown appears when Threat Model is checked

- [ ] **Step 3: Verify Settings page shows security settings**

Navigate to Settings page. Confirm security testing section displays:
- Secret Scan Mode
- SCA CVE Backend
- SCA Auto-Discover
- NVD API Key

- [ ] **Step 4: Test with a file containing secrets**

Submit a local file with a hardcoded secret. With Secret Scan enabled:
- Phase 0 banner should appear
- Secret Scan tab should show AI findings
- If Threat Model is also enabled, it should reference secret findings

- [ ] **Step 5: Commit any fixes found during manual testing**

```bash
git add -A
git commit -m "fix: address issues found during manual security UI testing"
```
