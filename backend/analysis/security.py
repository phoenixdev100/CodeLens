"""Security Analyzer: comprehensive deterministic security checks.

Performs detailed pattern-based security scanning across multiple categories:

1. Secret Scanning — detects leaked credentials:
   - AWS access keys & secret keys
   - GitHub tokens (PAT, fine-grained, OAuth)
   - Google API keys & service account keys
   - JWT secrets & tokens
   - Private keys (PEM blocks)
   - Database connection strings
   - Slack tokens
   - Stripe keys (publishable & secret)
   - Generic high-entropy secrets
   - Hardcoded password/credential assignments

2. Injection — detects injection vulnerabilities:
   - SQL string concatenation
   - NoSQL injection patterns
   - ORM unsafe usage (raw queries)
   - Template injection

3. XSS & CSRF — detects cross-site scripting & CSRF issues:
   - innerHTML / outerHTML assignment
   - dangerouslySetInnerHTML
   - document.write
   - Missing CSRF token patterns
   - Unsafe redirects (window.location from user input)

4. Path Traversal & SSRF — detects file/network access issues:
   - Path traversal patterns (../)
   - Open redirect patterns
   - SSRF patterns (internal URL fetching)
   - File system access with user input

5. Command Injection — detects OS command execution:
   - eval() / Function() usage
   - exec / execSync / spawn with string args
   - child_process usage
   - Shell injection vectors

6. Sensitive File Change — flags security-critical file modifications
7. Dependency Audit — analyzes package.json changes for supply-chain risk
"""
from __future__ import annotations

import re
from typing import List, Tuple

from models.analysis import Finding, SecurityCheckResult, SecuritySignal, Severity
from models.context import AnalysisContext, NormalizedFile


# ============================================================================
# SECRET SCANNING PATTERNS
# ============================================================================

# Specific cloud/service provider key patterns
_SECRET_PATTERNS: List[Tuple[str, re.Pattern, str, Severity]] = [
    (
        "AWS Access Key ID",
        re.compile(r"\b(AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA|ASCA)[A-Z0-9]{16}\b"),
        "AWS access key ID detected. This can grant access to AWS resources.",
        Severity.CRITICAL,
    ),
    (
        "AWS Secret Access Key",
        re.compile(r"""(?i)aws[_-]?(?:secret[_-]?access[_-]?key|secret[_-]?key)\s*[:=]\s*['"]([A-Za-z0-9/+=]{40})['"]"""),
        "AWS secret access key detected. This combined with an access key ID grants full AWS access.",
        Severity.CRITICAL,
    ),
    (
        "GitHub Token (PAT)",
        re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
        "GitHub Personal Access Token detected. This grants access to GitHub repositories.",
        Severity.CRITICAL,
    ),
    (
        "GitHub Fine-grained Token",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"),
        "GitHub fine-grained personal access token detected.",
        Severity.CRITICAL,
    ),
    (
        "GitHub OAuth Token",
        re.compile(r"\bgho_[A-Za-z0-9]{36}\b"),
        "GitHub OAuth token detected.",
        Severity.CRITICAL,
    ),
    (
        "GitHub App Token",
        re.compile(r"\b(ghu|ghs|ghr)_[A-Za-z0-9]{36}\b"),
        "GitHub App token detected.",
        Severity.CRITICAL,
    ),
    (
        "Google API Key",
        re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
        "Google API key detected. This can grant access to Google Cloud services.",
        Severity.HIGH,
    ),
    (
        "Google OAuth Access Token",
        re.compile(r"\bya29\.[0-9A-Za-z\-_]+"),
        "Google OAuth access token detected.",
        Severity.HIGH,
    ),
    (
        "JWT Token",
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "JWT token detected. This may contain sensitive claims or be a leaked secret.",
        Severity.HIGH,
    ),
    (
        "Slack Token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+"),
        "Slack token detected. This grants access to Slack workspaces.",
        Severity.HIGH,
    ),
    (
        "Stripe Publishable Key",
        re.compile(r"\bpk_(?:test_|live_)[0-9a-zA-Z]{24,}\b"),
        "Stripe publishable key detected.",
        Severity.MEDIUM,
    ),
    (
        "Stripe Secret Key",
        re.compile(r"\bsk_(?:test_|live_)[0-9a-zA-Z]{24,}\b"),
        "Stripe secret key detected. This can process payments and access financial data.",
        Severity.CRITICAL,
    ),
    (
        "Twilio API Key",
        re.compile(r"\bSK[0-9a-fA-F]{32}\b"),
        "Twilio API key detected.",
        Severity.HIGH,
    ),
    (
        "PEM Private Key Block",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
        "Private key (PEM) block detected in source. This is a critical secret leak.",
        Severity.CRITICAL,
    ),
    (
        "Database Connection String",
        re.compile(r"""(?i)(?:mongodb|postgres(?:ql)?|mysql|redis|amqp)://[^\s'"]*:[^\s'"]+@[^\s'"]+"""),
        "Database connection string with credentials detected.",
        Severity.CRITICAL,
    ),
]

