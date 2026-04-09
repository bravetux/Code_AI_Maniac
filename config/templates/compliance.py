"""Compliance prompt templates — one per standard per agent."""

from __future__ import annotations

from config.prompt_templates import PromptTemplate

COMPLIANCE_CATEGORIES: list[str] = [
    "Compliance: SOC 2",
    "Compliance: GDPR",
    "Compliance: PCI-DSS",
    "Compliance: HIPAA",
    "Compliance: ISO 27001",
    "Compliance: Generic Audit",
]


def _t(
    category: str, agent: str, description: str, text: str,
) -> PromptTemplate:
    return PromptTemplate(
        category=category,
        agent=agent,
        label=category,
        description=description,
        prompt_text=text,
    )


# ===================================================================
# SOC 2 — Trust Service Criteria
# ===================================================================

_SOC2_BUG = """\
## Compliance Analysis: SOC 2

Analyze the code for bugs that could violate SOC 2 Trust Service Criteria.

Focus your analysis on these specific controls:

1. **CC6.1 — Logical Access:** Look for bugs in authentication or authorization \
logic that could allow unauthorized access to systems or data. Check for \
hard-coded credentials, missing access checks, and broken session management.
2. **CC6.3 — Role-Based Access:** Identify defects in role assignment, privilege \
escalation paths, or missing least-privilege enforcement.
3. **CC7.2 — System Monitoring:** Find bugs that could suppress or corrupt audit \
log entries, break alerting pipelines, or allow security events to go undetected.
4. **CC8.1 — Change Management:** Detect issues where code changes bypass \
required approval gates, version control hooks, or deployment safeguards.
5. **CC6.6 — Boundary Protection:** Look for bugs in input validation, API \
gateway logic, or network boundary checks that weaken system boundaries.
6. **CC7.1 — Vulnerability Management:** Identify use of known-vulnerable \
libraries, unsafe deserialization, or missing security patches.

Rate each bug by SOC 2 impact: **Critical** (control failure), **High** \
(control weakness), **Medium** (control gap), **Low** (improvement opportunity).

For each finding, cite the specific control/article violated \
(e.g., "Violates CC6.1 — Logical Access Security").
"""

_SOC2_DESIGN = """\
## Compliance Analysis: SOC 2

Evaluate the code's design against SOC 2 Trust Service Criteria.

Assess the architecture for alignment with these controls:

1. **CC6.1 — Logical Access Security:** Does the design implement a centralized \
authentication and authorization layer? Are access decisions made at a single \
enforcement point, or scattered across the codebase?
2. **CC6.2 — Credential Management:** Is there a design pattern for secure \
credential storage, rotation, and revocation? Are secrets managed via vault \
or environment injection rather than config files?
3. **CC7.2 — Monitoring and Detection:** Does the architecture include structured \
logging, centralized log aggregation, and alerting? Are security-relevant events \
captured at every tier (API, service, data)?
4. **CC8.1 — Change Management:** Does the design support traceable deployments, \
immutable artifacts, and rollback capability? Are feature flags and canary \
releases integrated?
5. **CC9.1 — Risk Mitigation:** Does the design include redundancy, circuit \
breakers, and graceful degradation for critical paths?
6. **CC5.2 — Internal Controls:** Are there design patterns for separation of \
duties — e.g., the code that writes data cannot also approve that data?

For each design concern, recommend a specific architectural pattern or library \
that would bring the design into SOC 2 alignment.

For each finding, cite the specific control/article violated \
(e.g., "Gaps in CC6.2 — Credential Management").
"""

_SOC2_FLOW = """\
## Compliance Analysis: SOC 2

Trace data flows through the code with a focus on SOC 2 Trust Service Criteria.

Map the following flow dimensions:

1. **CC6.1 — Access Control Flow:** Trace every path from user input to \
protected resource. Document where access decisions are made, what identity \
context is available, and whether any path bypasses access checks.
2. **CC6.7 — Data Transmission:** Map all data leaving the system boundary — \
API calls, file exports, email, message queues. For each exit point, verify \
encryption in transit and confirm the recipient is authorized.
3. **CC7.2 — Audit Trail Flow:** Trace how security events propagate from \
origin to log storage. Identify any gaps where an event could occur without \
being logged, or where log entries could be tampered with.
4. **CC6.5 — Data Classification Flow:** Follow sensitive data (PII, secrets, \
financial data) from ingress to storage to egress. Identify where \
classification is applied and where it is lost or ignored.
5. **CC8.1 — Change Propagation:** Trace how configuration and code changes \
flow from commit to production. Identify any path that bypasses CI/CD gates.
6. **CC9.2 — Vendor Data Flow:** Map data shared with third-party services. \
Document what data is sent, whether consent was obtained, and how vendor \
access is revoked.

Produce a flow summary table: Source → Processing → Destination → SOC 2 Control.

For each finding, cite the specific control/article violated \
(e.g., "Unencrypted egress violates CC6.7").
"""

_SOC2_STATIC = """\
## Compliance Analysis: SOC 2

Perform static analysis focused on SOC 2 Trust Service Criteria violations.

Scan the code for these specific violation patterns:

1. **CC6.1 — Hard-Coded Credentials:** Detect passwords, API keys, tokens, \
or connection strings embedded in source code. Flag any secret not loaded \
from an environment variable or secrets manager.
2. **CC6.3 — Privilege Violations:** Find code that grants admin or elevated \
privileges without explicit role checks. Detect wildcard permissions, \
missing authorization decorators, and unchecked user roles.
3. **CC7.2 — Missing Audit Logging:** Identify state-changing operations \
(create, update, delete, login, permission change) that do not emit an audit \
log entry. Every mutation must be logged.
4. **CC6.6 — Input Validation Gaps:** Flag endpoints or functions that accept \
external input without sanitization, type checking, or length constraints.
5. **CC8.1 — Unsafe Deployment Artifacts:** Detect debug flags, development \
endpoints, or test backdoors that should not be present in production code.
6. **CC6.8 — Encryption Gaps:** Find data at rest that is not encrypted, \
or cryptographic operations using weak algorithms (MD5, SHA-1 for security, \
DES, RC4).

Severity mapping: Hard-coded secrets = Critical, missing audit logs = High, \
input validation gaps = High, encryption gaps = Critical.

For each finding, cite the specific control/article violated \
(e.g., "Hard-coded API key violates CC6.1").
"""

_SOC2_REQ = """\
## Compliance Analysis: SOC 2

Extract compliance requirements implied or implemented by this code, mapped \
to SOC 2 Trust Service Criteria.

For each requirement you discover, provide:

1. **CC6.x — Access Control Requirements:** What access control requirements \
does this code implement? Does it enforce CC6.1 (logical access), CC6.2 \
(credential management), CC6.3 (role-based access)? List each requirement \
with its current implementation status.
2. **CC7.x — Monitoring Requirements:** What monitoring and alerting \
requirements are implemented? Map to CC7.1 (vulnerability detection), \
CC7.2 (anomaly detection), CC7.3 (incident response triggers).
3. **CC8.x — Change Management Requirements:** What change management \
controls does the code enforce? Map to CC8.1 (change authorization), \
CC8.2 (infrastructure changes), CC8.3 (change testing).
4. **CC9.x — Risk Mitigation Requirements:** What risk mitigation strategies \
are present? Map to CC9.1 (risk identification) and CC9.2 (vendor risk).
5. **Gaps:** For each SOC 2 control area, list requirements that are NOT \
addressed by the current code but SHOULD be, based on the data and \
operations the code handles.
6. **Implicit Requirements:** Identify requirements that the code implies \
but does not explicitly enforce — e.g., the code stores PII but has no \
data retention policy.

Output a requirements traceability matrix: Requirement → SOC 2 Control → \
Status (Implemented | Partial | Missing).

For each finding, cite the specific control/article violated \
(e.g., "Missing requirement for CC7.2 — Anomaly Detection").
"""

