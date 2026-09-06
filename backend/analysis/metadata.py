"""PR Metadata Analyzer: checks PR description quality, breaking changes, migrations, and config.

Deterministic heuristics on PR metadata + file paths:
  - PR description quality (empty/too short)
  - Breaking change indicators (BREAKING CHANGE, !: in commit, etc.)
  - Database migration files
  - Configuration file changes
  - Environment file changes
  - CI/CD pipeline changes
  - Documentation changes
"""
from __future__ import annotations

import re
from typing import List

from models.analysis import Finding, Severity
from models.context import AnalysisContext, NormalizedFile


# Breaking change indicators in PR title/body
_BREAKING_RE = re.compile(
    r"""(?i)(breaking[_\s-]?change|!:\s|BREAKING\s*CHANGE|incompatible|migration\s+required)"""
)

# Migration file patterns
_MIGRATION_PATTERNS = [
    re.compile(r"\bmigrations?/.*\.(sql|py|js|ts)$", re.IGNORECASE),
    re.compile(r"\bmigrate[_-]", re.IGNORECASE),
    re.compile(r"\.sql$", re.IGNORECASE),
    re.compile(r"\bschema[_-]?", re.IGNORECASE),
]

# Config file patterns
_CONFIG_PATTERNS = [
    re.compile(r"\.env$", re.IGNORECASE),
    re.compile(r"\.env\.", re.IGNORECASE),
    re.compile(r"config\.(js|ts|json|yaml|yml|toml|ini)$", re.IGNORECASE),
    re.compile(r"\.rc$", re.IGNORECASE),
    re.compile(r"dockerfile", re.IGNORECASE),
    re.compile(r"docker-compose", re.IGNORECASE),
    re.compile(r"\.github/workflows/", re.IGNORECASE),
]

# CI/CD patterns
_CICD_PATTERNS = [
    re.compile(r"\.github/workflows/", re.IGNORECASE),
    re.compile(r"\.gitlab-ci", re.IGNORECASE),
    re.compile(r"Jenkinsfile", re.IGNORECASE),
    re.compile(r"\.circleci/", re.IGNORECASE),
    re.compile(r"azure-pipelines", re.IGNORECASE),
]

# Documentation patterns
_DOC_PATTERNS = [
    re.compile(r"\.md$", re.IGNORECASE),
    re.compile(r"\.rst$", re.IGNORECASE),
    re.compile(r"/docs?/", re.IGNORECASE),
    re.compile(r"README", re.IGNORECASE),
    re.compile(r"CHANGELOG", re.IGNORECASE),
]


