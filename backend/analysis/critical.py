"""Critical Area Analyzer: detect changes to business-critical system areas.

Deterministic path + content heuristics. Each detected area includes evidence.
"""
from __future__ import annotations

from typing import Dict, List

from models.analysis import CriticalArea, CriticalAreaSignal, Finding, Severity
from models.context import AnalysisContext, NormalizedFile
from analysis.areas import normalize_path

# Critical area definitions: kind -> (path patterns, content keywords)
CRITICAL_DEFINITIONS = {
    "authentication": {
        "path": ["auth", "login", "session", "token", "password", "oauth", "saml", "jwt"],
        "content": ["verifytoken", "verifyjwt", "authenticate", "login", "password", "session"],
    },
    "authorization": {
        "path": ["permission", "rbac", "acl", "policy", "role", "authorize", "access-control"],
        "content": ["authorize", "permission", "hasrole", "isadmin", "can(", "rbac"],
    },
    "payments": {
        "path": ["payment", "checkout", "billing", "invoice", "refund", "transaction", "stripe", "paypal"],
        "content": ["charge", "refund", "stripe", "paymentintent", "transaction", "checkout"],
    },
    "sensitive-data": {
        "path": ["secret", "key", "credential", "crypto", "encrypt", "decrypt", "pii", "gdpr"],
        "content": ["encrypt", "decrypt", "secret", "apikey", "api_key", "pii", "gdpr"],
    },
    "infrastructure": {
        "path": ["infra", "docker", "kubernetes", "k8s", "terraform", "ansible", "deploy", "pipeline", ".github/workflows"],
        "content": ["dockerfile", "kubernetes", "terraform", "deployment"],
    },
}

# Business-critical path patterns (broader: e.g. core service directories).
BUSINESS_CRITICAL_PATHS = ["core", "domain", "payment", "order", "checkout", "billing"]


class CriticalAreaAnalyzer:
    """Detects changes to critical system areas and emits findings."""

    def analyze(self, ctx: AnalysisContext) -> CriticalAreaSignal:
        areas: Dict[str, CriticalArea] = {}
        findings: List[Finding] = []

        for f in ctx.normalized_files:
            if f.is_test:
                continue
            for kind, defs in CRITICAL_DEFINITIONS.items():
                matched = self._match(f, defs["path"], defs["content"])
                if matched:
                    self._add(areas, kind, f, matched)

        # Business-critical broad paths
        for f in ctx.normalized_files:
            if f.is_test:
                continue
            norm = normalize_path(f.filename)
            for p in BUSINESS_CRITICAL_PATHS:
                if f"/{p}/" in f"/{norm}/" or norm.startswith(f"{p}/"):
                    # Avoid duplicating payments (already covered above)
                    if p in ("payment", "checkout", "billing"):
                        continue
                    self._add_business_critical(areas, f, p)

        # Build findings for each detected area
        for kind, area in areas.items():
            sev = Severity.HIGH
            if kind in ("authentication", "authorization", "payments", "sensitive-data"):
                sev = Severity.CRITICAL
            area.severity = sev
            findings.append(
                Finding(
                    id=f"critical-{kind}",
                    category="critical",
                    severity=sev,
                    title=f"Critical area changed: {kind}",
                    file=area.files[0] if area.files else None,
                    what_changed=(
                        f"{len(area.files)} file(s) in the {kind} area were changed."
                    ),
                    why_it_matters=(
                        f"Changes to {kind} can have serious security or business impact. "
                        f"Review carefully."
                    ),
                    evidence=area.evidence + [f"files={area.files}"],
                    confidence="high",
                )
            )

        return CriticalAreaSignal(areas=list(areas.values()), findings=findings)

    def _match(self, f: NormalizedFile, path_patterns: List[str], content_keywords: List[str]) -> List[str]:
        evidence: List[str] = []
        norm = normalize_path(f.filename)
        for p in path_patterns:
            if p in norm:
                evidence.append(f"path contains '{p}'")
                break
        if f.content:
            lower = f.content.lower()
            for kw in content_keywords:
                if kw in lower:
                    evidence.append(f"content references '{kw}'")
                    break
        return evidence

    def _add(self, areas: Dict[str, CriticalArea], kind: str, f: NormalizedFile, evidence: List[str]) -> None:
        if kind not in areas:
            areas[kind] = CriticalArea(name=kind, kind=kind, files=[], evidence=[])
        if f.filename not in areas[kind].files:
            areas[kind].files.append(f.filename)
        for e in evidence:
            if e not in areas[kind].evidence:
                areas[kind].evidence.append(e)

    def _add_business_critical(self, areas: Dict[str, CriticalArea], f: NormalizedFile, path_keyword: str) -> None:
        kind = "business-critical"
        if kind not in areas:
            areas[kind] = CriticalArea(name=kind, kind=kind, files=[], evidence=[])
        if f.filename not in areas[kind].files:
            areas[kind].files.append(f.filename)
        ev = f"path contains '/{path_keyword}/'"
        if ev not in areas[kind].evidence:
            areas[kind].evidence.append(ev)