_SOC2_COMMENT = """\
## Compliance Analysis: SOC 2

Write PR review comments focused on SOC 2 Trust Service Criteria compliance.

For each comment, apply this framework:

1. **CC6.1 — Access Control:** Comment on any code that handles \
authentication, authorization, or session management. Verify that every \
protected resource has an explicit access check. Flag missing checks as \
blocking.
2. **CC6.2 — Credential Handling:** Comment on any code that touches \
secrets, tokens, or connection strings. Ensure credentials are not logged, \
not hard-coded, and rotated on a schedule.
3. **CC7.2 — Audit Trail:** Comment on state-changing operations that lack \
audit logging. Suggest specific log formats including actor, action, \
resource, timestamp, and outcome.
4. **CC8.1 — Change Safety:** Comment on whether the PR includes tests, \
migration scripts, and rollback procedures where applicable.
5. **CC6.6 — Input Validation:** Comment on any new endpoint or function \
parameter that accepts external input without validation.
6. **CC6.8 — Encryption:** Comment on any data storage or transmission \
that lacks encryption or uses deprecated algorithms.

Format each comment as:
**[SOC 2 {Control ID}] {Severity}:** {Description} → {Recommended Fix}

For each finding, cite the specific control/article violated \
(e.g., "[SOC 2 CC6.1] HIGH: Missing auth check on /api/admin endpoint").
"""


# ===================================================================
# GDPR — General Data Protection Regulation
# ===================================================================

_GDPR_BUG = """\
## Compliance Analysis: GDPR

Analyze the code for bugs that could cause GDPR violations.

Focus on these specific articles and requirements:

1. **Article 5(1)(f) — Integrity & Confidentiality:** Look for bugs that \
could lead to unauthorized disclosure of personal data — buffer overflows, \
SQL injection, insecure direct object references, or broken access controls \
on personal data endpoints.
2. **Article 17 — Right to Erasure:** Find bugs in data deletion logic. \
Does the delete operation cascade to all stores (database, cache, backups, \
search indices)? Are there code paths where deletion silently fails?
3. **Article 25 — Data Protection by Design:** Identify bugs where personal \
data is processed without purpose limitation — e.g., logging PII that is \
not needed for the operation, or passing personal data to functions that \
do not require it.
4. **Article 32 — Security of Processing:** Detect bugs in encryption, \
hashing, or anonymization logic that weaken the security of personal data. \
Check for use of weak algorithms or improper key management.
5. **Article 33 — Breach Notification:** Find bugs that could delay or \
prevent breach detection — e.g., swallowed exceptions in security-critical \
paths, missing monitoring for unauthorized data access.
6. **Article 44 — International Transfers:** Identify code paths where \
personal data is sent to external services without checking the data \
residency or transfer mechanism (SCCs, adequacy decisions).

Rate each bug: **Violation** (active breach), **Risk** (likely breach), \
**Gap** (missing safeguard).

For each finding, cite the specific control/article violated \
(e.g., "Violates Article 17 — Right to Erasure").
"""

_GDPR_DESIGN = """\
## Compliance Analysis: GDPR

Evaluate the code's design for GDPR compliance.

Assess architecture against these articles:

1. **Article 25 — Data Protection by Design and Default:** Does the \
architecture minimize personal data collection? Is there a data \
classification layer that tags PII at ingestion? Are default settings \
privacy-preserving (opt-in, not opt-out)?
2. **Article 5(1)(b) — Purpose Limitation:** Does the design enforce that \
personal data collected for one purpose is not reused for another? Are \
there separate data stores or access policies per purpose?
3. **Article 5(1)(e) — Storage Limitation:** Does the design include \
automated data retention and expiry policies? Is there a TTL mechanism \
for personal data?
4. **Article 35 — Data Protection Impact Assessment:** Does the architecture \
support DPIA requirements? Can you identify high-risk processing activities \
(profiling, large-scale monitoring, sensitive data) in the design?
5. **Article 20 — Data Portability:** Does the design support exporting a \
user's personal data in a structured, machine-readable format (JSON, CSV)?
6. **Article 28 — Processor Obligations:** When data is shared with \
third-party services, does the design enforce contractual controls, data \
minimization, and return/deletion obligations?

For each design concern, suggest a specific pattern (e.g., "Implement a \
PII tagging middleware that classifies data at ingestion").

For each finding, cite the specific control/article violated \
(e.g., "Design lacks Article 25 — Data Protection by Design").
"""

_GDPR_FLOW = """\
## Compliance Analysis: GDPR

Trace personal data flows through the code to verify GDPR compliance.

Map these critical flow dimensions:

1. **Article 13/14 — Transparency of Data Collection:** Trace where personal \
data enters the system. For each ingress point, verify that a privacy notice \
or consent mechanism is triggered before processing begins.
2. **Article 5(1)(b) — Purpose-Bound Flow:** Follow each personal data \
element from collection to every point where it is read. Verify that each \
read is justified by the original collection purpose. Flag cross-purpose \
data reuse.
3. **Article 17 — Erasure Flow:** Trace the delete/forget path. When a \
user requests erasure, does the flow reach ALL stores — primary DB, caches, \
search indices, analytics pipelines, backups, third-party systems?
4. **Article 44-49 — Cross-Border Transfer Flow:** Map every point where \
personal data leaves the deployment region. Document the destination \
country, the legal basis for transfer, and whether encryption is applied \
in transit.
5. **Article 6 — Lawful Basis Flow:** For each processing activity, trace \
whether a lawful basis check (consent, contract, legitimate interest) is \
performed before the data is used.
6. **Article 32 — Security Flow:** Trace personal data through encryption \
and decryption boundaries. Identify any segment where personal data exists \
in plaintext outside a secure boundary.

Produce a data flow map: Data Subject → Collection Point → Processing → \
Storage → Sharing → Deletion.

For each finding, cite the specific control/article violated \
(e.g., "PII flows to analytics without Article 6 lawful basis check").
"""

_GDPR_STATIC = """\
## Compliance Analysis: GDPR

Perform static analysis to detect GDPR compliance violations in the code.

Scan for these violation patterns:

1. **Article 5(1)(f) — PII in Logs:** Detect personal data (names, emails, \
IP addresses, phone numbers, national IDs) written to log files, console \
output, or error messages. PII must be masked or excluded from logs.
2. **Article 25 — Missing Anonymization:** Find personal data that is \
stored or processed without anonymization or pseudonymization where the \
full identity is not required for the operation.
3. **Article 17 — Incomplete Deletion:** Identify delete operations that \
do not cascade to all related tables, caches, or external systems. Soft \
deletes that retain PII beyond the retention period are violations.
4. **Article 7 — Consent Handling Flaws:** Detect consent collection that \
uses pre-checked boxes, bundled consent, or lacks a withdrawal mechanism. \
Verify that consent is recorded with timestamp and scope.
5. **Article 32 — Weak Cryptography:** Flag use of MD5, SHA-1, DES, or \
ECB mode for protecting personal data. Verify that encryption keys are \
not stored alongside encrypted data.
6. **Article 30 — Missing Processing Records:** Identify data processing \
activities that are not registered in a processing activity log. Every \
operation on personal data should be traceable to a documented purpose.

Severity: PII in logs = High, missing anonymization = High, incomplete \
deletion = Critical, weak crypto = Critical.

For each finding, cite the specific control/article violated \
(e.g., "Email logged in plaintext — violates Article 5(1)(f)").
"""

