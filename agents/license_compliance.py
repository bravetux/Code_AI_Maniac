import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "license_compliance"

_SYSTEM_PROMPT = """You are a software licensing and compliance expert analysing code and its
dependencies for license compliance issues.

Analyse the code for license-related concerns and produce a markdown report:

## License Detection
### File-Level License Indicators
- License headers or comments found in the file
- Copyright notices
- SPDX identifiers

### Dependency Licenses
If the file contains dependency declarations (requirements.txt, package.json, pom.xml,
go.mod, Cargo.toml, etc.), analyse each dependency:
| Package | Version | License | Category | Compatibility |
Category: Permissive / Weak Copyleft / Strong Copyleft / Proprietary / Unknown
Compatibility: Compatible / Review Required / Incompatible / Unknown

If the file is source code (not a manifest), analyse imported packages and infer
likely licenses where possible.

## License Compatibility Matrix
Check compatibility between detected licenses:
- Can these licenses coexist in the same project?
- Are there copyleft obligations that propagate?
- Distribution implications (binary vs. source)

## Compliance Issues
For each issue:
### Issue N: [Title] (Severity: Critical/Major/Minor)
- **Package/File**: What is affected
- **License**: The problematic license
- **Problem**: Why this is a compliance risk
- **Obligation**: What the license requires (attribution, source disclosure, etc.)
- **Remediation**: How to resolve (replace package, add attribution, etc.)

Common issues to flag:
- GPL/AGPL dependencies in proprietary projects
- Missing attribution for MIT/BSD/Apache licensed code
- License-incompatible combinations
- Dependencies with no license (legally risky)
- SSPL or other controversial licenses
- Copy-pasted code with license obligations

## Attribution Requirements
List all packages/code that require attribution:
| Package | License | Attribution Required |

## Policy Recommendations
- Suggested license policy for this project
- Packages to replace if adopting a specific policy
- License scanning tool recommendations

Guidelines:
- Be conservative — flag uncertainty as "Review Required"
- Distinguish between development-only and production dependencies
- Consider the project's likely distribution model
- Note that license detection from code analysis is best-effort — recommend
  verification with actual LICENSE files"""


def run_license_compliance(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Analyse license compliance for this code{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"License compliance analysis for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
