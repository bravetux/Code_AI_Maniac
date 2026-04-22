# Security Testing Agents — Design Spec

**Date:** 2026-04-14
**Status:** Approved
**Scope:** Add a Security Testing section to AI Arena with three new agents and a pre-flight scanner

---

## 1. Overview

Add four security components to the AI Arena platform:

1. **Pre-flight Secret Scanner (Phase 0)** — regex-based gate that scans code before any agent touches it
2. **SCA / Dependency Analyzer (Phase 1)** — multi-ecosystem dependency vulnerability scanner
3. **Deep Secret Scanner (Phase 3)** — AI-powered secret detection in the synthesis phase
4. **SAST / Threat Modeler (Phase 4)** — STRIDE and attacker-narrative threat modeling

These integrate into the existing orchestrator's phased pipeline using Approach 3 ("Security Woven Into Phases"), placing each component where it's most effective.

---

## 2. Architecture — Pipeline Phases

```
Phase 0 (NEW)  : Pre-flight regex secret scan → gate/redact/warn
Phase 1 (EXT)  : Foundation agents + SCA agent (no cross-dependencies)
Phase 2 (SAME) : Context-aware agents (code_design, mermaid) — unchanged
Phase 3 (EXT)  : Synthesis agents + deep AI secret scan
Phase 4 (NEW)  : Threat model agent (consumes all prior findings)
```

Data flow:

```
Source Files
    │
    ▼
┌──────────────────────┐
│  Phase 0: Secret     │──→ block / redact / warn
│  Scanner (regex)     │    (configurable via SECRET_SCAN_MODE)
└──────────┬───────────┘
           │ code (original or redacted)
           ▼
┌──────────────────────┐
│  Phase 1: Foundation │
│  ├─ bug_analysis     │
│  ├─ static_analysis  │
│  ├─ code_flow        │
│  ├─ requirement      │
│  └─ dependency_analysis (NEW) ← auto-discovered dep files
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Phase 2: Context    │
│  ├─ code_design      │  (unchanged)
│  └─ mermaid          │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Phase 3: Synthesis  │
│  ├─ comment_generator│
│  └─ secret_scan (NEW)│ ← receives static_analysis + Phase 0 findings
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Phase 4: Threat     │
│  Model (NEW)         │ ← receives bug, static, secret, SCA findings
└──────────────────────┘
```

---

## 3. Component Designs

### 3.1 Pre-flight Secret Scanner (Phase 0)

**Type:** Tool (no LLM)
**File:** `tools/secret_scanner.py`

**Pattern library** — built-in regex patterns covering:
- AWS keys (`AKIA...`)
- Azure keys, GCP service account JSON
- Generic API keys/tokens (`api_key`, `secret`, `bearer`, `authorization`)
- Private keys (RSA/EC/PGP headers)
- Connection strings (database URLs with passwords, Redis, AMQP)
- JWT tokens, GitHub/GitLab/Bitbucket tokens
- Hardcoded passwords in assignment patterns (`password = "..."`)

**Behavior modes** (controlled by `SECRET_SCAN_MODE` in `.env`, default `warn`):

| Mode     | Behavior                                                                 |
|----------|--------------------------------------------------------------------------|
| `block`  | Halt analysis, return findings, refuse to send to Bedrock                |
| `redact` | Replace detected secrets with `[REDACTED-<type>]`, warn via banner, proceed |
| `warn`   | Show warning banner with findings, proceed with original code (default)  |

**Output schema:**

```json
{
  "secrets_found": [
    {
      "line": 42,
      "type": "aws_access_key",
      "match": "AKIA...XXXX",
      "confidence": "high|medium",
      "context": "line content with secret masked"
    }
  ],
  "action_taken": "block|redact|warn",
  "code": "<original or redacted content>"
}
```

**Integration:** Called in `run_analysis()` after `_fetch_files()`, before any agent. If mode is `block` and secrets found, job status is set to `blocked`.