_GDPR_REQ = """\
## Compliance Analysis: GDPR

Extract GDPR compliance requirements from the code and map them to \
specific articles of the regulation.

For each requirement discovered:

1. **Articles 13-14 — Transparency Requirements:** What data collection \
disclosures does the code implement or imply? Are privacy notices \
triggered at each collection point? List each requirement and its \
implementation status.
2. **Article 6 — Lawful Basis Requirements:** For each processing activity, \
identify the lawful basis (consent, contract, legitimate interest, legal \
obligation, vital interest, public task). Document whether the basis is \
explicitly enforced in code.
3. **Articles 15-22 — Data Subject Rights:** Which rights are implemented? \
Map code features to: access (Art. 15), rectification (Art. 16), erasure \
(Art. 17), restriction (Art. 18), portability (Art. 20), objection (Art. 21).
4. **Article 25 — Privacy by Design Requirements:** What data minimization \
and default privacy requirements are embedded in the code?
5. **Article 35 — DPIA Requirements:** Based on the data processed, does \
this code trigger a DPIA obligation? Identify high-risk processing.
6. **Gap Analysis:** List GDPR requirements that SHOULD be present based \
on the personal data handled but are NOT implemented in the code.

Output a requirements matrix: Requirement → GDPR Article → Status \
(Implemented | Partial | Missing).

For each finding, cite the specific control/article violated \
(e.g., "No implementation of Article 17 — Right to Erasure").
"""

_GDPR_COMMENT = """\
## Compliance Analysis: GDPR

Write PR review comments focused on GDPR compliance.

Apply this review framework:

1. **Article 5(1)(f) — Data Leakage:** Comment on any code that logs, \
prints, or transmits personal data. Require masking or removal. Block \
the PR if PII is exposed in logs or error messages.
2. **Article 25 — Privacy by Design:** Comment on new data collection \
or processing that does not apply data minimization. Suggest collecting \
only what is strictly necessary.
3. **Article 17 — Erasure Support:** Comment on new data stores or schemas \
that lack a deletion mechanism. Require a cascade-delete path for every \
new personal data store.
4. **Article 32 — Security Measures:** Comment on encryption usage, key \
management, and hashing of personal data. Require strong algorithms \
(AES-256, bcrypt/argon2 for passwords).
5. **Article 6 — Lawful Basis:** Comment on new processing activities \
that lack a documented lawful basis. Require a comment or annotation \
linking each processing activity to its legal justification.
6. **Article 33 — Breach Detection:** Comment on error handling in \
security-critical paths. Require that exceptions are logged and \
monitored, not silently swallowed.

Format each comment as:
**[GDPR Art. {N}] {Severity}:** {Description} → {Recommended Fix}

For each finding, cite the specific control/article violated \
(e.g., "[GDPR Art. 17] HIGH: New user table lacks cascade delete").
"""


# ===================================================================
# PCI-DSS — Payment Card Industry Data Security Standard
# ===================================================================

_PCIDSS_BUG = """\
## Compliance Analysis: PCI-DSS

Analyze the code for bugs that could violate PCI-DSS requirements.

Focus on these specific requirements:

1. **Req 3.4 — Render PAN Unreadable:** Look for bugs where the Primary \
Account Number (PAN) is stored in plaintext — in databases, log files, \
temporary files, or error messages. Verify that PAN is encrypted, hashed, \
or truncated at rest.
2. **Req 4.1 — Encrypt Transmission:** Find bugs where cardholder data is \
transmitted over unencrypted channels — HTTP instead of HTTPS, unencrypted \
database connections, plaintext message queues.
3. **Req 6.5 — Secure Coding:** Identify common vulnerabilities in payment \
code paths: SQL injection, XSS, CSRF, buffer overflows, insecure \
deserialization, and broken authentication.
4. **Req 8.2 — Authentication Bugs:** Detect bugs in multi-factor \
authentication, password validation, or session management for systems \
that process cardholder data.
5. **Req 10.2 — Audit Trail Bugs:** Find bugs where security events \
(access to cardholder data, failed login attempts, changes to accounts) \
are not logged or where log entries can be modified.
6. **Req 3.1 — Data Retention Bugs:** Identify code that retains \
cardholder data beyond the authorized retention period, or that fails to \
purge data according to the defined schedule.

Rate each bug: **Critical** (immediate PAN exposure), **High** (cardholder \
data at risk), **Medium** (control weakness), **Low** (hardening gap).

For each finding, cite the specific control/article violated \
(e.g., "PAN stored in plaintext — violates Req 3.4").
"""

_PCIDSS_DESIGN = """\
## Compliance Analysis: PCI-DSS

Evaluate the code's architecture for PCI-DSS compliance.

Assess the design against these requirements:

1. **Req 1.3 — Network Segmentation:** Does the architecture isolate the \
Cardholder Data Environment (CDE) from other systems? Is there a clear \
boundary between in-scope and out-of-scope components?
2. **Req 2.2 — Secure Configuration:** Does the design enforce hardened \
configurations? Are default passwords, unnecessary services, and sample \
data removed? Is there a configuration management pattern?
3. **Req 3.4 — Data Protection Architecture:** Is there a centralized \
tokenization or encryption service for PAN? Does the design prevent PAN \
from leaking into non-CDE components (logs, analytics, support tools)?
4. **Req 6.1 — Vulnerability Management:** Does the architecture include \
dependency scanning, SAST/DAST integration, and automated patching? Are \
third-party libraries inventoried and monitored?
5. **Req 7.1 — Access Control Design:** Is access to cardholder data \
restricted by role? Does the design implement least privilege? Are \
access control lists maintained centrally?
6. **Req 10.1 — Logging Architecture:** Is there a centralized, tamper-evident \
logging system? Are logs from all CDE components aggregated and retained \
for at least 12 months (Req 10.7)?

For each design gap, recommend a specific architectural change aligned \
with the PCI-DSS requirement.

For each finding, cite the specific control/article violated \
(e.g., "No CDE segmentation — violates Req 1.3").
"""

_PCIDSS_FLOW = """\
## Compliance Analysis: PCI-DSS

Trace cardholder data flows through the code for PCI-DSS compliance.

Map these critical flows:

1. **Req 3.1 — Cardholder Data Lifecycle:** Trace PAN and cardholder data \
from the moment it enters the system (form submission, API call, file upload) \
through processing, storage, and eventual deletion. Document every component \
that touches cardholder data.
2. **Req 3.4 — Encryption Boundaries:** Map where PAN is encrypted and \
decrypted. Identify any segment where PAN exists in plaintext. Verify that \
encryption keys are stored separately from encrypted data (Req 3.5).
3. **Req 4.1 — Transmission Security:** Trace all network hops for \
cardholder data. Verify TLS 1.2+ on every segment. Flag any plaintext \
transmission, including internal service-to-service calls.
4. **Req 10.2 — Audit Event Flow:** Trace how access to cardholder data \
generates audit events. Verify that events flow to a centralized, \
tamper-evident log store without gaps.
5. **Req 7.1 — Access Decision Points:** Map every point where access to \
cardholder data is granted or denied. Verify that access decisions are \
based on role and need-to-know.
6. **Req 9.4 — Media Handling Flow:** If cardholder data is exported to \
files, trace the file lifecycle — creation, transfer, storage, and \
destruction. Verify secure deletion.

Produce a CDE data flow diagram: Entry → Processing → Storage → Exit → \
Destruction, annotated with PCI-DSS controls at each step.

For each finding, cite the specific control/article violated \
(e.g., "PAN visible in plaintext between services — violates Req 4.1").
"""