# Hardcoded credential assignments: password = "..." , API_KEY = '...'
_CRED_ASSIGN_RE = re.compile(
    r"""(?i)\b(password|passwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|private[_-]?key|client[_-]?secret|db[_-]?password|database[_-]?url)\b\s*[:=]\s*['"]([^'"]{6,})['"]"""
)

# High-entropy-looking long strings (potential secrets)
_HIGH_ENTROPY_RE = re.compile(
    r"""['"]([A-Za-z0-9+/=_-]{40,})['"]"""
)


# ============================================================================
# INJECTION PATTERNS
# ============================================================================

_INJECTION_PATTERNS: List[Tuple[str, re.Pattern, str, Severity]] = [
    (
        "SQL String Concatenation",
        re.compile(r"""['"]\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b.*['"]\s*\+""", re.IGNORECASE),
        "SQL query built with string concatenation. This is vulnerable to SQL injection.",
        Severity.HIGH,
    ),
    (
        "SQL F-string Interpolation",
        re.compile(r"""f['"]\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b.*\{.*\}.*['"]""", re.IGNORECASE),
        "SQL query built with f-string interpolation. User input is directly embedded in the query, allowing SQL injection.",
        Severity.HIGH,
    ),
    (
        "SQL Format String Interpolation",
        re.compile(r"""['"]\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b.*['"]\s*%.*""", re.IGNORECASE),
        "SQL query built with % string formatting. This can allow SQL injection if user input is interpolated.",
        Severity.HIGH,
    ),
    (
        "SQL .format() Interpolation",
        re.compile(r"""['"]\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b.*['"]\s*\.format\s*\(""", re.IGNORECASE),
        "SQL query built with .format() method. This can allow SQL injection if user input is interpolated.",
        Severity.HIGH,
    ),
    (
        "SQL Raw Query",
        re.compile(r"""\.raw\s*\(\s*['"](?:SELECT|INSERT|UPDATE|DELETE|DROP)\b""", re.IGNORECASE),
        "Raw SQL query detected. Verify it uses parameterized inputs.",
        Severity.MEDIUM,
    ),
    (
        "NoSQL Injection (MongoDB)",
        re.compile(r"""\$where\s*[:=]\s*['"]"""),
        "MongoDB $where operator with string argument detected. This can allow NoSQL injection.",
        Severity.HIGH,
    ),
    (
        "NoSQL Injection (eval)",
        re.compile(r"""\$function\s*[:=]"""),
        "MongoDB $function operator detected. This can execute arbitrary JavaScript.",
        Severity.HIGH,
    ),
    (
        "ORM Unsafe Query",
        re.compile(r"""\.query\s*\(\s*['"](?:SELECT|INSERT|UPDATE|DELETE)\b""", re.IGNORECASE),
        "ORM raw query with SQL string detected. Verify parameterization.",
        Severity.MEDIUM,
    ),
    (
        "Cursor.execute with f-string",
        re.compile(r"""\.execute\s*\(\s*f['"](?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b""", re.IGNORECASE),
        "cursor.execute() called with an f-string SQL query. This is vulnerable to SQL injection.",
        Severity.HIGH,
    ),
    (
        "Cursor.execute with format",
        re.compile(r"""\.execute\s*\(\s*['"](?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b.*['"]\s*\.format\s*\(""", re.IGNORECASE),
        "cursor.execute() called with .format() SQL query. This is vulnerable to SQL injection.",
        Severity.HIGH,
    ),
    (
        "Template Injection",
        re.compile(r"""(?:render[_-]?template|render[_-]?string)\s*\(\s*['"].*\$\{.*['"]"""),
        "Template rendering with string interpolation detected. This can allow template injection.",
        Severity.MEDIUM,
    ),
]


# ============================================================================
# XSS & CSRF PATTERNS
# ============================================================================