---

### 3.2 SCA / Dependency Analyzer Agent (Phase 1)

**Type:** Strands Agent (two-layer: tool + LLM)
**Files:** `agents/dependency_analysis.py`, `tools/dependency_parser.py`, `tools/cve_backends/`

**Layer 1 — Dependency Parser** (`tools/dependency_parser.py`):

Pure Python parsing. Extracts package names and version constraints.

| Ecosystem   | Files Parsed                                            | CVE Ecosystem ID |
|-------------|---------------------------------------------------------|------------------|
| Python      | `requirements.txt`, `pyproject.toml`, `setup.cfg`, `Pipfile` | PyPI             |
| JavaScript  | `package.json`, `package-lock.json`, `yarn.lock`        | npm              |
| Java        | `pom.xml`, `build.gradle`                               | Maven            |
| C/C++       | `CMakeLists.txt`, `conanfile.txt`, `vcpkg.json`         | — (NVD/LLM only) |
| C#          | `*.csproj`, `packages.config`, `Directory.Packages.props` | NuGet            |
| Go          | `go.mod`, `go.sum`                                      | Go               |
| Rust        | `Cargo.toml`, `Cargo.lock`                              | crates.io        |

**Layer 2 — CVE Backends** (`tools/cve_backends/`):

Each backend exposes `lookup_vulnerabilities(packages: list[dict]) -> list[dict]`.

| Backend              | Setting Value | Needs Key?                          |
|----------------------|---------------|-------------------------------------|
| OSV.dev API          | `osv`         | No                                  |
| NVD API              | `nvd`         | Yes (`NVD_API_KEY`)                 |
| GitHub Advisory DB   | `github`      | Uses existing `GITHUB_TOKEN`        |
| LLM-only             | `llm`         | No                                  |
| OSV + LLM hybrid     | `osv_llm`     | No (default)                        |

Backend selected via `SCA_CVE_BACKEND` in `.env` (default: `osv_llm`).

**Auto-discovery** (`SCA_AUTO_DISCOVER` in `.env`, default `true`):
- GitHub/Gitea sources: fetches known dependency filenames from repo root via existing fetch tools
- Local sources: scans parent directory of submitted files for dependency files
- Disabled when `false` — only runs if user explicitly submits dependency files

**Output schema:**

```json
{
  "dependencies": [
    {
      "name": "requests",
      "version": "2.25.1",
      "latest": "2.31.0",
      "ecosystem": "PyPI",
      "outdated": true,
      "vulnerabilities": [
        {
          "cve_id": "CVE-2023-32681",
          "severity": "major",
          "summary": "...",
          "fixed_in": "2.31.0",
          "source": "osv"
        }
      ]
    }
  ],
  "risk_summary": "<LLM-generated prioritized assessment>",
  "remediation": "<LLM-generated upgrade plan>",
  "summary": "12 dependencies scanned, 3 vulnerable, 5 outdated."
}
```

**Orchestrator:** Runs in Phase 1 alongside foundation agents. No dependencies on other agents.

---

### 3.3 Deep Secret Scanner Agent (Phase 3)

**Type:** Strands Agent
**File:** `agents/secret_scan.py`

**Why Phase 3:** Receives `static_analysis` findings to avoid duplicate flags. Focuses on what regex and static analysis missed.

**Detection focus:**
- Base64/hex-encoded secrets
- Secrets assembled across multiple variables (`key = prefix + suffix`)
- Secrets in string formatting/interpolation
- Config files with placeholder values that look like real credentials
- Hardcoded encryption keys or salts
- Secrets in comments or docstrings
- Environment variable fallbacks to hardcoded values (`os.getenv("KEY", "actual-secret-here")`)
- Validation of Phase 0 regex hits — confirm or dismiss as false positives

**Inputs:**
- File content (original or redacted from Phase 0)
- Phase 0 regex findings
- `static_analysis` results