_PCIDSS_STATIC = """\
## Compliance Analysis: PCI-DSS

Perform static analysis to detect PCI-DSS violations in the code.

Scan for these specific patterns:

1. **Req 3.4 — PAN Exposure:** Detect patterns matching credit card numbers \
(regex for 13-19 digit sequences with Luhn check) in source code, \
configuration files, test fixtures, or comments. Any PAN in source is a \
critical violation.
2. **Req 4.1 — Insecure Protocols:** Flag use of HTTP (not HTTPS), FTP \
(not SFTP), unencrypted SMTP, or TLS versions below 1.2. Detect \
`verify=False` or certificate validation bypass.
3. **Req 6.5.1 — Injection Flaws:** Identify SQL, NoSQL, LDAP, OS command, \
and XPath injection vulnerabilities. Flag string concatenation in queries \
and unparameterized statements.
4. **Req 6.5.7 — XSS:** Detect user input rendered in HTML without \
encoding or sanitization. Flag use of `innerHTML`, `dangerouslySetInnerHTML`, \
or template engines with auto-escaping disabled.
5. **Req 8.2 — Weak Authentication:** Find hardcoded passwords, default \
credentials, missing MFA enforcement, and insecure password storage \
(plaintext, MD5, SHA-1 without salt).
6. **Req 2.1 — Default Settings:** Detect default ports, default admin \
usernames, sample data, debug modes, and development configurations that \
should not be present in production code.

Severity: PAN in source = Critical, injection = Critical, insecure \
protocol = High, weak auth = High, defaults = Medium.

For each finding, cite the specific control/article violated \
(e.g., "Test fixture contains PAN '4111...' — violates Req 3.4").
"""

_PCIDSS_REQ = """\
## Compliance Analysis: PCI-DSS

Extract PCI-DSS compliance requirements from the code.

Map code features to these PCI-DSS requirements:

1. **Req 1 — Network Security Requirements:** What firewall rules, network \
segmentation, or boundary protection does the code implement or require? \
Document CDE boundary definitions.
2. **Req 3 — Stored Data Requirements:** What data protection mechanisms \
are implemented for cardholder data at rest? Map to Req 3.1 (retention), \
Req 3.4 (render PAN unreadable), Req 3.5 (key management).
3. **Req 6 — Secure Development Requirements:** What secure coding \
practices are enforced? Map to Req 6.1 (vulnerability management), \
Req 6.3 (code review), Req 6.5 (common vulnerabilities).
4. **Req 7-8 — Access Control Requirements:** What access controls are \
implemented? Map to Req 7.1 (need-to-know), Req 8.1 (user identification), \
Req 8.2 (authentication mechanisms).
5. **Req 10 — Monitoring Requirements:** What logging and monitoring is \
implemented? Map to Req 10.1 (audit trails), Req 10.2 (event logging), \
Req 10.5 (log integrity).
6. **Gap Analysis:** For each PCI-DSS requirement area, list controls that \
are NOT present in the code but are required given the cardholder data \
operations performed.

Output a compliance matrix: Requirement → PCI-DSS Control → Status \
(Implemented | Partial | Missing | N/A).

For each finding, cite the specific control/article violated \
(e.g., "No encryption at rest — missing Req 3.4 implementation").
"""

_PCIDSS_COMMENT = """\
## Compliance Analysis: PCI-DSS

Write PR review comments focused on PCI-DSS compliance.

Apply this payment security review framework:

1. **Req 3.4 — PAN Handling:** Comment on any code that reads, writes, \
or transmits PAN. Verify tokenization or encryption. Block the PR if PAN \
is stored in plaintext anywhere — including test data.
2. **Req 4.1 — Transmission Security:** Comment on any network calls \
involving cardholder data. Require TLS 1.2+ and certificate validation. \
Flag `verify=False` as blocking.
3. **Req 6.5 — Secure Coding:** Comment on injection vulnerabilities, \
XSS, CSRF, insecure deserialization, and other OWASP Top 10 issues in \
payment-related code paths.
4. **Req 10.2 — Audit Logging:** Comment on state-changing operations in \
the CDE that lack audit logging. Require structured log entries with \
actor, action, resource, timestamp, and result.
5. **Req 7.1 — Least Privilege:** Comment on access control changes. \
Verify that new permissions follow least-privilege. Flag wildcard \
permissions or overly broad role assignments.
6. **Req 8.2 — Authentication:** Comment on authentication changes. \
Require strong password policies, MFA where applicable, and secure \
session management.

Format each comment as:
**[PCI-DSS {Req}] {Severity}:** {Description} → {Recommended Fix}

For each finding, cite the specific control/article violated \
(e.g., "[PCI-DSS Req 3.4] CRITICAL: PAN logged in payment_service.py:42").
"""


# ===================================================================
# HIPAA — Health Insurance Portability and Accountability Act
# ===================================================================

_HIPAA_BUG = """\
## Compliance Analysis: HIPAA

Analyze the code for bugs that could cause HIPAA violations involving \
Protected Health Information (PHI).

Focus on these HIPAA Security Rule requirements:

1. **§164.312(a)(1) — Access Control:** Look for bugs in authentication \
or authorization that could allow unauthorized access to PHI. Check for \
missing role-based access controls, broken session management, and \
privilege escalation paths in health data endpoints.
2. **§164.312(e)(1) — Transmission Security:** Find bugs where PHI is \
transmitted without encryption — HTTP endpoints handling health data, \
unencrypted database connections, plaintext HL7 or FHIR messages.
3. **§164.312(b) — Audit Controls:** Detect bugs that could prevent audit \
trail generation for PHI access. Look for swallowed exceptions, missing \
log statements, or audit log corruption in health data access paths.
4. **§164.312(c)(1) — Integrity Controls:** Identify bugs that could allow \
PHI to be improperly altered — missing input validation on health records, \
race conditions in concurrent updates, or missing checksums.
5. **§164.312(d) — Authentication Bugs:** Find bugs in person or entity \
authentication mechanisms for systems handling PHI. Check MFA \
implementation, token validation, and identity verification logic.
6. **§164.308(a)(6) — Incident Response:** Detect bugs that could delay \
breach detection or response — silent failures in security monitoring, \
missing alerts for unauthorized PHI access, or broken notification chains.

Rate each bug: **Violation** (active PHI exposure), **Risk** (likely \
breach), **Gap** (missing safeguard).

For each finding, cite the specific control/article violated \
(e.g., "PHI accessible without auth — violates §164.312(a)(1)").
"""