_XSS_CSRF_PATTERNS: List[Tuple[str, re.Pattern, str, Severity]] = [
    (
        "innerHTML Assignment (XSS)",
        re.compile(r"\.innerHTML\s*="),
        "innerHTML assignment detected. This can introduce XSS if content is user-controlled.",
        Severity.MEDIUM,
    ),
    (
        "outerHTML Assignment (XSS)",
        re.compile(r"\.outerHTML\s*="),
        "outerHTML assignment detected. This can introduce XSS if content is user-controlled.",
        Severity.MEDIUM,
    ),
    (
        "dangerouslySetInnerHTML (React XSS)",
        re.compile(r"\bdangerouslySetInnerHTML\b"),
        "dangerouslySetInnerHTML detected in React. Verify the content is sanitized.",
        Severity.MEDIUM,
    ),
    (
        "document.write (XSS)",
        re.compile(r"\bdocument\.write\s*\("),
        "document.write() detected. This can introduce XSS and is considered bad practice.",
        Severity.MEDIUM,
    ),
    (
        "eval() (Code Injection)",
        re.compile(r"\beval\s*\("),
        "eval() usage detected. This can execute arbitrary code and is a security risk.",
        Severity.HIGH,
    ),
    (
        "new Function() (Code Injection)",
        re.compile(r"\bnew\s+Function\s*\("),
        "new Function() detected. This is equivalent to eval() and can execute arbitrary code.",
        Severity.HIGH,
    ),
    (
        "Unsafe Redirect",
        re.compile(r"""(?:window\.location|location\.href)\s*=\s*(?:req|request|params|query|input|data)\b"""),
        "Redirect using user input detected. This can allow open redirect attacks.",
        Severity.MEDIUM,
    ),
    (
        "Missing CSRF (Express)",
        re.compile(r"""\b(?:app|router)\.(?:post|put|delete|patch)\s*\("""),
        "State-changing route detected. Verify CSRF protection middleware is applied.",
        Severity.LOW,
    ),
]


# ============================================================================
# PATH TRAVERSAL & SSRF PATTERNS
# ============================================================================

_PATH_SSRF_PATTERNS: List[Tuple[str, re.Pattern, str, Severity]] = [
    (
        "Path Traversal Pattern",
        re.compile(r"""['"]\.\./\.\./"""),
        "Path traversal pattern (../) detected. This can access files outside intended directory.",
        Severity.HIGH,
    ),
    (
        "File Read with User Input",
        re.compile(r"""\b(?:readFile|readFileSync|read|open|createReadStream)\s*\(\s*(?:req|request|params|query|input|data|body)\b"""),
        "File read operation using user input detected. This can allow path traversal.",
        Severity.HIGH,
    ),
    (
        "File Write with User Input",
        re.compile(r"""\b(?:writeFile|writeFileSync|write|createWriteStream|appendFile)\s*\(\s*(?:req|request|params|query|input|data|body)\b"""),
        "File write operation using user input detected. This can allow arbitrary file writes.",
        Severity.HIGH,
    ),
    (
        "SSRF — HTTP Request with User Input",
        re.compile(r"""\b(?:fetch|axios|request|http\.get|https\.get|urllib)\s*\(\s*(?:req|request|params|query|input|data|body|url)\b"""),
        "HTTP request using user input detected. This can allow SSRF attacks.",
        Severity.HIGH,
    ),
    (
        "Open Redirect",
        re.compile(r"""(?:redirect|res\.redirect)\s*\(\s*(?:req|request|params|query|input|data|body)\b"""),
        "Redirect using user input detected. This can allow open redirect attacks.",
        Severity.MEDIUM,
    ),
]


# ============================================================================
# COMMAND INJECTION PATTERNS
# ============================================================================