**Output schema:**

```json
{
  "secrets": [
    {
      "line": 15,
      "type": "encoded_credential",
      "severity": "critical|major|minor",
      "description": "Base64-encoded AWS secret key assigned to config variable",
      "evidence": "<the suspicious code pattern, secret value masked>",
      "recommendation": "Move to environment variable or secrets manager",
      "false_positive_risk": "low|medium|high"
    }
  ],
  "phase0_validation": [
    {
      "line": 42,
      "phase0_type": "aws_access_key",
      "verdict": "confirmed|false_positive",
      "reason": "This is a test fixture key used only in unit tests"
    }
  ],
  "narrative": "<overall secrets hygiene assessment>",
  "summary": "3 secret(s) found, 1 Phase 0 finding confirmed, 1 dismissed as false positive."
}
```

**Caching:** Key `secret_scan:v1`, uses standard `check_cache`/`write_cache`.

---

### 3.4 SAST / Threat Model Agent (Phase 4)

**Type:** Strands Agent
**File:** `agents/threat_model.py`

**Why Phase 4:** Consumes all prior findings to produce the most informed threat assessment.

**Two output modes** (user-selectable via `threat_model_mode` dropdown):

#### Formal Mode (STRIDE)

```json
{
  "mode": "formal",
  "trust_boundaries": [
    {
      "id": "TB-1",
      "description": "User input to API handler",
      "components": ["parse_request()", "validate_input()"]
    }
  ],
  "attack_surface": [
    {
      "entry_point": "REST endpoint /api/upload",
      "exposure": "public",
      "data_handled": "user files"
    }
  ],
  "stride_analysis": [
    {
      "id": "T-001",
      "category": "Spoofing|Tampering|Repudiation|Information Disclosure|Denial of Service|Elevation of Privilege",
      "asset": "session token",
      "threat": "Attacker replays stolen JWT to impersonate user",
      "attack_vector": "Token extracted from logs or browser storage",
      "likelihood": "high|medium|low",
      "impact": "high|medium|low",
      "risk_score": "critical|major|minor",
      "existing_mitigation": "Token has 24h expiry",
      "recommended_mitigation": "Add token binding to client IP, reduce expiry to 1h",
      "related_findings": ["bug_analysis:line_42", "secret_scan:line_15"]
    }
  ],
  "data_flow_mermaid": "<Mermaid DFD source showing trust boundaries>",
  "summary": "12 threats identified: 2 critical, 4 major, 6 minor"
}
```

#### Attacker Mode

```json
{
  "mode": "attacker",
  "executive_summary": "<2-3 sentence overall risk posture>",
  "attack_scenarios": [
    {
      "id": "A-001",
      "title": "Credential theft via log injection",
      "stride_category": "Information Disclosure",
      "risk_score": "critical|major|minor",
      "narrative": "<step-by-step how an attacker would exploit this>",
      "prerequisites": "Access to application logs",
      "impact": "Full account takeover",
      "proof_of_concept": "<pseudocode or description of exploit steps>",
      "mitigation": "<specific defensive measures>",
      "related_findings": ["static_analysis:line_88", "secret_scan:line_15"]
    }
  ],
  "priority_ranking": ["A-003", "A-001", "A-002"],
  "summary": "5 attack scenarios identified, 1 critical chain found"
}
```

**Inputs:**
- File content
- `bug_analysis` results
- `static_analysis` results
- `secret_scan` results
- `dependency_analysis` results

**Caching:** Key `threat_model:v1`. The `custom_prompt` parameter passed to `write_cache` is augmented with a hash of the serialized upstream results (bug_analysis + static_analysis + secret_scan + dependency_analysis). This ensures a re-run with different upstream findings invalidates the cache, while reusing the existing cache infrastructure unchanged.

---

## 4. UI Integration

### 4.1 Sidebar — Security Testing Section

Separate collapsible section below existing "Features", with `st.divider()` + `st.subheader("Security Testing")`.