_HIPAA_DESIGN = """\
## Compliance Analysis: HIPAA

Evaluate the code's architecture for HIPAA compliance.

Assess the design against these requirements:

1. **§164.312(a)(1) — Access Control Design:** Does the architecture \
implement unique user identification, emergency access procedures, \
automatic logoff, and encryption/decryption of PHI? Is there a \
centralized access control service?
2. **§164.308(a)(4) — Information Access Management:** Does the design \
enforce role-based access to PHI with formal authorization procedures? \
Are access rights reviewed and revoked when roles change?
3. **§164.312(e)(1) — Transmission Architecture:** Does the design ensure \
all PHI in transit is encrypted? Are HL7, FHIR, and API communications \
secured with TLS 1.2+? Is there end-to-end encryption for PHI?
4. **§164.308(a)(7) — Contingency Planning:** Does the architecture \
support data backup, disaster recovery, and emergency mode operation? \
Can PHI be restored from backups within the required timeframe?
5. **§164.314(a) — Business Associate Architecture:** When PHI is shared \
with third-party services, does the design enforce BAA requirements? \
Are third-party data flows isolated and auditable?
6. **§164.312(b) — Audit Architecture:** Is there a comprehensive audit \
logging system that captures all PHI access, modification, and deletion \
events? Are logs tamper-evident and retained for six years?

For each design gap, recommend a specific architectural pattern for \
HIPAA compliance.

For each finding, cite the specific control/article violated \
(e.g., "No audit log for PHI access — gaps in §164.312(b)").
"""

_HIPAA_FLOW = """\
## Compliance Analysis: HIPAA

Trace PHI flows through the code for HIPAA compliance verification.

Map these critical flow dimensions:

1. **§164.312(a)(1) — PHI Access Flow:** Trace every path from user \
request to PHI retrieval. Document where identity is verified, where \
authorization is checked, and whether any path allows unauthenticated \
PHI access.
2. **§164.312(e)(1) — PHI Transmission Flow:** Map all network segments \
where PHI travels. Verify encryption at every hop — between client and \
server, between services, between application and database.
3. **§164.530(j) — PHI Retention Flow:** Trace PHI from creation through \
active use to archival and destruction. Verify that retention policies \
are enforced and that PHI is securely destroyed when the retention \
period expires.
4. **§164.524 — Patient Access Flow:** Trace how a patient's request \
for their records is fulfilled. Does the flow cover all PHI stores? \
Can records be exported in the required timeframe (30 days)?
5. **§164.528 — Disclosure Accounting Flow:** Trace how PHI disclosures \
to third parties are recorded. Verify that an accounting of disclosures \
can be generated for any patient for the past six years.
6. **§164.308(a)(6) — Breach Detection Flow:** Trace how unauthorized \
PHI access is detected and escalated. Map the flow from anomaly detection \
to incident response to notification.

Produce a PHI flow map: Data Subject → Collection → Processing → Storage → \
Sharing → Archival → Destruction.

For each finding, cite the specific control/article violated \
(e.g., "PHI sent to analytics service without BAA — violates §164.314(a)").
"""

_HIPAA_STATIC = """\
## Compliance Analysis: HIPAA

Perform static analysis to detect HIPAA compliance violations in the code.

Scan for these violation patterns:

1. **§164.312(a)(1) — PHI in Logs:** Detect Protected Health Information \
(patient names, MRNs, SSNs, diagnoses, medications, lab results) written \
to log files, console output, or error messages. PHI must never appear \
in application logs.
2. **§164.312(e)(1) — Unencrypted PHI:** Find PHI stored without \
encryption at rest. Flag database columns containing health data that \
lack column-level encryption or transparent data encryption.
3. **§164.312(c)(1) — Integrity Violations:** Detect PHI modification \
operations that lack validation, checksums, or transactional integrity. \
Flag concurrent write paths without proper locking.
4. **§164.312(d) — Weak Authentication:** Find hardcoded credentials, \
default passwords, missing MFA enforcement, and insecure session \
management in systems that handle PHI.
5. **§164.530(c) — Missing Safeguards:** Identify PHI processing code \
that lacks appropriate administrative, physical, or technical safeguards — \
missing access controls, unprotected file storage, or insecure temp files.
6. **§164.312(b) — Missing Audit Events:** Identify PHI access operations \
(read, create, update, delete, export, print) that do not generate audit \
log entries. Every PHI touchpoint must be auditable.

Severity: PHI in logs = Critical, unencrypted PHI = Critical, missing \
audit = High, weak auth = High, integrity gaps = Medium.

For each finding, cite the specific control/article violated \
(e.g., "Patient SSN in error log — violates §164.312(a)(1)").
"""

_HIPAA_REQ = """\
## Compliance Analysis: HIPAA

Extract HIPAA compliance requirements from the code, mapped to the \
Security Rule and Privacy Rule.

For each requirement discovered:

1. **§164.312 — Technical Safeguard Requirements:** What access control, \
audit, integrity, authentication, and transmission security requirements \
does this code implement? Map to specific subsections: (a)(1) access, \
(b) audit, (c)(1) integrity, (d) authentication, (e)(1) transmission.
2. **§164.308 — Administrative Safeguard Requirements:** What security \
management, workforce security, information access management, and \
incident response requirements are embedded in the code?
3. **§164.310 — Physical Safeguard Requirements:** If the code manages \
infrastructure, what facility access, workstation use, and device/media \
control requirements are implemented?
4. **§164.524-§164.528 — Patient Rights Requirements:** Does the code \
implement access rights (§164.524), amendment rights (§164.526), and \
accounting of disclosures (§164.528)?
5. **§164.314 — Business Associate Requirements:** When PHI is shared \
with external services, are BAA requirements enforced in the code? \
Map data sharing patterns to BAA obligations.
6. **Gap Analysis:** List HIPAA requirements that are NOT addressed by \
the current code but SHOULD be, based on the PHI operations performed.

Output a compliance matrix: Requirement → HIPAA Section → Status \
(Implemented | Partial | Missing).

For each finding, cite the specific control/article violated \
(e.g., "No audit logging for PHI reads — missing §164.312(b)").
"""

_HIPAA_COMMENT = """\
## Compliance Analysis: HIPAA

Write PR review comments focused on HIPAA compliance for Protected \
Health Information.

Apply this health data review framework:

1. **§164.312(a)(1) — Access Control:** Comment on any code that accesses \
PHI. Verify role-based access checks. Block the PR if any endpoint \
exposes PHI without authentication and authorization.
2. **§164.312(e)(1) — Encryption:** Comment on PHI transmission and \
storage. Require AES-256 at rest and TLS 1.2+ in transit. Flag any \
unencrypted PHI as blocking.
3. **§164.312(b) — Audit Trail:** Comment on PHI operations that lack \
audit logging. Require log entries with: who accessed, what PHI, when, \
from where, and the outcome (success/failure).
4. **§164.312(c)(1) — Data Integrity:** Comment on PHI modification \
operations. Require validation, transactional safety, and integrity \
checks. Flag race conditions in concurrent PHI updates.
5. **§164.530(c) — Minimum Necessary:** Comment on code that accesses \
more PHI than necessary for the operation. Require field-level access \
control and data minimization.
6. **§164.314(a) — Business Associates:** Comment on any code that sends \
PHI to third-party services. Require documentation of the BAA and \
verification that data sharing is within scope.

Format each comment as:
**[HIPAA {Section}] {Severity}:** {Description} → {Recommended Fix}

For each finding, cite the specific control/article violated \
(e.g., "[HIPAA §164.312(b)] HIGH: PHI read without audit log entry").
"""


# ===================================================================
# ISO 27001 — Information Security Management System
# ===================================================================

