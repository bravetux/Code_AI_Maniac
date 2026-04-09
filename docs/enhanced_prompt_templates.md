# Enhanced Prompt Templates Reference Guide

## Overview

Enhanced prompt templates are a system of 40 pre-built analysis frameworks that extend an agent's capabilities without replacing its core instructions. They operate in **append mode**, meaning the template text is prepended to any custom prompt the user provides, allowing templates to work seamlessly with presets and user-defined prompts.

### How Templates Work

1. **Append Mode (Default):** When a template is applied, its expert analysis framework is appended to the agent's system prompt. Both the template guidance and the user's custom prompt (if any) are combined, giving the agent richer context.

2. **Three-State System:**
   - **Template + No Custom Prompt:** Agent receives the template text with the append marker (`__append__`)
   - **Template + Custom Prompt (append mode):** Template text is prepended to the custom prompt
   - **Template + Custom Prompt (overwrite mode):** User's custom prompt wins; template is ignored

3. **Overwrite Priority:** Users can explicitly enable overwrite mode to disable templates and use only their custom prompt. This preserves full control while making templates the default enhancement.

### When to Use Templates

- **Deep Analysis:** Complex code requiring comprehensive multi-pass investigation or architectural reconstruction
- **Security Focused:** Code handling sensitive data, authentication, or compliance requirements
- **Architecture Reverse Engineering:** Understanding system design, dependencies, and technical decisions
- **Quick Scan:** Time-constrained analysis where speed prioritises over comprehensiveness
- **Report Generator:** Formal documentation for audits, stakeholder reviews, or compliance

---

## Category 1: Deep Analysis

Multi-pass chain-of-thought analysis with comprehensive coverage. Designed for thorough investigation of code quality, design, and risks.

| Agent | Description |
|-------|-------------|
| **bug_analysis** | Multi-pass chain-of-thought bug analysis with root-cause tracing (surface scan → assumption audit → failure modes → interaction analysis → synthesis) |
| **code_design** | SOLID audit, coupling matrix, and evolutionary architecture assessment with brutally honest design critique |
| **code_flow** | Debugger-precision flow tracing with state machines and data lineage, function-name accuracy required |
| **mermaid** | Information-dense diagrams with validated nodes, error paths, and edge labels |
| **requirement** | Formal specification with behavioural contracts, traceability matrix, and testable requirements |
| **static_analysis** | Semantic type analysis, temporal coupling, and resource lifecycle audit going beyond automated tools |
| **comment_generator** | Mentoring-style PR reviews that teach underlying principles rather than just flagging issues |
| **commit_analysis** | Forensic commit archaeology with narrative reconstruction and risk pattern detection |

---

## Category 2: Security Focused

Security-lens analysis using threat modelling frameworks. Designed for systems handling sensitive data, authentication, or compliance requirements.

| Agent | Description |
|-------|-------------|
| **bug_analysis** | STRIDE threat model + OWASP Top 10 security audit with attack complexity and impact ratings |
| **code_design** | Trust boundaries, defence in depth, and threat modelling with cryptographic assessment |
| **code_flow** | Taint propagation analysis, authentication/authorisation flow, and secret tracking |
| **mermaid** | Trust boundary diagrams with attack surface indicators and data sensitivity labels |
| **requirement** | Security requirements extraction with authentication, authorisation, and compliance gap analysis |
| **static_analysis** | Injection, authentication, cryptographic, and CWE-referenced vulnerability audit |
| **comment_generator** | Security-first PR review with exploitability ratings and new attack surface detection |
| **commit_analysis** | Credential hygiene, dependency risk, and security posture trending analysis |

---

## Category 3: Architecture Reverse Engineering

Design archaeology and pattern recognition. Reconstructs system architecture, identifies design patterns, and tracks evolution.

| Agent | Description |
|-------|-------------|
| **bug_analysis** | Bugs as symptoms of architectural decisions with pattern violation detection |
| **code_design** | Full architecture reconstruction with Architecture Decision Records (ADRs) and pattern catalogue |
| **code_flow** | System-level flow with failure domains, scalability bottlenecks, and cross-cutting concerns |
| **mermaid** | C4-style architecture diagrams with pattern annotations and dependency direction validation |
| **requirement** | Quality attributes, integration contracts, and constraint archaeology for system rebuilding |
| **static_analysis** | Modularity assessment, abstraction quality scoring, and dependency health metrics |
| **comment_generator** | Architecture-impact PR review with evolution assessment and technical debt tracking |
| **commit_analysis** | Architecture evolution tracking and design decision trail reconstruction |