_CMD_INJECTION_PATTERNS: List[Tuple[str, re.Pattern, str, Severity]] = [
    (
        "exec() with string argument",
        re.compile(r"""\bexec\s*\(\s*['"]"""),
        "exec() with string argument detected. This can allow command injection.",
        Severity.HIGH,
    ),
    (
        "execSync() with string argument",
        re.compile(r"""\bexecSync\s*\(\s*['"]"""),
        "execSync() with string argument detected. This can allow command injection.",
        Severity.HIGH,
    ),
    (
        "os.system() usage",
        re.compile(r"""\bos\.system\s*\("""),
        "os.system() call detected. If user input flows into the argument, this allows command injection. Use subprocess with shell=False instead.",
        Severity.HIGH,
    ),
    (
        "os.popen() usage",
        re.compile(r"""\bos\.popen\s*\("""),
        "os.popen() call detected. This runs a shell command and is vulnerable to command injection if user input is involved.",
        Severity.HIGH,
    ),
    (
        "subprocess with shell=True",
        re.compile(r"""\bsubprocess\.(?:call|run|Popen|check_output)\s*\(.*shell\s*=\s*True"""),
        "subprocess called with shell=True. This allows shell injection if user input is in the command string.",
        Severity.HIGH,
    ),
    (
        "eval() usage",
        re.compile(r"""\beval\s*\("""),
        "eval() call detected. This can execute arbitrary code if user input is involved.",
        Severity.HIGH,
    ),
    (
        "child_process usage",
        re.compile(r"\bchild_process\b"),
        "child_process module usage detected. Verify no user input flows into commands.",
        Severity.MEDIUM,
    ),
    (
        "spawn() with string argument",
        re.compile(r"""\bspawn\s*\(\s*['"]"""),
        "spawn() with string argument detected. Verify the command is not user-controlled.",
        Severity.MEDIUM,
    ),
    (
        "Shell Injection (backticks/template)",
        re.compile(r"""`.*\$\{.*(?:req|request|params|query|input|body|user|username|password).*\}.*`"""),
        "Template literal with user input in shell context detected. This can allow shell injection.",
        Severity.HIGH,
    ),
    (
        "os.system with f-string",
        re.compile(r"""\bos\.system\s*\(\s*f['"]"""),
        "os.system() called with an f-string. User input is directly embedded in the shell command, allowing command injection.",
        Severity.CRITICAL,
    ),
]


# Files that are security-sensitive by location
_SENSITIVE_PATH_PATTERNS = [
    "auth", "login", "session", "token", "password", "permission",
    "rbac", "crypto", "secret", "security", "oauth", "jwt", "middleware",
]


