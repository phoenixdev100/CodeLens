"""Review Priority Engine: ranks files by aggregating finding severities.

Deterministic — no AI. Each file gets a score (0-100) based on:
  - Finding severities attached to that file
  - Whether the file is in a critical area
  - Whether the file has missing tests
  - Change size (additions)

Files are ranked by score descending. Each PriorityItem includes the
supporting finding IDs so the reviewer can trace the reasoning.
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple

from models.analysis import AnalysisResult, Finding, Severity
from models.priority import PriorityItem, ReviewPriority


_SEVERITY_POINTS = {
    Severity.INFO: 5,
    Severity.LOW: 15,
    Severity.MEDIUM: 30,
    Severity.HIGH: 50,
    Severity.CRITICAL: 70,
}

# Bonus for files in critical areas
_CRITICAL_BONUS = 20
# Bonus for files with missing tests
_MISSING_TEST_BONUS = 10
# Bonus for large additions
_LARGE_ADDITION_BONUS = 15
_LARGE_ADDITION_THRESHOLD = 200


class PriorityEngine:
    """Produces a deterministic, evidence-backed review priority list."""

    def prioritize(self, result: AnalysisResult) -> ReviewPriority:
        # Collect files from findings and from normalized files
        file_findings: Dict[str, List[Finding]] = {}
        for f in result.all_findings:
            if f.file:
                file_findings.setdefault(f.file, [])
                file_findings[f.file].append(f)

        # Critical area files
        critical_files: Set[str] = set()
        for area in result.critical.areas:
            for fn in area.files:
                critical_files.add(fn)

        # Missing test files
        missing_test_files: Set[str] = set(result.tests.coverage.missing_test_files)

        # Build candidate file set: files in findings + critical files + changed source files
        candidates: Set[str] = set(file_findings.keys()) | critical_files
        # Also include changed source files from the change signal (via normalized_files in context)
        # We don't have direct access to normalized_files here, but we can use test mappings
        for tm in result.tests.coverage.missing_test_files:
            candidates.add(tm)

        if not candidates:
            return ReviewPriority(items=[], top_concerns=[])

        # Compute per-file scores
        scored: List[Tuple[str, int, Severity, List[str], str]] = []
        for fn in candidates:
            findings = file_findings.get(fn, [])
            score = 0
            reasons: List[str] = []
            finding_ids: List[str] = []

            # Finding severity points
            for f in findings:
                pts = _SEVERITY_POINTS.get(f.severity, 10)
                score += pts
                finding_ids.append(f.id)
                reasons.append(f"{f.title} ({f.severity.value})")

            # Critical area bonus
            if fn in critical_files:
                score += _CRITICAL_BONUS
                reasons.append(f"file is in a critical area (+{_CRITICAL_BONUS})")

            # Missing test bonus
            if fn in missing_test_files:
                score += _MISSING_TEST_BONUS
                reasons.append(f"no corresponding test change detected (+{_MISSING_TEST_BONUS})")

            # Cap at 100
            score = min(100, score)

            # Determine overall severity for this file (max of its findings)
            if findings:
                max_sev = max(findings, key=lambda f: list(_SEVERITY_POINTS.keys()).index(f.severity) if f.severity in _SEVERITY_POINTS else 0)
                severity = max_sev.severity
            elif fn in critical_files:
                severity = Severity.HIGH
            else:
                severity = Severity.MEDIUM

            reason = "; ".join(reasons[:4]) if reasons else "flagged by analysis signals"
            scored.append((fn, score, severity, finding_ids, reason))

        # Sort by score descending, then by filename for stability
        scored.sort(key=lambda x: (-x[1], x[0]))

        items = [
            PriorityItem(
                rank=i + 1,
                file=fn,
                score=score,
                severity=sev,
                reason=reason,
                supporting_finding_ids=fids,
            )
            for i, (fn, score, sev, fids, reason) in enumerate(scored)
        ]

        # Top concerns summary
        top_concerns = []
        for item in items[:3]:
            top_concerns.append(f"{item.rank}. {item.file} (score {item.score}, {item.severity.value})")

        return ReviewPriority(items=items, top_concerns=top_concerns)