---

## Category 4: Quick Scan

Rapid triage analysis prioritising speed and top findings. Designed for time-constrained reviews and executive summaries.

| Agent | Description |
|-------|-------------|
| **bug_analysis** | Rapid triage: top 3-5 critical findings only with RED/AMBER/GREEN traffic-light rating |
| **code_design** | 500-word architectural snapshot with top 3 strengths and concerns |
| **code_flow** | Concise 10-step flow summary with key decision points for quick understanding |
| **mermaid** | Minimal 10-node diagram designed for 10-second comprehension |
| **requirement** | Top 5-10 core requirements with implementation status (fully/partially/not) |
| **static_analysis** | Critical findings only with traffic-light quality rating A-F and single most important fix |
| **comment_generator** | 3-5 critical comments with one-paragraph summary and GO/NO-GO recommendation |
| **commit_analysis** | 300-word release readiness snapshot with risk signals |

---

## Category 5: Report Generator

Formal, publication-quality documentation. Designed for compliance audits, leadership reviews, and operational handoff.

| Agent | Description |
|-------|-------------|
| **bug_analysis** | Formal audit report with severity matrix, risk plot, and remediation plan with effort estimates |
| **code_design** | Architecture review document with component table, 1-5 quality scores, and technical debt register |
| **code_flow** | Operations-grade flow documentation with monitoring points and recovery procedures |
| **mermaid** | Presentation-quality diagrams with professional styling and title annotations |
| **requirement** | IEEE 830-inspired Software Requirements Specification with traceability matrix |
| **static_analysis** | Formal audit report with CWE references, complexity metrics, and code quality score A-F |
| **comment_generator** | Structured review document with findings table and merge readiness checklist |
| **commit_analysis** | Release readiness report for change advisory board with scope table and changelog |

---

## How Templates Interact with Custom Prompts and Presets

### Append Mode Mechanics

When append mode is active (default):
```
Final Prompt = [Agent's built-in system prompt] + [Template text] + [User's custom prompt]
```

This layering allows:
- The agent's base instructions to establish core behaviour
- The template to provide an analysis framework
- The user's custom prompt to fine-tune or extend with specific details

### Overwrite Mode

Users can enable overwrite mode to completely replace the agent's guidance with their own custom prompt, bypassing templates entirely. This is useful for:
- Highly specialised analysis frameworks
- Domain-specific requirements
- Completely custom workflows

### Preset Integration

Presets (saved analysis configurations) typically include:
- A selected template category
- Optional custom prompt text
- Other agent parameters

When a preset is applied:
1. The template for that category is loaded
2. The preset's custom prompt (if any) is appended in append mode
3. The combined prompt guides the agent

---

## Quick Reference Table