class SecurityAnalyzer:
    """Produces comprehensive, evidence-backed security findings."""

    def analyze(self, ctx: AnalysisContext) -> SecuritySignal:
        all_findings: List[Finding] = []
        seen_ids: set[str] = set()
        checks: List[SecurityCheckResult] = []

        # Run each check category
        checks.append(self._check_secrets(ctx, all_findings, seen_ids))
        checks.append(self._check_injection(ctx, all_findings, seen_ids))
        checks.append(self._check_xss_csrf(ctx, all_findings, seen_ids))
        checks.append(self._check_path_traversal_ssrf(ctx, all_findings, seen_ids))
        checks.append(self._check_command_injection(ctx, all_findings, seen_ids))
        checks.append(self._check_sensitive_files(ctx, all_findings, seen_ids))
        checks.append(self._check_dependency_audit(ctx, all_findings, seen_ids))

        passed = sum(1 for c in checks if c.status == "pass")
        failed = sum(1 for c in checks if c.status == "fail")

        return SecuritySignal(
            findings=all_findings,
            checks=checks,
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
        )

    # --- Check 1: Secret Scanning ---
    def _check_secrets(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            content = f.content or ""
            added_text = self._added_text(f)
            scan_text = f"{content}\n{added_text}"

            # Specific provider key patterns
            for name, pattern, description, sev in _SECRET_PATTERNS:
                matches = pattern.findall(scan_text)
                if not matches:
                    continue
                fid = f"sec-secret-{f.filename}-{name}"
                if fid in seen:
                    continue
                seen.add(fid)
                # Extract a sample (first 20 chars) for evidence without exposing full secret
                sample = matches[0] if isinstance(matches[0], str) else str(matches[0])
                masked = sample[:8] + "..." if len(sample) > 8 else sample
                check_findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=sev,
                        title=f"{name} detected in {f.filename}",
                        file=f.filename,
                        what_changed=f"A {name.lower()} was found in the code.",
                        why_it_matters=description,
                        evidence=[
                            f"type={name}",
                            f"sample={masked}",
                            f"occurrences={len(matches)}",
                            "pattern: provider-specific secret key",
                        ],
                        confidence="high",
                    )
                )

            # Generic credential assignments
            for m in _CRED_ASSIGN_RE.finditer(scan_text):
                var, value = m.group(1), m.group(2)
                fid = f"sec-cred-{f.filename}-{var}"
                if fid in seen:
                    continue
                seen.add(fid)
                check_findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=Severity.HIGH,
                        title=f"Hardcoded {var.lower()} in {f.filename}",
                        file=f.filename,
                        what_changed=f"A {var.lower()} appears to be assigned a literal string value.",
                        why_it_matters=(
                            "Hardcoded secrets in source code are a serious security risk. "
                            "Move to environment variables or a secret manager."
                        ),
                        evidence=[
                            f"variable={var}",
                            f"value_length={len(value)}",
                            "pattern: credential assignment with string literal",
                        ],
                        confidence="medium",
                    )
                )

            # High-entropy strings (potential secrets)
            entropy_matches = _HIGH_ENTROPY_RE.findall(scan_text)
            if entropy_matches and not any("secret" in f.id for f in check_findings):
                fid = f"sec-entropy-{f.filename}"
                if fid not in seen:
                    seen.add(fid)
                    check_findings.append(
                        Finding(
                            id=fid,
                            category="security",
                            severity=Severity.LOW,
                            title=f"High-entropy string in {f.filename}",
                            file=f.filename,
                            what_changed=f"{len(entropy_matches)} high-entropy string(s) detected (40+ chars).",
                            why_it_matters=(
                                "Long high-entropy strings may be secrets or API keys. "
                                "Verify they are not sensitive credentials."
                            ),
                            evidence=[
                                f"count={len(entropy_matches)}",
                                "pattern: 40+ character alphanumeric string",
                            ],
                            confidence="low",
                        )
                    )

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="secret-scan",
            status="fail" if check_findings else "pass",
            summary=f"{len(check_findings)} secret(s) detected" if check_findings else "No secrets detected",
            findings=check_findings,
        )

    # --- Check 2: Injection ---
    def _check_injection(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            scan_text = f"{f.content or ''}\n{self._added_text(f)}"

            for name, pattern, description, sev in _INJECTION_PATTERNS:
                matches = pattern.findall(scan_text)
                if not matches:
                    continue
                fid = f"sec-injection-{f.filename}-{name}"
                if fid in seen:
                    continue
                seen.add(fid)
                check_findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=sev,
                        title=f"Injection risk: {name} in {f.filename}",
                        file=f.filename,
                        what_changed=f"Detected {name}.",
                        why_it_matters=description,
                        evidence=[
                            f"pattern: {name}",
                            f"occurrences: {len(matches)}",
                        ],
                        confidence="medium",
                    )
                )

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="injection",
            status="fail" if check_findings else "pass",
            summary=f"{len(check_findings)} injection risk(s) detected" if check_findings else "No injection risks detected",
            findings=check_findings,
        )

    # --- Check 3: XSS & CSRF ---
    def _check_xss_csrf(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            scan_text = f"{f.content or ''}\n{self._added_text(f)}"

            for name, pattern, description, sev in _XSS_CSRF_PATTERNS:
                matches = pattern.findall(scan_text)
                if not matches:
                    continue
                fid = f"sec-xss-{f.filename}-{name}"
                if fid in seen:
                    continue
                seen.add(fid)
                check_findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=sev,
                        title=f"XSS/CSRF risk: {name} in {f.filename}",
                        file=f.filename,
                        what_changed=f"Detected {name}.",
                        why_it_matters=description,
                        evidence=[
                            f"pattern: {name}",
                            f"occurrences: {len(matches)}",
                        ],
                        confidence="medium",
                    )
                )

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="xss-csrf",
            status="fail" if check_findings else "pass",
            summary=f"{len(check_findings)} XSS/CSRF risk(s) detected" if check_findings else "No XSS/CSRF risks detected",
            findings=check_findings,
        )

    # --- Check 4: Path Traversal & SSRF ---
    def _check_path_traversal_ssrf(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            scan_text = f"{f.content or ''}\n{self._added_text(f)}"

            for name, pattern, description, sev in _PATH_SSRF_PATTERNS:
                matches = pattern.findall(scan_text)
                if not matches:
                    continue
                fid = f"sec-patht-ssrf-{f.filename}-{name}"
                if fid in seen:
                    continue
                seen.add(fid)
                check_findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=sev,
                        title=f"Path/SSRF risk: {name} in {f.filename}",
                        file=f.filename,
                        what_changed=f"Detected {name}.",
                        why_it_matters=description,
                        evidence=[
                            f"pattern: {name}",
                            f"occurrences: {len(matches)}",
                        ],
                        confidence="medium",
                    )
                )

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="path-traversal-ssrf",
            status="fail" if check_findings else "pass",
            summary=f"{len(check_findings)} path/SSRF risk(s) detected" if check_findings else "No path traversal/SSRF risks detected",
            findings=check_findings,
        )

    # --- Check 5: Command Injection ---
    def _check_command_injection(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            scan_text = f"{f.content or ''}\n{self._added_text(f)}"

            for name, pattern, description, sev in _CMD_INJECTION_PATTERNS:
                matches = pattern.findall(scan_text)
                if not matches:
                    continue
                fid = f"sec-cmd-{f.filename}-{name}"
                if fid in seen:
                    continue
                seen.add(fid)
                check_findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=sev,
                        title=f"Command injection risk: {name} in {f.filename}",
                        file=f.filename,
                        what_changed=f"Detected {name}.",
                        why_it_matters=description,
                        evidence=[
                            f"pattern: {name}",
                            f"occurrences: {len(matches)}",
                        ],
                        confidence="medium",
                    )
                )

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="command-injection",
            status="fail" if check_findings else "pass",
            summary=f"{len(check_findings)} command injection risk(s) detected" if check_findings else "No command injection risks detected",
            findings=check_findings,
        )

    # --- Check 6: Sensitive File Change ---
    def _check_sensitive_files(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            norm = f.filename.replace("\\", "/").lower()
            for p in _SENSITIVE_PATH_PATTERNS:
                if p in norm:
                    fid = f"sec-sensitive-{f.filename}"
                    if fid in seen:
                        continue
                    seen.add(fid)
                    check_findings.append(
                        Finding(
                            id=fid,
                            category="security",
                            severity=Severity.HIGH,
                            title=f"Security-sensitive file changed: {f.filename}",
                            file=f.filename,
                            what_changed=f"File path contains '{p}', indicating a security-sensitive area.",
                            why_it_matters=(
                                "Changes to auth/session/token/crypto/security files can affect "
                                "the security posture. Review for correctness and absence of regressions."
                            ),
                            evidence=[f"path contains '{p}'"],
                            confidence="high",
                        )
                    )
                    break

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="sensitive-file",
            status="warn" if check_findings else "pass",
            summary=f"{len(check_findings)} sensitive file(s) changed" if check_findings else "No sensitive files changed",
            findings=check_findings,
        )

    # --- Check 7: Dependency Audit ---
    def _check_dependency_audit(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> SecurityCheckResult:
        check_findings: List[Finding] = []

        for f in ctx.normalized_files:
            if not f.filename.endswith("package.json"):
                continue
            added_text = self._added_text(f)
            dep_lines = [
                line.strip()
                for line in added_text.splitlines()
                if ('"' in line) and (":" in line) and not line.strip().startswith(("{", "}", "[", "]"))
            ]
            if not dep_lines:
                continue

            fid = f"sec-deps-{f.filename}"
            if fid in seen:
                continue
            seen.add(fid)

            # Check for suspicious patterns
            suspicious = []
            for line in dep_lines:
                # Unpinned versions (using * or latest)
                if "*" in line or "latest" in line:
                    suspicious.append(f"unpinned version: {line.strip()}")
                # GitHub URL dependencies (potential supply chain risk)
                if "github.com" in line or "git+" in line:
                    suspicious.append(f"git dependency: {line.strip()}")
                # Postinstall scripts (potential malware vector)
                if "postinstall" in line:
                    suspicious.append(f"postinstall script: {line.strip()}")

            sev = Severity.HIGH if suspicious else Severity.LOW
            check_findings.append(
                Finding(
                    id=fid,
                    category="security",
                    severity=sev,
                    title=f"Dependency changes in {f.filename}",
                    file=f.filename,
                    what_changed=f"{len(dep_lines)} dependency line(s) added/modified.",
                    why_it_matters=(
                        "New dependencies can introduce supply-chain risk. Verify packages are "
                        "trusted, versions are pinned, and no postinstall scripts execute arbitrary code."
                    ),
                    evidence=[f"added dependency lines: {len(dep_lines)}"] + dep_lines[:5] + suspicious[:3],
                    confidence="high",
                )
            )

        findings.extend(check_findings)
        return SecurityCheckResult(
            check_type="dependency",
            status="warn" if check_findings else "pass",
            summary=f"{len(check_findings)} dependency change(s) flagged" if check_findings else "No dependency changes",
            findings=check_findings,
        )

    def _added_text(self, f: NormalizedFile) -> str:
        """Extract added lines from the parsed patch as plain text."""
        if not f.patch:
            return ""
        lines: List[str] = []
        for hunk in f.patch.hunks:
            for line in hunk.lines:
                if line.startswith("+") and not line.startswith("+++"):
                    lines.append(line[1:])
        return "\n".join(lines)