_ISO27001_BUG = """\
## Compliance Analysis: ISO 27001

Analyze the code for bugs that could violate ISO 27001 Annex A controls.

Focus on these specific controls:

1. **A.8.2 — Information Classification:** Look for bugs where sensitive \
data is misclassified or handled without regard to its classification \
level. Check for missing classification labels, data handled above its \
clearance level, or classification downgrades without authorization.
2. **A.9.4 — System Access Control:** Identify bugs in access control \
mechanisms — broken authentication, missing session timeouts, privilege \
escalation, or access checks that can be bypassed via race conditions \
or parameter manipulation.
3. **A.10.1 — Cryptographic Controls:** Find bugs in cryptographic \
implementations — use of deprecated algorithms, improper key management, \
missing initialization vectors, predictable random number generation, \
or timing side-channels.
4. **A.12.4 — Logging and Monitoring:** Detect bugs that could disrupt \
logging — exception handlers that suppress log entries, log injection \
vulnerabilities, or race conditions in log writing.
5. **A.14.2 — Secure Development:** Identify coding defects that violate \
secure development policies — unchecked return values, use-after-free, \
integer overflows, or unsafe type casts.
6. **A.18.1 — Legal Compliance:** Find bugs that could cause violations \
of applicable legal, statutory, or contractual requirements — improper \
data retention, missing consent checks, or unauthorized data sharing.

Rate each bug by ISO 27001 risk level: **High** (control failure), \
**Medium** (control weakness), **Low** (improvement opportunity).

For each finding, cite the specific control/article violated \
(e.g., "Broken session timeout — violates A.9.4.2").
"""

_ISO27001_DESIGN = """\
## Compliance Analysis: ISO 27001

Evaluate the code's design against ISO 27001 Annex A controls and \
information security management principles.

Assess the architecture against these controls:

1. **A.8.1 — Asset Management:** Does the design maintain an inventory of \
information assets? Are data stores, services, and APIs catalogued with \
their classification and ownership?
2. **A.9.1 — Access Control Policy:** Does the architecture implement a \
centralized access control policy? Is there a clear pattern for \
authentication, authorization, and access revocation?
3. **A.10.1 — Cryptography Architecture:** Does the design include a \
cryptographic key management strategy? Are encryption algorithms selected \
per data classification? Is there a key rotation mechanism?
4. **A.12.1 — Operational Security:** Does the architecture enforce \
separation of development, test, and production environments? Are \
operational procedures documented and automated?
5. **A.14.1 — Secure Systems Architecture:** Does the design incorporate \
security requirements analysis? Are threat models maintained? Is there \
a pattern for security testing (SAST, DAST, penetration testing)?
6. **A.17.1 — Business Continuity:** Does the architecture support \
continuity requirements — redundancy, failover, backup, and recovery? \
Are RPO and RTO targets reflected in the design?

For each design gap, recommend a specific improvement aligned with the \
ISO 27001 control.

For each finding, cite the specific control/article violated \
(e.g., "No key rotation mechanism — violates A.10.1.2").
"""

_ISO27001_FLOW = """\
## Compliance Analysis: ISO 27001

Trace information flows through the code for ISO 27001 compliance.

Map these flow dimensions:

1. **A.8.2 — Classification Flow:** Trace how data classification labels \
are applied at ingestion and maintained as data flows through the system. \
Identify points where classification is lost, downgraded, or ignored.
2. **A.9.4 — Access Control Flow:** Map every decision point where access \
to information assets is granted or denied. Verify that the access control \
policy is consistently enforced across all paths.
3. **A.13.1 — Network Security Flow:** Trace data across network \
boundaries. Identify all ingress and egress points. Verify that data \
crossing trust boundaries is authenticated, authorized, and encrypted.
4. **A.12.4 — Audit Event Flow:** Trace how security events are generated, \
collected, and stored. Verify that the audit trail covers all access to \
classified information and cannot be tampered with.
5. **A.13.2 — Information Transfer Flow:** Map all data transfers between \
the system and external parties. Verify that transfer agreements, \
encryption, and integrity checks are in place.
6. **A.14.2 — Change Management Flow:** Trace how code and configuration \
changes flow from development to production. Verify that changes are \
reviewed, tested, and approved before deployment.

Produce an information flow map: Source → Classification → Processing → \
Transfer → Storage → ISO 27001 Control.

For each finding, cite the specific control/article violated \
(e.g., "Data crosses trust boundary without encryption — violates A.13.1.1").
"""

_ISO27001_STATIC = """\
## Compliance Analysis: ISO 27001

Perform static analysis to detect ISO 27001 control violations in the code.

Scan for these violation patterns:

1. **A.9.4.3 — Password Management:** Detect hardcoded passwords, default \
credentials, password storage in plaintext, and weak password validation \
(no minimum length, no complexity requirements).
2. **A.10.1.1 — Cryptographic Control Violations:** Flag use of deprecated \
algorithms (MD5, SHA-1 for security, DES, 3DES, RC4), hardcoded encryption \
keys, missing IVs, and ECB mode usage.
3. **A.12.4.1 — Event Logging Gaps:** Identify security-relevant operations \
that do not generate log events — login attempts, access denials, privilege \
changes, data modifications, and system errors.
4. **A.14.2.5 — Secure Coding Violations:** Detect OWASP Top 10 \
vulnerabilities: injection, broken authentication, sensitive data exposure, \
XXE, broken access control, security misconfiguration, XSS, insecure \
deserialization, vulnerable components, and insufficient logging.
5. **A.8.2.3 — Asset Handling:** Find sensitive data (credentials, PII, \
classified information) stored without appropriate protection — unencrypted \
files, world-readable permissions, or insecure temporary storage.
6. **A.12.6.1 — Vulnerability Management:** Detect use of known-vulnerable \
library versions, missing security patches, or dependencies with published \
CVEs.

Severity: Hardcoded secrets = Critical, deprecated crypto = High, missing \
logging = High, OWASP Top 10 = High, vulnerable deps = Medium.

For each finding, cite the specific control/article violated \
(e.g., "MD5 used for password hashing — violates A.10.1.1").
"""

_ISO27001_REQ = """\
## Compliance Analysis: ISO 27001

Extract information security requirements from the code, mapped to \
ISO 27001 Annex A controls.

For each requirement discovered:

1. **A.5 — Information Security Policies:** Does the code implement or \
enforce any information security policies? Map to A.5.1.1 (policy \
definition) and A.5.1.2 (policy review).
2. **A.9 — Access Control Requirements:** What access control mechanisms \
are implemented? Map to A.9.1 (policy), A.9.2 (user access management), \
A.9.3 (user responsibilities), A.9.4 (system access control).
3. **A.10 — Cryptography Requirements:** What cryptographic controls are \
implemented? Map to A.10.1.1 (cryptographic policy) and A.10.1.2 (key \
management).
4. **A.12 — Operations Security Requirements:** What operational security \
controls are present? Map to A.12.1 (procedures), A.12.2 (malware), \
A.12.3 (backup), A.12.4 (logging), A.12.6 (vulnerability management).
5. **A.14 — Development Security Requirements:** What secure development \
practices are enforced? Map to A.14.1 (security requirements), A.14.2 \
(development process), A.14.3 (test data).
6. **Gap Analysis:** For each Annex A control domain, list controls that \
should be present based on the information processed but are missing.

Output a Statement of Applicability matrix: Control → Applicability → \
Status (Implemented | Partial | Missing | Excluded with justification).

For each finding, cite the specific control/article violated \
(e.g., "No key management policy — missing A.10.1.2").
"""