**File:** `app/components/security_selector.py`

Controls:
- **Secret Scan** checkbox — enables Phase 0 + Phase 3 as a pair
- **Dependency Analysis** checkbox
- **Threat Model** checkbox
  - Sub-dropdown: `Formal (STRIDE)` / `Attacker Narrative`

### 4.2 Pre-flight Banner

When Phase 0 finds secrets, a warning/error banner appears at the top of the results area before any tabs:
- Count and types of secrets found
- Action taken (blocked/redacted/warned)
- Expandable detail with line numbers and masked values

### 4.3 Result Tabs — Security Group

Security results in a separate `st.tabs()` group below existing analysis tabs:

```
[Bug Analysis] [Code Design] [Code Flow] [Mermaid] [Requirements] [Static Analysis] [PR Comments]

── Security Testing ──
[Secret Scan] [Dependency Analysis] [Threat Model]
```

**File:** `app/components/security_results.py`

Tab renderers:
- **Secret Scan:** severity-grouped list (like bug_analysis) + Phase 0 validation verdicts
- **Dependency Analysis:** table of dependencies with vulnerability badges, expandable CVE details
- **Threat Model (Formal):** STRIDE table with expandable threat cards + embedded Mermaid DFD
- **Threat Model (Attacker):** ranked attack scenario cards with expandable narratives

### 4.4 Reports

Security findings included in per-file and consolidated reports. New suffixes:
- `_secret_scan.md`
- `_dependency_analysis.md`
- `_threat_model.md`

---

## 5. Configuration

### 5.1 New Settings in `config/settings.py`

Added to the `Settings` class:

| Setting            | Type   | Default    | Values                             |
|--------------------|--------|------------|------------------------------------|
| `secret_scan_mode` | `str`  | `warn`     | `block`, `redact`, `warn`          |
| `sca_cve_backend`  | `str`  | `osv_llm`  | `osv`, `nvd`, `github`, `llm`, `osv_llm` |
| `sca_auto_discover`| `bool` | `true`     | `true`, `false`                    |
| `nvd_api_key`      | `str`  | `""`       | API key (required for `nvd` backend) |

### 5.2 Agent Registry

`ALL_AGENTS` in `config/settings.py` gains three entries:

```python
ALL_AGENTS: frozenset[str] = frozenset({
    # existing...
    "secret_scan",
    "dependency_analysis",
    "threat_model",
})
```

Controlled by `ENABLED_AGENTS` the same as existing agents.

---

## 6. File Structure

### New Files

```
tools/
  secret_scanner.py              # Phase 0 regex engine
  dependency_parser.py           # Dependency file parsing (all ecosystems)
  cve_backends/
    __init__.py                  # Backend registry + dispatcher
    osv.py                       # OSV.dev API client
    nvd.py                       # NVD API client
    github_advisory.py           # GitHub Advisory DB client
    llm_only.py                  # Bedrock-only CVE assessment
    hybrid.py                    # OSV + LLM combined

agents/
  secret_scan.py                 # Phase 3 deep AI secret scanner
  dependency_analysis.py         # Phase 1 SCA agent
  threat_model.py                # Phase 4 threat model agent

app/
  components/
    security_selector.py         # Sidebar security section
    security_results.py          # Security tab group rendering
```

### Modified Files

```
config/settings.py               # New settings + 3 agent keys in ALL_AGENTS
agents/orchestrator.py           # Phase 0 + Phase 1 SCA + Phase 3 secret scan + Phase 4 threat model
app/components/feature_selector.py  # Import/render security_selector
app/components/result_tabs.py    # Security result group + report suffixes + markdown export
app/pages/1_Analysis.py          # Wire security selector + security results
app/pages/5_Settings.py          # Security settings UI
```

### Unchanged

- Existing agent files
- Phase 2 logic
- Database schema (security results use same `results` JSON blob)
- Cache/history infrastructure
