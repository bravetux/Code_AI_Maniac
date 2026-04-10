"""Built-in enhanced prompt templates for all agents.

Each template appends expert analysis frameworks to an agent's default system
prompt, enabling deeper, more structured output without replacing the base
instructions.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents._bedrock import _APPEND_PREFIX

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptTemplate:
    category: str       # e.g. "Deep Analysis"
    agent: str          # e.g. "bug_analysis"
    label: str          # Human-readable category name
    description: str    # One-line tooltip for the UI
    prompt_text: str    # Appended after the agent's built-in system prompt


TEMPLATE_CATEGORIES: list[str] = [
    "Deep Analysis",
    "Security Focused",
    "Architecture Reverse Engineering",
    "Quick Scan",
    "Report Generator",
    "Language Expert",
    "Performance Deep Dive",
    "Compliance: SOC 2",
    "Compliance: GDPR",
    "Compliance: PCI-DSS",
    "Compliance: HIPAA",
    "Compliance: ISO 27001",
    "Compliance: Generic Audit",
]

# ---------------------------------------------------------------------------
# Category 1 — Deep Analysis
# Chain-of-thought, root-cause tracing, multi-pass analysis
# ---------------------------------------------------------------------------

_DEEP_BUG = """\
## Enhanced Analysis Protocol

Before reporting any finding, execute this analysis chain:

1. **First Pass — Surface Scan:** Read the entire code. Note your initial impressions. \
What stands out? What feels off but you cannot yet articulate?

2. **Second Pass — Assumption Audit:** For each function, list the implicit assumptions \
it makes about its inputs, state, and environment. Which assumptions are unvalidated? \
Which could be violated by callers?

3. **Third Pass — Failure Mode Analysis:** For each code path, ask: "What is the worst \
thing that can happen here?" Consider: null/undefined propagation, integer overflow, \
race conditions, resource exhaustion, encoding mismatches, timezone errors, \
floating-point precision loss.

4. **Fourth Pass — Interaction Analysis:** How do components interact? Where are the \
trust boundaries? Does data cross a boundary without validation? Does error handling \
in one layer mask failures in another?

5. **Synthesis:** For each bug found, trace the full causal chain: \
trigger condition -> propagation path -> observable failure -> business impact. \
Rate confidence (high/medium/low) in each finding.

Think step-by-step. Show your reasoning for each finding. If you are uncertain about \
a finding, say so explicitly rather than omitting it."""

_DEEP_DESIGN = """\
## Enhanced Design Analysis Protocol

Apply these analytical lenses in sequence:

1. **SOLID Principles Audit:**
   - Single Responsibility: Does each class/module have exactly one reason to change?
   - Open/Closed: Can behaviour be extended without modifying existing code?
   - Liskov Substitution: Are subtypes truly substitutable for their base types?
   - Interface Segregation: Are interfaces minimal and focused?
   - Dependency Inversion: Do high-level modules depend on abstractions, not concretions?

2. **Coupling & Cohesion Matrix:** For each module, identify what it depends on and \
what depends on it. Score cohesion (are responsibilities related?) and coupling \
(how many external dependencies?). Highlight the highest-risk couplings.

3. **Change Impact Analysis:** If you had to add a new feature, change a data format, \
or swap a dependency — where would changes ripple? Identify the modules with the \
highest "change amplification."

4. **Pattern Recognition:** Identify design patterns in use (both intentional and \
accidental). Are they applied correctly? Are there missing patterns that would \
simplify the design?

5. **Evolutionary Architecture Assessment:** Is this design positioned to evolve, or \
is it painted into a corner? What are the most likely future requirements, and how \
hard would they be to implement?

Be brutally honest. A design review that only praises is useless. Prioritise \
findings by impact on maintainability and extensibility."""

_DEEP_FLOW = """\
## Enhanced Flow Analysis Protocol

Trace execution with the precision of a debugger:

1. **Entry Point Mapping:** Identify every way this code can be invoked. For each \
entry point: who calls it, what triggers it, what preconditions must hold.

2. **State Machine Extraction:** Model the implicit state machine. What are the \
states? What transitions between them? What invariants must hold in each state? \
Where can the state machine get stuck?

3. **Data Lineage Tracing:** For each piece of data: where does it originate, how is \
it transformed at each step, where does it ultimately go? Track type changes, \
encoding changes, and validation points.

4. **Concurrency Analysis:** Identify shared mutable state. Map which threads or \
coroutines access which data. Where are the synchronisation points? What happens \
under concurrent access?

5. **Error Propagation Mapping:** Trace how errors flow. Where are errors caught? \
Where are they swallowed? Where do they propagate unchecked? Map error paths as \
carefully as happy paths.

6. **Performance Hot Path Identification:** Which execution path runs most frequently? \
Where are the O(n^2) loops, blocking I/O calls, or unnecessary allocations on the \
hot path?

Use actual function names, variable names, and line numbers. A reader should be \
able to follow your analysis with the code open side-by-side."""

_DEEP_MERMAID = """\
## Enhanced Diagram Generation Protocol

Create comprehensive, information-dense diagrams:

1. **Before drawing:** Analyse the code to identify all components, their \
relationships, and data flows. List them mentally before generating the diagram.

2. **Diagram principles:**
   - Every node must correspond to a real function, class, or component in the code
   - Every edge must represent a real call, data flow, or dependency
   - Label edges with what is passed (data type, method name)
   - Use subgraphs to group related components
   - Include error paths and alternative flows, not just the happy path
   - Use consistent style coding for happy paths vs error paths vs optional paths

3. **Validation:** After generating, verify every node and edge against the actual \
code. Remove anything speculative.

Generate a diagram that a new team member could use to understand the system in \
60 seconds."""

_DEEP_REQUIREMENT = """\
## Enhanced Requirements Extraction Protocol

Reverse-engineer requirements with the rigour of a formal specification:

1. **Behavioural Decomposition:** For each function/method, extract the behavioural \
contract:
   - Preconditions: What must be true before invocation?
   - Postconditions: What is guaranteed after successful execution?
   - Invariants: What must remain true throughout execution?
   - Side effects: What external state changes?