| Category | Agent | Key Focus | Output Style | Ideal For |
|----------|-------|-----------|--------------|-----------|
| **Deep Analysis** | bug_analysis | Root-cause chains | Detailed findings | Complex bugs, architecture-related issues |
| **Deep Analysis** | code_design | SOLID principles | Thorough critique | Design review, refactoring planning |
| **Deep Analysis** | code_flow | State machines, data lineage | Function-level trace | Understanding complex flows |
| **Deep Analysis** | mermaid | Validated diagrams | Information-dense | Architecture visualisation |
| **Deep Analysis** | requirement | Formal contracts | Testable specs | Requirements documentation |
| **Deep Analysis** | static_analysis | Beyond tools | Semantic analysis | Uncovering subtle issues |
| **Deep Analysis** | comment_generator | Teaching moments | Mentoring style | Code review growth |
| **Deep Analysis** | commit_analysis | Narrative reconstruction | Risk assessment | Release readiness |
| **Security Focused** | bug_analysis | STRIDE/OWASP | Threat-centric | Security audits |
| **Security Focused** | code_design | Threat model | Architecture security | Secure design review |
| **Security Focused** | code_flow | Taint propagation | Attack path tracing | Authentication/auth flow |
| **Security Focused** | mermaid | Trust boundaries | Security diagrams | Architecture security viz |
| **Security Focused** | requirement | Auth/compliance | Security spec | Compliance requirements |
| **Security Focused** | static_analysis | CWE references | Vulnerability audit | Security code review |
| **Security Focused** | comment_generator | Exploitability | Security review | Security PR review |
| **Security Focused** | commit_analysis | Credential tracking | Risk trend | Release security check |
| **Architecture** | bug_analysis | Pattern violations | Architectural symptoms | Design-related bugs |
| **Architecture** | code_design | ADRs, patterns | Architecture reconstruction | Understanding legacy systems |
| **Architecture** | code_flow | Failure domains | System-level trace | Scalability analysis |
| **Architecture** | mermaid | C4 diagrams | Pattern-annotated | Architecture communication |
| **Architecture** | requirement | Quality attributes | Constraint archaeology | System rebuild specs |
| **Architecture** | static_analysis | Modularity, cohesion | Fitness report | Architecture health |
| **Architecture** | comment_generator | Design impact | Evolution assessment | Architectural PRs |
| **Architecture** | commit_analysis | Design trail | Evolution narrative | Architecture history |
| **Quick Scan** | bug_analysis | Top 3-5 only | Traffic-light summary | Fast feedback loop |
| **Quick Scan** | code_design | 500-word snapshot | Concise overview | Executive summary |
| **Quick Scan** | code_flow | 10-step happy path | Quick reference | Onboarding new developers |
| **Quick Scan** | mermaid | 10-node minimal | 10-second diagram | Quick comprehension |
| **Quick Scan** | requirement | Top 5-10 | Status bullets | Core requirements only |
| **Quick Scan** | static_analysis | Critical only | Brief severity list | Fast quality check |
| **Quick Scan** | comment_generator | 3-5 critical | GO/NO-GO | Time-boxed review |
| **Quick Scan** | commit_analysis | 300-word summary | Risk snapshot | Fast release check |
| **Report Generator** | bug_analysis | Full audit | Formal report | Compliance documentation |
| **Report Generator** | code_design | Quality scores | Architecture document | Stakeholder review |
| **Report Generator** | code_flow | Operations manual | Technical guide | Ops team handoff |
| **Report Generator** | mermaid | Presentation-grade | Formal diagrams | Stakeholder presentations |
| **Report Generator** | requirement | IEEE 830 SRS | Formal spec | Contractual documentation |
| **Report Generator** | static_analysis | CWE audit | Formal report | Compliance audit trail |
| **Report Generator** | comment_generator | Structured document | Formal review | Audit trail, archival |
| **Report Generator** | commit_analysis | Release readiness | Change advisory | Release sign-off |

---

## Selection Guide by Use Case

**"I need to find and fix bugs"**
- Start: Deep Analysis (bug_analysis)
- Refine: Security Focused if sensitive data; Architecture if suspicious patterns

**"I'm reviewing code design"**
- Start: Deep Analysis (code_design)
- Refine: Architecture for systemic issues; Security Focused for design flaws with security implications

**"I'm doing code review (PR)"**
- Start: Deep Analysis (comment_generator)
- Refine: Security Focused for security-critical PRs; Quick Scan for speed-sensitive reviews

**"I need compliance documentation"**
- Start: Report Generator (matches agent)
- Refine: Security Focused if compliance is security-related (HIPAA, PCI-DSS)

**"I'm short on time"**
- Use: Quick Scan (any agent)
- Follow up: Deep Analysis later for detailed remediation

**"I'm teaching someone the codebase"**
- Use: Deep Analysis (code_flow) + Quick Scan (mermaid)
- These provide narrative understanding and visual reference

**"I need to understand architecture"**
- Use: Architecture Reverse Engineering (code_design + mermaid)
- These reconstruct design from code and visualise it

---

## Customising Templates

Templates are provided as starting points. Common customisations:

1. **Add domain context:** Include custom prompt with template to inject domain-specific rules
2. **Restrict scope:** Use Quick Scan as a base, then customize to specific subsystems
3. **Hybrid analysis:** Combine Deep Analysis framework with Security Focused concern in custom prompt
4. **Reporting:** Use Report Generator as structure, add custom sections in custom prompt

All customisations work through append mode, allowing templates and custom prompts to work together seamlessly.