_ISO27001_COMMENT = """\
## Compliance Analysis: ISO 27001

Write PR review comments focused on ISO 27001 Annex A control compliance.

Apply this information security review framework:

1. **A.9.4 — Access Control:** Comment on any code that handles \
authentication or authorization. Verify that access controls follow the \
principle of least privilege. Block PRs that bypass access checks.
2. **A.10.1 — Cryptography:** Comment on cryptographic implementations. \
Require approved algorithms (AES-256, SHA-256+, RSA-2048+), proper key \
management, and no hardcoded keys.
3. **A.12.4 — Logging:** Comment on security-relevant operations that \
lack structured logging. Require log entries for authentication events, \
authorization decisions, data access, and configuration changes.
4. **A.14.2 — Secure Development:** Comment on common coding flaws — \
injection, XSS, CSRF, insecure deserialization. Require input validation, \
output encoding, and parameterized queries.
5. **A.8.2 — Information Handling:** Comment on code that handles \
classified or sensitive data. Verify appropriate protection per the data's \
classification level.
6. **A.12.6 — Vulnerability Management:** Comment on dependency changes. \
Verify that new or updated libraries are free of known vulnerabilities.

Format each comment as:
**[ISO 27001 {Control}] {Severity}:** {Description} → {Recommended Fix}

For each finding, cite the specific control/article violated \
(e.g., "[ISO 27001 A.10.1.1] HIGH: Hardcoded AES key in config.py").
"""


# ===================================================================
# Generic Compliance Audit — Framework-Agnostic
# ===================================================================

_GENERIC_BUG = """\
## Compliance Analysis: Generic Audit

Analyze the code for bugs that could constitute compliance violations \
under any regulatory framework.

Perform a framework-agnostic analysis using these universal compliance \
dimensions:

1. **Access Control Defects:** Find bugs in authentication, authorization, \
session management, and privilege assignment. Any bug that allows \
unauthorized access to protected resources is a compliance concern \
regardless of the specific framework.
2. **Data Protection Defects:** Identify bugs where sensitive data \
(PII, financial data, health data, secrets) is exposed, leaked, or \
inadequately protected — in logs, error messages, temporary files, or \
unencrypted storage.
3. **Audit Trail Defects:** Detect bugs that prevent, corrupt, or allow \
tampering with audit logs. Every compliance framework requires an audit \
trail; bugs here are universally problematic.
4. **Data Lifecycle Defects:** Find bugs in data creation, processing, \
retention, and deletion logic. Incomplete deletions, unbounded retention, \
and missing lifecycle policies are common compliance gaps.
5. **Third-Party Integration Defects:** Identify bugs in how data is shared \
with external services — missing validation, unencrypted transfers, or \
unauthorized data sharing.
6. **Incident Detection Defects:** Look for bugs that could delay breach \
detection — swallowed exceptions, missing alerts, or broken monitoring \
in security-critical paths.

For each bug found, indicate which compliance frameworks it could violate \
(e.g., "This could violate SOC 2 CC6.1, GDPR Article 32, HIPAA §164.312(a)(1), \
PCI-DSS Req 7.1, and ISO 27001 A.9.4"). If the user has specified a target \
framework, map findings to that framework's specific controls.

For each finding, cite the specific control/article violated \
or the universal compliance principle at risk.
"""

_GENERIC_DESIGN = """\
## Compliance Analysis: Generic Audit

Evaluate the code's design for compliance readiness across any regulatory \
framework.

Assess the architecture using these universal compliance design principles:

1. **Defense in Depth:** Does the architecture implement multiple layers of \
security controls? Evaluate perimeter, network, application, and data \
layer protections. A compliant design never relies on a single control.
2. **Least Privilege:** Does the design enforce minimum necessary access at \
every layer? Evaluate service accounts, API permissions, database roles, \
and user access patterns.
3. **Separation of Duties:** Does the architecture prevent any single user \
or process from performing conflicting actions — e.g., creating and \
approving, writing and auditing?
4. **Privacy by Design:** Does the architecture minimize data collection, \
enforce purpose limitation, and support data subject rights (access, \
correction, deletion, portability)?
5. **Auditability by Design:** Does the architecture produce comprehensive \
audit trails? Can every action on sensitive data be traced to a specific \
actor, time, and justification?
6. **Resilience by Design:** Does the architecture support business \
continuity — backup, recovery, failover, and incident response?

For each design principle, rate the current architecture: **Strong**, \
**Adequate**, **Weak**, or **Missing**. If the user has specified a target \
compliance framework, map each principle to that framework's controls.

For each finding, cite the specific control/article violated \
or the universal compliance principle at risk.
"""

_GENERIC_FLOW = """\
## Compliance Analysis: Generic Audit

Trace data flows through the code for compliance analysis under any \
regulatory framework.

Map these universal compliance flow dimensions:

1. **Sensitive Data Ingress:** Trace where sensitive data (PII, financial, \
health, credentials) enters the system. For each entry point, document: \
what data, from whom, under what authorization, and with what disclosures.
2. **Processing Flow:** Follow sensitive data through every processing step. \
At each step, document: what operation, by which component, under what \
authority, and whether the processing is proportionate to its purpose.
3. **Storage Flow:** Map where sensitive data comes to rest — databases, \
caches, files, queues, third-party stores. For each store, document: \
encryption status, access controls, retention policy, and backup coverage.
4. **Sharing and Transfer Flow:** Trace sensitive data leaving the system \
boundary. For each transfer: recipient, legal/contractual basis, encryption \
in transit, and data minimization (is only necessary data shared?).
5. **Deletion and Retention Flow:** Trace how data deletion requests \
propagate through the system. Verify that deletion reaches all stores, \
including derived data, caches, and third-party copies.
6. **Audit Trail Flow:** Trace how compliance-relevant events are captured, \
transmitted, stored, and protected from tampering.

Produce a comprehensive data flow map. If the user has specified a target \
compliance framework, annotate each flow segment with the applicable \
controls from that framework.

For each finding, cite the specific control/article violated \
or the universal compliance principle at risk.
"""

_GENERIC_STATIC = """\
## Compliance Analysis: Generic Audit

Perform static analysis for compliance violations applicable to any \
regulatory framework.

Scan for these universal compliance violation patterns:

1. **Secrets in Source:** Detect hardcoded passwords, API keys, tokens, \
private keys, and connection strings in source code, configuration files, \
and test fixtures. This violates virtually every compliance framework.
2. **Sensitive Data Exposure:** Find PII, financial data, health data, \
or other sensitive information in logs, error messages, comments, or \
unprotected storage. Scan for patterns: email addresses, phone numbers, \
SSNs, credit card numbers, medical record numbers.
3. **Weak Cryptography:** Flag deprecated algorithms (MD5, SHA-1 for \
security, DES, 3DES, RC4), hardcoded keys, missing IVs, ECB mode, and \
disabled certificate validation.
4. **Missing Access Controls:** Identify endpoints, functions, or data \
operations that lack authentication or authorization checks. Flag \
admin functionality accessible without elevated privileges.
5. **Missing Audit Logging:** Detect state-changing operations, \
authentication events, and data access operations that do not generate \
audit log entries.
6. **Vulnerable Dependencies:** Identify use of libraries with known \
CVEs, outdated dependencies, and packages that have reached end-of-life.

For each finding, list ALL compliance frameworks it could violate. If the \
user has specified a target framework, prioritize that framework's controls.

Severity: Secrets in source = Critical, sensitive data exposure = High, \
weak crypto = High, missing access controls = High, missing audit = Medium.

For each finding, cite the specific control/article violated \
or the universal compliance principle at risk.
"""