class PRMetadataAnalyzer:
    """Checks PR metadata and file types for review-relevant signals."""

    def analyze(self, ctx: AnalysisContext) -> List[Finding]:
        findings: List[Finding] = []
        seen: set[str] = set()

        self._check_description_quality(ctx, findings, seen)
        self._check_breaking_changes(ctx, findings, seen)
        self._check_migrations(ctx, findings, seen)
        self._check_config_changes(ctx, findings, seen)
        self._check_cicd_changes(ctx, findings, seen)
        self._check_doc_changes(ctx, findings, seen)

        return findings

    def _check_description_quality(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> None:
        body = (ctx.meta.body or "").strip()
        title = (ctx.meta.title or "").strip()

        if not body and len(title) < 20:
            fid = "meta-empty-description"
            if fid in seen:
                return
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    category="change",
                    severity=Severity.MEDIUM,
                    title="PR has no description",
                    what_changed="The PR body is empty and the title is very short.",
                    why_it_matters=(
                        "A PR without description makes it harder for reviewers to understand "
                        "the intent, context, and testing approach. Add a description."
                    ),
                    evidence=[
                        f"body_length={len(body)}",
                        f"title_length={len(title)}",
                        "body is empty",
                    ],
                    confidence="high",
                )
            )
        elif len(body) < 50:
            fid = "meta-short-description"
            if fid in seen:
                return
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    category="change",
                    severity=Severity.LOW,
                    title="PR description is very short",
                    what_changed=f"PR body is only {len(body)} characters.",
                    why_it_matters=(
                        "A very short description may not provide enough context for thorough review. "
                        "Consider adding: what changed, why, how to test."
                    ),
                    evidence=[f"body_length={len(body)}"],
                    confidence="high",
                )
            )

    def _check_breaking_changes(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> None:
        text = f"{ctx.meta.title}\n{ctx.meta.body or ''}"
        matches = _BREAKING_RE.findall(text)
        if not matches:
            return
        fid = "meta-breaking-change"
        if fid in seen:
            return
        seen.add(fid)
        findings.append(
            Finding(
                id=fid,
                category="change",
                severity=Severity.CRITICAL,
                title="Breaking change indicated",
                what_changed=f"PR title/body contains breaking change indicator: {', '.join(set(matches))}.",
                why_it_matters=(
                    "Breaking changes can affect downstream consumers. Verify compatibility, "
                    "check for migration guides, and coordinate with affected teams."
                ),
                evidence=[
                    f"indicators={', '.join(set(matches))}",
                    "pattern: breaking change keyword in title/body",
                ],
                confidence="high",
            )
        )

    def _check_migrations(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> None:
        migration_files: List[str] = []
        for f in ctx.normalized_files:
            norm = f.filename.replace("\\", "/")
            for pattern in _MIGRATION_PATTERNS:
                if pattern.search(norm):
                    migration_files.append(f.filename)
                    break

        if not migration_files:
            return
        fid = "meta-migrations"
        if fid in seen:
            return
        seen.add(fid)
        findings.append(
            Finding(
                id=fid,
                category="change",
                severity=Severity.HIGH,
                title=f"Database migration files changed ({len(migration_files)})",
                file=migration_files[0],
                what_changed=f"{len(migration_files)} migration file(s) changed.",
                why_it_matters=(
                    "Database migrations can cause irreversible data changes. Verify the migration "
                    "is reversible, tested, and coordinated with deployment."
                ),
                evidence=[f"count={len(migration_files)}"] + migration_files[:5],
                confidence="high",
            )
        )

    def _check_config_changes(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> None:
        config_files: List[str] = []
        env_files: List[str] = []
        for f in ctx.normalized_files:
            norm = f.filename.replace("\\", "/")
            for pattern in _CONFIG_PATTERNS:
                if pattern.search(norm):
                    if ".env" in norm:
                        env_files.append(f.filename)
                    else:
                        config_files.append(f.filename)
                    break

        if env_files:
            fid = "meta-env-files"
            if fid not in seen:
                seen.add(fid)
                findings.append(
                    Finding(
                        id=fid,
                        category="security",
                        severity=Severity.HIGH,
                        title=f"Environment file changed ({len(env_files)})",
                        file=env_files[0],
                        what_changed=f"{len(env_files)} environment file(s) changed.",
                        why_it_matters=(
                            "Changes to .env files may expose secrets or change runtime behavior. "
                            "Verify no secrets are committed and changes are intentional."
                        ),
                        evidence=[f"count={len(env_files)}"] + env_files[:5],
                        confidence="high",
                    )
                )

        if config_files:
            fid = "meta-config-files"
            if fid not in seen:
                seen.add(fid)
                findings.append(
                    Finding(
                        id=fid,
                        category="change",
                        severity=Severity.MEDIUM,
                        title=f"Configuration files changed ({len(config_files)})",
                        file=config_files[0],
                        what_changed=f"{len(config_files)} config file(s) changed.",
                        why_it_matters=(
                            "Configuration changes can affect runtime behavior, deployment, "
                            "and security. Review carefully."
                        ),
                        evidence=[f"count={len(config_files)}"] + config_files[:5],
                        confidence="high",
                    )
                )

    def _check_cicd_changes(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> None:
        cicd_files: List[str] = []
        for f in ctx.normalized_files:
            norm = f.filename.replace("\\", "/")
            for pattern in _CICD_PATTERNS:
                if pattern.search(norm):
                    cicd_files.append(f.filename)
                    break

        if not cicd_files:
            return
        fid = "meta-cicd"
        if fid in seen:
            return
        seen.add(fid)
        findings.append(
            Finding(
                id=fid,
                category="change",
                severity=Severity.HIGH,
                title=f"CI/CD pipeline changed ({len(cicd_files)})",
                file=cicd_files[0],
                what_changed=f"{len(cicd_files)} CI/CD file(s) changed.",
                why_it_matters=(
                    "CI/CD pipeline changes can affect build, test, and deployment processes. "
                    "Verify no security controls are bypassed."
                ),
                evidence=[f"count={len(cicd_files)}"] + cicd_files[:5],
                confidence="high",
            )
        )

    def _check_doc_changes(self, ctx: AnalysisContext, findings: List[Finding], seen: set[str]) -> None:
        doc_files: List[str] = []
        for f in ctx.normalized_files:
            norm = f.filename.replace("\\", "/")
            for pattern in _DOC_PATTERNS:
                if pattern.search(norm):
                    doc_files.append(f.filename)
                    break

        if not doc_files:
            return
        fid = "meta-docs"
        if fid in seen:
            return
        seen.add(fid)
        findings.append(
            Finding(
                id=fid,
                category="change",
                severity=Severity.INFO,
                title=f"Documentation changed ({len(doc_files)})",
                file=doc_files[0],
                what_changed=f"{len(doc_files)} documentation file(s) changed.",
                why_it_matters=(
                    "Documentation updates are generally positive. Verify they reflect the actual changes."
                ),
                evidence=[f"count={len(doc_files)}"] + doc_files[:5],
                confidence="high",
            )
        )