2. **Business Rule Extraction:** Identify embedded business rules — validation logic, \
threshold values, state transitions, access control checks. For each rule, determine: \
is this a domain rule or an implementation choice?

3. **Implicit Requirements:** What does the code assume about its environment? \
(OS, network, file system, timezone, locale, available memory, concurrent access \
patterns.) These are requirements the code enforces but does not document.

4. **Negative Requirements:** What does the code explicitly prevent? (Input \
validation, access control, rate limiting.) Document what the system shall NOT allow.

5. **Traceability Matrix:** For each REQ, cite the exact lines that implement it. \
A requirement without traceable code may indicate dead specification or missing \
implementation.

Write requirements that are testable. Each REQ should have a clear pass/fail \
criterion."""

_DEEP_STATIC = """\
## Enhanced Static Analysis Protocol

Go beyond what automated tools can find:

1. **Semantic Type Analysis:** Even in dynamically typed code, data has semantic \
types (a "userId" is not just a string). Identify where semantic types are confused, \
where unsafe coercions occur, where a value is used in a context that does not match \
its semantic meaning.

2. **Temporal Coupling Analysis:** Identify code that must be called in a specific \
order but does not enforce that order. Where are the implicit sequencing \
requirements? What happens when callers violate the expected sequence?

3. **Resource Lifecycle Audit:** For every resource (file handle, connection, lock, \
memory allocation, temporary file): where is it acquired, where is it released, and \
what happens on the error path between acquisition and release?

4. **Attack Surface Mapping:** Identify every point where untrusted data enters the \
system. Trace it to where it is used. Check for: injection (SQL, command, XSS, LDAP), \
path traversal, deserialisation, SSRF, and improper access control at each usage point.

5. **Complexity Hotspot Identification:** Calculate cognitive complexity for each \
function. Identify the deepest nesting, the longest functions, the most complex \
conditionals. These are where bugs hide.

For each finding, explain the specific failure scenario — not just "this could be a \
problem" but "if an attacker sends X, then Y happens, resulting in Z."
"""

_DEEP_COMMENT = """\
## Enhanced PR Review Protocol

Write reviews that engineers actually learn from:

1. **Categorise Before Commenting:** Group findings into: must-fix-before-merge, \
should-fix-soon, and nice-to-have. Lead the review summary with this prioritisation \
so the author knows what to focus on.

2. **Teach, Don't Just Flag:** For each comment, explain the underlying principle. \
Instead of "add input validation here," explain what attack vector this prevents and \
show the specific validation code.

3. **Suggest, Don't Dictate:** Provide concrete fix suggestions but acknowledge \
alternative approaches. Use language like "Consider..." or "One approach would be..." \
for non-critical issues.

4. **Praise Deliberately:** Call out genuinely good patterns — not generic "nice code" \
but specific observations like "Good use of the strategy pattern here — it will make \
adding new providers straightforward."

5. **Review Holistically:** After individual comments, step back and assess: Does this \
change achieve its stated goal? Are there architectural concerns beyond line-level \
issues? Is the test coverage adequate for the risk level?

Write comments in the tone of a senior engineer mentoring a colleague — direct, \
constructive, and focused on growth."""

_DEEP_COMMIT = """\
## Enhanced Commit Analysis Protocol

Analyse commit history like a forensic software archaeologist:

1. **Commit Narrative Reconstruction:** Read the commits in chronological order and \
reconstruct the story. What was the developer trying to build? Where did they change \
direction? What problems did they encounter (evidenced by fix commits)?

2. **Commit Hygiene Assessment:** For each commit evaluate:
   - Atomicity: Does it contain exactly one logical change?
   - Message quality: Does the message explain WHY, not just WHAT?
   - Completeness: Are tests included with the feature/fix?
   - Reversibility: Could this commit be cleanly reverted?

3. **Risk Pattern Detection:**
   - Rapid-fire small commits -> possible debugging by trial-and-error
   - Large commits with vague messages -> possible rushed or untested changes
   - "fix" commits following feature commits -> possible inadequate testing
   - Late-night timestamps -> possible fatigue-related risk
   - Many files changed -> high blast radius

4. **Release Readiness Verdict:** Give a clear GO / CONDITIONAL GO / NO-GO \
recommendation with specific conditions that must be met.

5. **Team Process Recommendations:** What workflow improvements would prevent the \
issues you identified? Be specific and actionable.

Write as if presenting to the team at a release readiness meeting. Be honest, be \
specific, use examples from the actual commits."""

# ---------------------------------------------------------------------------
# Category 2 — Security Focused
# STRIDE, OWASP Top 10, threat modelling
# ---------------------------------------------------------------------------

_SEC_BUG = """\
## Security-First Analysis Mode

Analyse this code through a security lens using the STRIDE threat model:

- **Spoofing:** Can any identity be faked? Authentication bypasses, token forgery, \
session fixation?
- **Tampering:** Can data be modified in transit or at rest? Input manipulation, \
parameter pollution, mass assignment?
- **Repudiation:** Can actions be denied? Missing audit logs, unsigned transactions?
- **Information Disclosure:** Can secrets leak? Error messages exposing internals, \
timing attacks, verbose logging of sensitive data?
- **Denial of Service:** Can the system be overwhelmed? Unbounded loops, regex DoS \
(ReDoS), resource exhaustion, algorithmic complexity attacks?
- **Elevation of Privilege:** Can permissions be escalated? Insecure direct object \
references, missing authorisation checks, privilege confusion?

Cross-reference against OWASP Top 10 2021: A01:Broken Access Control, \
A02:Cryptographic Failures, A03:Injection, A04:Insecure Design, \
A05:Security Misconfiguration, A06:Vulnerable Components, A07:Auth Failures, \
A08:Data Integrity Failures, A09:Logging Failures, A10:SSRF.

Rate each finding with attack complexity (low/high), required privileges \
(none/low/high), and potential impact (confidentiality/integrity/availability)."""

_SEC_DESIGN = """\
## Security Architecture Review Mode

Evaluate the design through a security architecture lens:

1. **Trust Boundary Analysis:** Identify trust boundaries. Where does trusted code \
interact with untrusted input? Is there a clear security perimeter? Are trust \
boundaries enforced consistently?

2. **Defence in Depth Assessment:** How many layers of defence exist? If one layer \
fails, what catches the threat? Identify single points of security failure.

3. **Principle of Least Privilege:** Does each component have only the permissions it \
needs? Are credentials scoped minimally? Can blast radius be reduced?

4. **Secure by Default:** Are defaults secure? Does the system fail open or fail \
closed? Are security features opt-out rather than opt-in?

5. **Cryptographic Assessment:** Are secrets hardcoded? Is encryption used correctly? \
Are there custom crypto implementations? Are keys rotated? Is the RNG \
cryptographically secure?

6. **Data Classification:** Identify PII, credentials, tokens, and other sensitive \
data. How is each classified type stored, transmitted, and logged? Is any sensitive \
data in URLs, logs, or error messages?

Produce a threat model summary with identified threats, existing mitigations, and \
recommended additional controls."""

_SEC_FLOW = """\
## Security-Focused Flow Analysis

Trace execution with a focus on trust boundaries and data tainting:

1. **Taint Propagation:** Identify all untrusted input sources (user input, network, \
files, environment variables). Trace how tainted data propagates through the code. \
Where is it sanitised? Where does it reach a sink (database query, command execution, \
HTML output, file path) without sanitisation?

2. **Authentication Flow:** Map the complete authentication lifecycle: credential \
submission, verification, session creation, session validation, session termination. \
Identify bypass opportunities at each step.

3. **Authorisation Flow:** For each protected resource, trace the authorisation check. \
Is it applied consistently? Can it be bypassed through alternative code paths?

4. **Secret Flow:** Track how secrets (API keys, passwords, tokens) move through the \
system. Where are they stored, transmitted, logged, or cached? Are they ever exposed \
in error messages or debug output?

5. **Error Path Security:** What happens when things fail? Do error paths leak \
information? Do they leave the system in a less-secure state? Are error paths tested?

Flag every location where untrusted data reaches a security-sensitive operation."""

_SEC_MERMAID = """\
## Security-Focused Diagram Protocol

Generate diagrams that highlight security boundaries and attack surfaces:

1. **Trust boundaries:** Draw clear boundaries between trusted and untrusted zones. \
Mark every point where data crosses a trust boundary.

2. **Data flow with sensitivity labels:** Label each data flow with its sensitivity \
level (public, internal, confidential, secret). Highlight where sensitive data flows \
into less-trusted zones.

3. **Attack surface indicators:** Mark entry points that accept external input. \
Annotate with the validation/sanitisation applied at each point.

4. **Authentication and authorisation gates:** Show where auth checks occur in the \
flow. Highlight any paths that bypass these gates.

Use red styling for untrusted paths, green for authenticated/authorised paths, and \
dashed lines for optional or conditional security controls."""

_SEC_REQUIREMENT = """\
## Security Requirements Extraction Mode

Extract security-specific requirements from the code:

1. **Authentication Requirements:** What authentication mechanisms does the code \
implement or expect? Multi-factor? Token-based? Session management details?

2. **Authorisation Requirements:** What access control model is enforced? RBAC? ABAC? \
What roles and permissions exist? Are they consistently enforced?

3. **Data Protection Requirements:** How is data protected at rest and in transit? \
What encryption is used? What data retention policies are implied?

4. **Input Validation Requirements:** What validation rules are enforced? On which \
inputs? What characters, lengths, and formats are accepted or rejected?

5. **Audit and Logging Requirements:** What events are logged? What is the log format? \
Are security-relevant events (login, access, modification) captured?

6. **Compliance Implications:** Does the code imply compliance with specific standards \
(PCI-DSS, HIPAA, GDPR, SOC2)? What compliance gaps exist?

For each security requirement, rate its current implementation as: \
fully implemented / partially implemented / missing."""

_SEC_STATIC = """\
## Security-Focused Static Analysis

Perform a security audit targeting the most dangerous vulnerability classes:

1. **Injection Analysis (CWE-79, CWE-89, CWE-78):** For every database query, \
command execution, and HTML output — is the input parameterised or sanitised? Trace \
every path from input to query/command/output.

2. **Authentication & Session (CWE-287, CWE-384):** Are passwords hashed with strong \
algorithms (bcrypt, argon2)? Are sessions cryptographically random? Is there session \
fixation protection? Are tokens invalidated on logout?