_GENERIC_REQ = """\
## Compliance Analysis: Generic Audit

Extract compliance requirements from the code, suitable for mapping to \
any regulatory framework.

Discover requirements across these universal compliance domains:

1. **Access Control Requirements:** What authentication, authorization, \
session management, and privilege management requirements does the code \
implement? Document each mechanism and its strength.
2. **Data Protection Requirements:** What encryption, hashing, masking, \
tokenization, and anonymization requirements are present? Map each to \
the data classification it protects.
3. **Audit and Monitoring Requirements:** What logging, monitoring, \
alerting, and incident detection requirements are implemented? Document \
the completeness of the audit trail.
4. **Data Lifecycle Requirements:** What data collection, retention, \
archival, and deletion requirements are enforced? Identify data classes \
and their lifecycle policies.
5. **Third-Party and Integration Requirements:** What controls govern \
data sharing with external services? Document contractual, technical, \
and operational safeguards.
6. **Gap Analysis:** For each domain, identify requirements that SHOULD \
exist based on the sensitivity of data and operations but are NOT present.

Output a compliance requirements matrix: Requirement → Domain → Status \
(Implemented | Partial | Missing). If the user has specified a target \
framework, include a column mapping each requirement to that framework's \
specific controls.

For each finding, cite the specific control/article violated \
or the universal compliance principle at risk.
"""

_GENERIC_COMMENT = """\
## Compliance Analysis: Generic Audit

Write PR review comments applying universal compliance review principles.

Use this framework-agnostic review checklist:

1. **Authentication & Authorization:** Comment on any code that handles \
identity or access control. Verify proper authentication, authorization, \
and session management. Block PRs that introduce access control bypasses.
2. **Data Protection:** Comment on handling of sensitive data. Require \
encryption at rest and in transit, data masking in logs, and secure \
deletion. Flag any exposure of sensitive data as blocking.
3. **Audit Logging:** Comment on state-changing or security-relevant \
operations that lack audit log entries. Require structured logging with \
actor, action, resource, timestamp, and result.
4. **Input Validation:** Comment on new endpoints or data inputs that \
lack validation, sanitization, or type checking. Require defense against \
injection, XSS, and other input-based attacks.
5. **Dependency Security:** Comment on new or updated dependencies. \
Require that they are free of known CVEs and are actively maintained.
6. **Compliance Documentation:** Comment where code changes affect \
compliance-relevant behavior. Require inline documentation linking the \
code to the specific compliance control it implements.

Format each comment as:
**[Compliance] {Severity}:** {Description} → {Recommended Fix}
(Applicable frameworks: {list frameworks this could affect})

For each finding, cite the specific control/article violated \
or the universal compliance principle at risk.
"""


# ===================================================================
# Collected template list — all 36 templates
# ===================================================================

COMPLIANCE_TEMPLATES: list[PromptTemplate] = [
    # --- SOC 2 (6) ---
    _t("Compliance: SOC 2", "bug_analysis",
       "Find bugs violating SOC 2 Trust Service Criteria", _SOC2_BUG),
    _t("Compliance: SOC 2", "code_design",
       "Evaluate architecture against SOC 2 controls", _SOC2_DESIGN),
    _t("Compliance: SOC 2", "code_flow",
       "Trace data flows for SOC 2 compliance", _SOC2_FLOW),
    _t("Compliance: SOC 2", "static_analysis",
       "Static scan for SOC 2 control violations", _SOC2_STATIC),
    _t("Compliance: SOC 2", "requirement",
       "Extract SOC 2 compliance requirements from code", _SOC2_REQ),
    _t("Compliance: SOC 2", "comment_generator",
       "PR review comments for SOC 2 compliance", _SOC2_COMMENT),

    # --- GDPR (6) ---
    _t("Compliance: GDPR", "bug_analysis",
       "Find bugs that could cause GDPR violations", _GDPR_BUG),
    _t("Compliance: GDPR", "code_design",
       "Evaluate design for GDPR data protection", _GDPR_DESIGN),
    _t("Compliance: GDPR", "code_flow",
       "Trace personal data flows for GDPR compliance", _GDPR_FLOW),
    _t("Compliance: GDPR", "static_analysis",
       "Static scan for GDPR compliance violations", _GDPR_STATIC),
    _t("Compliance: GDPR", "requirement",
       "Extract GDPR requirements from code", _GDPR_REQ),
    _t("Compliance: GDPR", "comment_generator",
       "PR review comments for GDPR compliance", _GDPR_COMMENT),

    # --- PCI-DSS (6) ---
    _t("Compliance: PCI-DSS", "bug_analysis",
       "Find bugs violating PCI-DSS requirements", _PCIDSS_BUG),
    _t("Compliance: PCI-DSS", "code_design",
       "Evaluate architecture for PCI-DSS compliance", _PCIDSS_DESIGN),
    _t("Compliance: PCI-DSS", "code_flow",
       "Trace cardholder data flows for PCI-DSS", _PCIDSS_FLOW),
    _t("Compliance: PCI-DSS", "static_analysis",
       "Static scan for PCI-DSS violations", _PCIDSS_STATIC),
    _t("Compliance: PCI-DSS", "requirement",
       "Extract PCI-DSS requirements from code", _PCIDSS_REQ),
    _t("Compliance: PCI-DSS", "comment_generator",
       "PR review comments for PCI-DSS compliance", _PCIDSS_COMMENT),

    # --- HIPAA (6) ---
    _t("Compliance: HIPAA", "bug_analysis",
       "Find bugs that could expose PHI (HIPAA)", _HIPAA_BUG),
    _t("Compliance: HIPAA", "code_design",
       "Evaluate architecture for HIPAA compliance", _HIPAA_DESIGN),
    _t("Compliance: HIPAA", "code_flow",
       "Trace PHI flows for HIPAA compliance", _HIPAA_FLOW),
    _t("Compliance: HIPAA", "static_analysis",
       "Static scan for HIPAA violations", _HIPAA_STATIC),
    _t("Compliance: HIPAA", "requirement",
       "Extract HIPAA compliance requirements from code", _HIPAA_REQ),
    _t("Compliance: HIPAA", "comment_generator",
       "PR review comments for HIPAA compliance", _HIPAA_COMMENT),

    # --- ISO 27001 (6) ---
    _t("Compliance: ISO 27001", "bug_analysis",
       "Find bugs violating ISO 27001 Annex A controls", _ISO27001_BUG),
    _t("Compliance: ISO 27001", "code_design",
       "Evaluate design against ISO 27001 controls", _ISO27001_DESIGN),
    _t("Compliance: ISO 27001", "code_flow",
       "Trace information flows for ISO 27001", _ISO27001_FLOW),
    _t("Compliance: ISO 27001", "static_analysis",
       "Static scan for ISO 27001 control violations", _ISO27001_STATIC),
    _t("Compliance: ISO 27001", "requirement",
       "Extract ISO 27001 requirements from code", _ISO27001_REQ),
    _t("Compliance: ISO 27001", "comment_generator",
       "PR review comments for ISO 27001 compliance", _ISO27001_COMMENT),

    # --- Generic Audit (6) ---
    _t("Compliance: Generic Audit", "bug_analysis",
       "Find compliance-relevant bugs (any framework)", _GENERIC_BUG),
    _t("Compliance: Generic Audit", "code_design",
       "Evaluate design for compliance readiness", _GENERIC_DESIGN),
    _t("Compliance: Generic Audit", "code_flow",
       "Trace sensitive data flows for compliance", _GENERIC_FLOW),
    _t("Compliance: Generic Audit", "static_analysis",
       "Static scan for universal compliance violations", _GENERIC_STATIC),
    _t("Compliance: Generic Audit", "requirement",
       "Extract compliance requirements (any framework)", _GENERIC_REQ),
    _t("Compliance: Generic Audit", "comment_generator",
       "PR review comments for general compliance", _GENERIC_COMMENT),
]