3. **Access Control (CWE-862, CWE-863):** For every endpoint and data access — is \
authorisation checked? Can horizontal escalation occur (user A accessing user B's \
data)? Can vertical escalation occur (regular user accessing admin functions)?

4. **Cryptographic Issues (CWE-327, CWE-328):** Are deprecated algorithms used \
(MD5, SHA1 for security, DES, RC4)? Are IVs/nonces reused? Are keys derived from \
weak sources?

5. **Sensitive Data Exposure (CWE-200, CWE-532):** Is sensitive data logged? Returned \
in error responses? Stored in plaintext? Transmitted without encryption?

For each finding, provide the CWE identifier, the exact vulnerable code path, and a \
specific remediation with code example."""

_SEC_COMMENT = """\
## Security-Focused PR Review Mode

Review this code change with a security-first mindset:

1. **New Attack Surface:** Does this change introduce new input handlers, API \
endpoints, file parsers, or external integrations? Each is a potential attack vector \
— flag them for security review.

2. **Regression Risk:** Does this change modify authentication, authorisation, input \
validation, or cryptographic code? Changes to security-critical code require extra \
scrutiny.

3. **Dependency Risk:** Are new dependencies introduced? Check for known \
vulnerabilities. Are existing dependencies updated in a way that changes their \
security posture?

4. **Sensitive Data Handling:** Does this change touch code that handles passwords, \
tokens, PII, or financial data? Verify handling follows secure coding standards.

5. **Security Testing Gap:** Does the change include security-relevant test cases? \
Missing security tests for security-critical code is a must-fix finding.

For each security comment, rate: severity (critical/high/medium/low) and \
exploitability (trivial/moderate/difficult)."""

_SEC_COMMIT = """\
## Security-Focused Commit History Review

Analyse the commit history for security-relevant patterns:

1. **Security Fix Audit:** Identify commits that fix security issues. Were they \
handled properly? Was a CVE assigned if needed? Was the fix complete or partial?

2. **Credential Hygiene:** Were any secrets, API keys, or credentials committed \
(even if later removed)? Git history is permanent — removal does not equal security.

3. **Dependency Changes:** Were dependencies added or updated? Check for known \
vulnerabilities in added versions. Were security-critical dependencies pinned to \
specific versions?

4. **Security-Critical Code Changes:** Identify commits that modify authentication, \
authorisation, encryption, input validation, or session management. Were these changes \
reviewed? Do they include security tests?

5. **Security Posture Trend:** Is the security posture improving or degrading over \
the commit history? Are security issues being fixed faster than they are introduced?

Produce a security risk assessment with a clear recommendation for security review \
priorities before release."""

# ---------------------------------------------------------------------------
# Category 3 — Architecture Reverse Engineering
# Pattern recognition, dependency analysis, design archaeology
# ---------------------------------------------------------------------------

_ARCH_BUG = """\
## Architecture-Aware Bug Analysis

Analyse bugs as symptoms of architectural decisions:

1. **Pattern Violation Detection:** Identify design patterns in use. Are any violations \
of these patterns causing bugs? (e.g., a Singleton with mutable state causing race \
conditions, an Observer with missing unsubscription causing memory leaks.)

2. **Layer Violation Bugs:** Does the code respect its architectural layers? Are there \
bugs caused by bypassing abstraction layers (direct database access from a controller, \
UI logic in a model)?

3. **Interface Contract Bugs:** Do callers respect the contracts of the functions they \
call? Are there bugs caused by misunderstood interfaces, unexpected null returns, or \
undocumented side effects?

4. **Architectural Debt Bugs:** Identify bugs that exist because of accumulated \
architectural debt — workarounds, shortcuts, and hacks that have calcified into the \
codebase.

For each bug, explain which architectural decision made it possible and what \
structural change would prevent this class of bug entirely."""

_ARCH_DESIGN = """\
## Architecture Reverse Engineering Protocol

Reconstruct the architecture from the code like a software archaeologist:

1. **Layer Identification:** What are the architectural layers? (Presentation, \
business logic, data access, infrastructure.) Are the layers clearly separated? Where \
do they bleed into each other?

2. **Component Catalogue:** Identify every distinct component. For each: what is its \
single responsibility, what are its dependencies, what is its public interface, and \
what design pattern does it implement?

3. **Dependency Graph:** Map all dependencies (imports, function calls, data flows). \
Identify: circular dependencies, high-fanout components (depended on by many), and \
high-fanin components (depending on many).

4. **Design Decision Archaeology:** For each significant design choice, infer the \
reasoning: Why was this pattern chosen? What constraints was the author working under? \
What trade-offs were made? What alternatives existed?

5. **Architectural Style Classification:** What architectural style is this? \
(Layered, hexagonal, microkernel, pipes-and-filters, event-driven, MVC.) Is it \
applied consistently? Where does it deviate?

6. **Evolution Trajectory:** Based on the current architecture, what is easy to \
change and what is hard? What are the most likely future requirements, and where will \
the architecture need to bend?

Produce an architecture decision record (ADR) format for each significant design \
decision discovered."""

_ARCH_FLOW = """\
## Architecture-Level Flow Analysis

Trace flows at the system architecture level, not just code level:

1. **Request Lifecycle:** Trace a complete request from external trigger to response. \
Map every layer it passes through, every transformation it undergoes, every external \
system it touches.

2. **Cross-Cutting Concerns:** How do cross-cutting concerns (logging, auth, caching, \
error handling, transactions) weave through the flow? Are they implemented \
consistently via middleware/decorators, or are they scattered ad-hoc?

3. **Component Interaction Map:** How do components communicate? Synchronous calls? \
Events? Shared state? Message queues? Map the communication topology.

4. **Failure Domain Analysis:** What are the failure domains? If component A fails, \
what else breaks? Map the blast radius of each component's failure.

5. **Scalability Bottleneck Identification:** Which components are stateful? Which \
hold locks? Which do blocking I/O? These are the bottlenecks under load.

Produce a flow analysis that would help a new architect understand the system's \
runtime behaviour in 10 minutes."""

_ARCH_MERMAID = """\
## Architecture Diagram Protocol

Generate architecture-level diagrams that reveal system structure:

1. **C4 Model Approach:** Structure the diagram following C4 principles:
   - System context: how does this code interact with external actors/systems?
   - Container level: what are the major deployable units?
   - Component level: what are the key components within each container?

2. **Dependency Direction:** Show dependency arrows pointing from dependent to \
dependency. Highlight any arrows pointing in the wrong direction (layer violations).

3. **Boundary Markers:** Use subgraphs to mark architectural boundaries: layers, \
modules, bounded contexts, trust zones.

4. **Pattern Annotation:** Annotate components with the design pattern they implement \
(Repository, Factory, Observer, Strategy, etc.).

Create a diagram that reveals the architecture at a glance — the "big picture" view \
that is usually missing from code."""

_ARCH_REQUIREMENT = """\
## Architecture-Focused Requirements Extraction

Extract requirements that reveal the architectural constraints:

1. **Quality Attribute Requirements:** Extract implied quality attributes: \
performance targets (throughput, latency), reliability (uptime, fault tolerance), \
scalability (concurrent users, data volume), security (access control model, \
encryption requirements).

2. **Integration Requirements:** What external systems does this code integrate with? \
What are the interface contracts? What happens when integrations fail?

3. **Deployment Requirements:** What does the code assume about its deployment \
environment? Container? Serverless? Specific OS? Network topology?

4. **Configuration Requirements:** What is configurable? What is hardcoded that should \
be configurable? What are the configuration dependencies between components?

5. **Constraint Archaeology:** What technical constraints shaped the architecture? \
(Legacy system compatibility, team expertise, compliance requirements, performance \
budgets.) Document these as architectural decision records.

Write requirements that would allow a team to rebuild this system from scratch with \
the same architectural qualities."""

_ARCH_STATIC = """\
## Architecture-Level Static Analysis

Analyse code quality through an architectural lens:

1. **Modularity Assessment:** Are module boundaries clean? Can each module be \
understood, tested, and deployed independently? Measure by counting cross-boundary \
dependencies.

2. **Abstraction Quality:** Are abstractions at the right level? Too low (leaky) or \
too high (unusable)? Do abstractions hide complexity or just rename it?

3. **Dependency Health:** Map the dependency graph. Are there circular dependencies? \
Is the dependency direction correct (stable dependencies principle)? Are there \
components with too many dependents (fragile base class problem)?

4. **Code Organisation Coherence:** Do files and directories reflect the architecture? \
Is related code collocated? Would a new developer find files where they expect them?

5. **Technical Debt Hotspots:** Identify areas where the code has diverged from its \
intended architecture. Quantify the cost: how much harder is each change because of \
this debt?

Produce an architectural fitness report with specific metrics and actionable \
improvement recommendations."""

_ARCH_COMMENT = """\
## Architecture-Aware PR Review

Review this change for its architectural impact:

1. **Architectural Conformance:** Does this change respect the existing architecture? \
Does it introduce new patterns inconsistent with established ones?

2. **Dependency Impact:** Does this change add new dependencies? Do they point in the \
right direction (toward stable abstractions)? Could they introduce coupling that makes \
future changes harder?

3. **Abstraction Quality:** Do new abstractions introduced by this change have clear \
contracts? Are they at the right level? Will they be reusable or are they \
single-purpose wrappers?

4. **Technical Debt Assessment:** Does this change increase or decrease technical \
debt? Is any new debt intentional and documented, or accidental?

5. **Evolution Enablement:** Does this change make the system easier or harder to \
evolve? Are future changes in this area easier or harder after this PR?

Focus comments on design-level concerns rather than style or formatting."""

_ARCH_COMMIT = """\
## Architecture Evolution Analysis

Analyse how the architecture has evolved across these commits:

1. **Architectural Change Classification:** For each commit, classify: is this a \
feature addition, a refactoring, a bug fix, a dependency update, or an architectural \
change? What proportion of work is feature vs. maintenance?

2. **Component Evolution:** Which components are changing most frequently? High churn \
suggests either active development or instability. Correlate with bug-fix commits to \
distinguish.

3. **Dependency Evolution:** How have dependencies changed? Are new dependencies well- \
justified? Are deprecated dependencies being removed?

4. **Pattern Consistency:** Are new commits following established patterns or \
introducing new ones? Divergence suggests either evolution or inconsistency.

5. **Architecture Decision Trail:** Can you reconstruct the architectural decisions \
from the commit history? What design choices were made, reversed, or evolved?

Summarise the architectural trajectory: is the system getting simpler or more complex? \
More modular or more tangled? More consistent or more fragmented?"""

# ---------------------------------------------------------------------------
# Category 4 — Quick Scan
# Fast, high-level overview, top findings only
# ---------------------------------------------------------------------------

_QUICK_BUG = """\
## Quick Scan Mode

Perform a rapid triage — report ONLY the top 3-5 most critical findings:

- Skip minor style issues, naming suggestions, and low-impact improvements
- Focus exclusively on: crashes, data corruption, security vulnerabilities, and \
logic errors that would cause incorrect behaviour in production
- For each finding: one sentence description, the affected line(s), and the \
recommended fix
- Rate overall code health: RED (critical issues) / AMBER (notable concerns) / \
GREEN (production-ready)

Keep your response concise — aim for under 500 words total. Brevity is the priority."""

_QUICK_DESIGN = """\
## Quick Scan Mode

Provide a rapid architectural assessment in under 500 words:

- One paragraph: what this code does and how it is structured
- Top 3 design strengths
- Top 3 design concerns (ranked by impact)
- Overall verdict: RED / AMBER / GREEN for production readiness
- One sentence: the single most impactful improvement

Skip detailed analysis. Prioritise actionable insight over completeness."""

_QUICK_FLOW = """\
## Quick Scan Mode

Provide a concise execution flow summary in under 400 words:

- Main entry point and what triggers it
- Happy-path flow in 5-10 numbered steps (one sentence each)
- Key decision points (where does the code branch?)
- External dependencies touched
- One paragraph: what a new developer needs to know most

Skip edge cases, error handling details, and performance analysis."""

_QUICK_MERMAID = """\
## Quick Scan Mode

Generate a minimal, clean diagram:

- Maximum 10-15 nodes
- Show only the main flow (skip error handling and edge cases)
- Use clear, short labels
- No subgraphs unless absolutely necessary
- Prioritise readability over completeness

The diagram should be understood in 10 seconds."""

_QUICK_REQUIREMENT = """\
## Quick Scan Mode

Extract only the top 5-10 most important requirements:

- Focus on core functional requirements that define what the system does
- Skip minor implementation details and configuration points
- One sentence per requirement
- Rate implementation completeness: fully/partially/not implemented
- List the single biggest gap between what the code does and what it should do

Keep the output under 400 words."""

_QUICK_STATIC = """\
## Quick Scan Mode

Report only critical and major findings:

- Maximum 5 findings
- Skip minor code style issues and documentation gaps
- For each finding: severity (critical/major), one sentence description, the line(s)
- Overall code quality: RED / AMBER / GREEN
- The single most important thing to fix

Keep your response under 400 words."""

_QUICK_COMMENT = """\
## Quick Scan Mode

Generate a concise PR review:

- Maximum 3-5 comments, critical issues only
- One-paragraph summary comment with GO / NO-GO recommendation
- Skip style nits, naming suggestions, and minor improvements
- Each comment: file, line, one sentence, suggested fix

Aim for a review that takes 2 minutes to read and act on."""

_QUICK_COMMIT = """\
## Quick Scan Mode

Provide a rapid commit history assessment:

- One paragraph: what was built/changed across these commits
- Top 3 risk signals (if any)
- Release readiness: GO / CONDITIONAL GO / NO-GO
- One sentence: the single biggest concern (or "no major concerns")

Keep the output under 300 words."""

# ---------------------------------------------------------------------------
# Category 5 — Report Generator
# Formal, publication-quality output
# ---------------------------------------------------------------------------

_REPORT_BUG = """\
## Professional Report Generation Mode

Produce a formal, publication-quality bug analysis report:

### Document Structure
1. **Executive Summary** — 2-3 sentences for non-technical stakeholders: how many \
issues found, overall risk level, recommended action.

2. **Findings Summary Table** — Tabular overview:
   | # | Severity | Category | Line(s) | Description | Status |
   Present ALL findings in this table before detailed analysis.

3. **Detailed Findings** — For each finding:
   - **Finding ID:** BUG-001, BUG-002, etc.
   - **Severity:** Critical / Major / Minor (with justification)
   - **Category:** Logic Error / Security / Performance / Data Integrity
   - **Affected Code:** File, line range, function name
   - **Description:** Clear, precise description of the issue
   - **Root Cause:** Why this issue exists
   - **Impact Assessment:** What happens if not fixed (probability x severity)
   - **Remediation:** Specific fix with code example
   - **Effort Estimate:** Small (< 1 hr) / Medium (1-4 hrs) / Large (4+ hrs)

4. **Risk Matrix** — Plot findings on a likelihood vs impact matrix.

5. **Recommendations** — Prioritised action items with owners and timelines.

Write in formal, professional English suitable for inclusion in a compliance audit \
or quality review document."""

_REPORT_DESIGN = """\
## Professional Report Generation Mode

Produce a formal architecture and design review document:

### Document Structure
1. **Executive Summary** — What this component does, its role in the system, and the \
overall assessment of its design quality. Write for stakeholders.

2. **System Overview** — Architecture diagram description, technology stack, key \
design decisions and their rationale.

3. **Component Analysis** — For each component:
   | Component | Responsibility | Dependencies | Quality Score |

4. **Design Quality Assessment:**
   - Modularity: Score 1-5 with justification
   - Testability: Score 1-5 with justification
   - Extensibility: Score 1-5 with justification
   - Maintainability: Score 1-5 with justification
   - Security Posture: Score 1-5 with justification

5. **Technical Debt Register:**
   | ID | Description | Impact | Effort to Fix | Priority |

6. **Improvement Roadmap** — Phased plan: Quick Wins (week 1), Short-term (month 1), \
Medium-term (quarter 1), Long-term (year 1).

7. **Appendices** — Dependency list, API inventory, configuration parameters.

Write in the style of a professional technical architecture document suitable for \
leadership review."""

_REPORT_FLOW = """\
## Professional Report Generation Mode

Produce a formal code flow documentation report:

### Document Structure
1. **Overview** — What this code does, who uses it, and why this documentation exists.

2. **System Context** — Where this code fits in the larger system. External actors, \
upstream and downstream systems.

3. **Flow Diagrams** — Describe the flows that should be diagrammed (use numbered \
steps with clear references to functions and line numbers).

4. **Detailed Flow Descriptions** — For each major flow:
   - **Trigger:** What initiates this flow
   - **Preconditions:** What must be true
   - **Steps:** Numbered walkthrough with function:line references
   - **Data Transformations:** How data changes shape at each step
   - **Error Handling:** How failures are managed at each step
   - **Postconditions:** What is true after successful completion

5. **Performance Characteristics** — Expected execution time, resource usage, \
bottlenecks.

6. **Operational Considerations** — Monitoring points, failure modes, recovery \
procedures.

Write as a technical operations document suitable for on-call engineers."""

_REPORT_MERMAID = """\
## Professional Diagram Generation Mode

Generate comprehensive, presentation-quality diagrams:

1. **Multiple diagram types if appropriate:** Generate the most informative diagram \
type for the code. Consider: flowchart for processes, sequence for interactions, \
class for OOP structures.

2. **Professional styling:**
   - Use clear, business-appropriate node labels (not abbreviated code names)
   - Add a title comment at the top of the diagram
   - Group related components logically
   - Use consistent directional flow (top-to-bottom or left-to-right)

3. **Completeness:** Include all significant paths, decision points, and error \
handling. Annotate with data types and conditions on edges.

Generate a diagram suitable for inclusion in a technical design document or \
architecture review presentation."""

_REPORT_REQUIREMENT = """\
## Professional Report Generation Mode

Produce a formal software requirements specification (SRS):

### Document Structure (IEEE 830 inspired)
1. **Introduction**
   - Purpose: What this document covers
   - Scope: System boundaries
   - Definitions and Acronyms

2. **Overall Description**
   - Product perspective: Where this fits in the larger system
   - Product functions: High-level capability summary
   - User characteristics: Who uses this and their technical level
   - Constraints: Technical, regulatory, business constraints
   - Assumptions and dependencies

3. **Specific Requirements**
   - Functional requirements: REQ-F-001 through REQ-F-NNN
   - Non-functional requirements: REQ-NF-001 through REQ-NF-NNN
   - Interface requirements: REQ-I-001 through REQ-I-NNN
   Each requirement: ID, description, priority (must/should/could), source (line refs), \
   verification method (test/inspection/analysis)

4. **Traceability Matrix:**
   | Requirement | Source Lines | Test Case | Status |

5. **Appendices** — Glossary, related documents, change history.

Write in formal requirements language ("The system shall...") suitable for \
contractual or compliance use."""

_REPORT_STATIC = """\
## Professional Report Generation Mode

Produce a formal static analysis report:

### Document Structure
1. **Executive Summary** — Total findings by severity, overall code quality score \
(A/B/C/D/F), key recommendations.

2. **Methodology** — What was analysed, tools used (linter + AI semantic analysis), \
scope and limitations.

3. **Findings Summary:**
   | ID | Severity | Category | File:Line | Description |

4. **Detailed Findings** — For each finding:
   - **Finding ID:** SA-001, SA-002, etc.
   - **Category:** Security / Performance / Logic / Maintainability / Concurrency / \
Error Handling
   - **Severity:** Critical / Major / Minor
   - **CWE Reference:** (if applicable)
   - **Description:** Technical explanation
   - **Evidence:** The specific code that exhibits the issue
   - **Risk:** What could go wrong in production
   - **Remediation:** Specific fix with code example
   - **Effort:** Small / Medium / Large

5. **Code Quality Metrics:**
   - Complexity score per function
   - Dependency count
   - Test coverage assessment (inferred)

6. **Recommendations** — Prioritised action plan.

Write in formal audit report style suitable for compliance review."""

_REPORT_COMMENT = """\
## Professional Report Generation Mode

Generate a formal, structured PR review document:

### Review Structure
1. **Review Summary:**
   - PR objective assessment: Does this change achieve its goal?
   - Overall recommendation: Approve / Request Changes / Reject
   - Critical issues count / Major issues count / Minor issues count

2. **Findings Table:**
   | # | Severity | File:Line | Category | Description |

3. **Detailed Comments** — For each finding:
   - **Category:** Bug / Security / Performance / Design / Style
   - **Severity:** Critical / Major / Minor / Suggestion
   - **Location:** File:line
   - **Description:** Clear explanation with context
   - **Recommendation:** Specific fix with code

4. **Positive Observations** — What was done well. Be specific.

5. **Testing Assessment** — Is the change adequately tested? What additional tests \
are recommended?

6. **Merge Readiness Checklist:**
   - [ ] All critical issues resolved
   - [ ] Security review complete
   - [ ] Test coverage adequate
   - [ ] Documentation updated
   - [ ] No regressions introduced

Write in professional code review format suitable for audit trail."""

_REPORT_COMMIT = """\
## Professional Report Generation Mode

Produce a formal release readiness report from commit history:

### Document Structure
1. **Executive Summary** — Release scope, risk level, GO/NO-GO recommendation. \
Write for non-technical leadership.

2. **Release Scope:**
   | Category | Count | Description |
   Features, bug fixes, refactoring, dependency updates, documentation.

3. **Changelog** — Professional changelog in Keep a Changelog format:
   ### Added / Changed / Fixed / Removed / Security

4. **Risk Assessment:**
   | Risk | Likelihood | Impact | Mitigation |

5. **Commit Quality Metrics:**
   - Atomic commits: X%
   - Descriptive messages: X%
   - Test-accompanied changes: X%
   - Average commit size (files changed)

6. **Release Readiness:**
   - [ ] All features complete
   - [ ] Critical bugs resolved
   - [ ] Security review complete
   - [ ] Rollback plan documented
   - **Verdict:** GO / CONDITIONAL GO / NO-GO

7. **Recommendations** — Pre-release actions, post-release monitoring, process \
improvements.

Write as a formal release management document suitable for change advisory board \
review."""

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

def _t(category: str, agent: str, description: str, text: str) -> PromptTemplate:
    return PromptTemplate(
        category=category, agent=agent, label=category,
        description=description, prompt_text=text,
    )


TEMPLATES: list[PromptTemplate] = [
    # ── Deep Analysis ────────────────────────────────────────────────────────
    _t("Deep Analysis", "bug_analysis",
       "Multi-pass chain-of-thought bug analysis with root-cause tracing",
       _DEEP_BUG),
    _t("Deep Analysis", "code_design",
       "SOLID audit, coupling matrix, and evolutionary architecture assessment",
       _DEEP_DESIGN),
    _t("Deep Analysis", "code_flow",
       "Debugger-precision flow tracing with state machines and data lineage",
       _DEEP_FLOW),
    _t("Deep Analysis", "mermaid",
       "Information-dense diagrams with validated nodes and error paths",
       _DEEP_MERMAID),
    _t("Deep Analysis", "requirement",
       "Formal specification with behavioural contracts and traceability",
       _DEEP_REQUIREMENT),
    _t("Deep Analysis", "static_analysis",
       "Semantic type analysis, temporal coupling, and resource lifecycle audit",
       _DEEP_STATIC),
    _t("Deep Analysis", "comment_generator",
       "Mentoring-style PR reviews that teach underlying principles",
       _DEEP_COMMENT),
    _t("Deep Analysis", "commit_analysis",
       "Forensic commit archaeology with narrative reconstruction",
       _DEEP_COMMIT),

    # ── Security Focused ─────────────────────────────────────────────────────
    _t("Security Focused", "bug_analysis",
       "STRIDE threat model + OWASP Top 10 security audit",
       _SEC_BUG),
    _t("Security Focused", "code_design",
       "Trust boundaries, defence in depth, and threat modelling",
       _SEC_DESIGN),
    _t("Security Focused", "code_flow",
       "Taint propagation, auth flow analysis, and secret tracking",
       _SEC_FLOW),
    _t("Security Focused", "mermaid",
       "Trust boundary diagrams with attack surface indicators",
       _SEC_MERMAID),
    _t("Security Focused", "requirement",
       "Security requirements extraction with compliance gap analysis",
       _SEC_REQUIREMENT),
    _t("Security Focused", "static_analysis",
       "Injection, auth, crypto, and CWE-referenced vulnerability audit",
       _SEC_STATIC),
    _t("Security Focused", "comment_generator",
       "Security-first PR review with exploitability ratings",
       _SEC_COMMENT),
    _t("Security Focused", "commit_analysis",
       "Credential hygiene, dependency risk, and security posture trending",
       _SEC_COMMIT),

    # ── Architecture Reverse Engineering ──────────────────────────────────────
    _t("Architecture Reverse Engineering", "bug_analysis",
       "Bugs as symptoms of architectural decisions",
       _ARCH_BUG),
    _t("Architecture Reverse Engineering", "code_design",
       "Full architecture reconstruction with ADRs and pattern catalogue",
       _ARCH_DESIGN),
    _t("Architecture Reverse Engineering", "code_flow",
       "System-level flow with failure domains and scalability analysis",
       _ARCH_FLOW),
    _t("Architecture Reverse Engineering", "mermaid",
       "C4-style architecture diagrams with pattern annotations",
       _ARCH_MERMAID),
    _t("Architecture Reverse Engineering", "requirement",
       "Quality attributes, integration contracts, and constraint archaeology",
       _ARCH_REQUIREMENT),
    _t("Architecture Reverse Engineering", "static_analysis",
       "Modularity, abstraction quality, and dependency health scoring",
       _ARCH_STATIC),
    _t("Architecture Reverse Engineering", "comment_generator",
       "Architecture-impact PR review with evolution assessment",
       _ARCH_COMMENT),
    _t("Architecture Reverse Engineering", "commit_analysis",
       "Architecture evolution tracking and design decision trail",
       _ARCH_COMMIT),

    # ── Quick Scan ────────────────────────────────────────────────────────────
    _t("Quick Scan", "bug_analysis",
       "Rapid triage: top 3-5 critical findings with traffic-light rating",
       _QUICK_BUG),
    _t("Quick Scan", "code_design",
       "500-word architectural snapshot with top concerns",
       _QUICK_DESIGN),
    _t("Quick Scan", "code_flow",
       "Concise 10-step flow summary for quick understanding",
       _QUICK_FLOW),
    _t("Quick Scan", "mermaid",
       "Minimal 10-node diagram for 10-second comprehension",
       _QUICK_MERMAID),
    _t("Quick Scan", "requirement",
       "Top 5-10 requirements with implementation status",
       _QUICK_REQUIREMENT),
    _t("Quick Scan", "static_analysis",
       "Critical findings only with traffic-light quality rating",
       _QUICK_STATIC),
    _t("Quick Scan", "comment_generator",
       "3-5 critical comments with GO/NO-GO recommendation",
       _QUICK_COMMENT),
    _t("Quick Scan", "commit_analysis",
       "300-word release readiness snapshot",
       _QUICK_COMMIT),

    # ── Report Generator ─────────────────────────────────────────────────────
    _t("Report Generator", "bug_analysis",
       "Formal audit report with severity matrix and remediation plan",
       _REPORT_BUG),
    _t("Report Generator", "code_design",
       "Architecture review document with quality scores and debt register",
       _REPORT_DESIGN),
    _t("Report Generator", "code_flow",
       "Operations-grade flow documentation with monitoring points",
       _REPORT_FLOW),
    _t("Report Generator", "mermaid",
       "Presentation-quality diagrams with professional styling",
       _REPORT_MERMAID),
    _t("Report Generator", "requirement",
       "IEEE 830-inspired SRS with traceability matrix",
       _REPORT_REQUIREMENT),
    _t("Report Generator", "static_analysis",
       "Formal audit report with CWE references and quality metrics",
       _REPORT_STATIC),
    _t("Report Generator", "comment_generator",
       "Structured review document with merge readiness checklist",
       _REPORT_COMMENT),
    _t("Report Generator", "commit_analysis",
       "Release readiness report for change advisory board",
       _REPORT_COMMIT),
]

# ---------------------------------------------------------------------------
# Merge templates from sub-modules
# ---------------------------------------------------------------------------

from config.templates.language_expert import LANGUAGE_EXPERT_TEMPLATES, LANGUAGE_INDEX
from config.templates.compliance import COMPLIANCE_TEMPLATES
from config.templates.performance import PERFORMANCE_TEMPLATES, PERFORMANCE_ADDONS
from config.language_families import get_language_family

TEMPLATES.extend(LANGUAGE_EXPERT_TEMPLATES)
TEMPLATES.extend(COMPLIANCE_TEMPLATES)
TEMPLATES.extend(PERFORMANCE_TEMPLATES)

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_INDEX: dict[tuple[str, str], PromptTemplate] = {
    (t.category, t.agent): t for t in TEMPLATES
}


def get_templates_for_agent(agent: str) -> list[PromptTemplate]:
    """Return all templates applicable to the given agent key."""
    return [t for t in TEMPLATES if t.agent == agent]


def get_template(category: str, agent: str) -> PromptTemplate | None:
    """Return a specific template by category + agent, or None."""
    return _INDEX.get((category, agent))


def _merge_text(base: str, addon: str) -> str:
    """Combine a base template with a language-family addon."""
    return f"{base}\n\n{addon}"


def apply_template(
    category: str | None,
    agent: str,
    custom_prompt: str | None,
    language: str | None = None,
) -> str | None:
    """Merge a template into *custom_prompt* using APPEND mode.

    Rules:
    - *category* is None or no matching template  ->  return custom_prompt unchanged
    - *custom_prompt* is None / empty              ->  return ``__append__`` + template
    - *custom_prompt* starts with ``__append__``   ->  prepend template before user text
    - *custom_prompt* is in overwrite mode          ->  user override wins; skip template

    Language-aware categories:
    - **Language Expert** — selects template by language family (via LANGUAGE_INDEX)
    - **Performance Deep Dive** — merges universal template + family addon (via PERFORMANCE_ADDONS)

    This keeps the user in full control: overwrite mode always beats templates.
    """
    if not category:
        return custom_prompt

    family = get_language_family(language)

    # --- Language Expert: look up by family instead of category ---
    if category == "Language Expert":
        template = LANGUAGE_INDEX.get((family, agent))
        if template is None:
            # Fall back to generic
            template = LANGUAGE_INDEX.get(("generic", agent))
        if template is None:
            return custom_prompt
        text = template.prompt_text
    # --- Performance Deep Dive: universal + optional addon ---
    elif category == "Performance Deep Dive":
        template = get_template(category, agent)
        if template is None:
            return custom_prompt
        text = template.prompt_text
        addon = PERFORMANCE_ADDONS.get((family, agent))
        if addon:
            text = _merge_text(text, addon)
    # --- All other categories: standard lookup ---
    else:
        template = get_template(category, agent)
        if template is None:
            return custom_prompt
        text = template.prompt_text

    if not custom_prompt:
        return f"{_APPEND_PREFIX}{text}"

    if custom_prompt.startswith(_APPEND_PREFIX):
        user_text = custom_prompt[len(_APPEND_PREFIX):]
        return f"{_APPEND_PREFIX}{text}\n\n{user_text}"

    # Overwrite mode — user's explicit override takes priority
    return custom_prompt
