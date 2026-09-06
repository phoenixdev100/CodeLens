"""Change Analyzer: what changed, how big, which areas, scope/drift.

Deterministic signals only. No AI.
"""
from __future__ import annotations

from typing import Dict, List

from config import Settings, get_settings
from models.analysis import (
    ChangeSignal,
    Finding,
    FunctionalArea,
    ScopeDriftSignal,
    Severity,
)
from models.context import AnalysisContext, NormalizedFile
from analysis.areas import detect_areas, infer_stated_areas


class ChangeAnalyzer:
    """Produces the ChangeSignal for an AnalysisContext."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(self, ctx: AnalysisContext) -> ChangeSignal:
        files = ctx.normalized_files
        files_changed = len(files)
        lines_added = sum(f.additions for f in files)
        lines_removed = sum(f.deletions for f in files)
        total = lines_added + lines_removed

        size_class = self._size_class(files_changed, total)

        category_counts: Dict[str, int] = {}
        for f in files:
            cat = f.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        areas = self._functional_areas(files)
        scope_drift = self._scope_drift(ctx, areas)

        findings: List[Finding] = []

        # Size finding
        if size_class in ("large", "xlarge"):
            findings.append(
                Finding(
                    id="change-size",
                    category="change",
                    severity=Severity.HIGH if size_class == "xlarge" else Severity.MEDIUM,
                    title=f"PR is {size_class} ({files_changed} files, +{lines_added}/-{lines_removed})",
                    what_changed=(
                        f"{files_changed} files changed, +{lines_added} / -{lines_removed} lines "
                        f"({total} total changes)."
                    ),
                    why_it_matters=(
                        "Large PRs are harder to review thoroughly and more likely to introduce "
                        "subtle defects. Consider breaking into smaller PRs."
                    ),
                    evidence=[
                        f"files_changed={files_changed}",
                        f"lines_added={lines_added}",
                        f"lines_removed={lines_removed}",
                        f"size_class={size_class}",
                    ],
                    confidence="high",
                )
            )

        # Scope drift finding
        if scope_drift.has_drift:
            findings.append(
                Finding(
                    id="change-scope-drift",
                    category="change",
                    severity=Severity.MEDIUM,
                    title="Potential scope drift detected",
                    what_changed=(
                        f"PR touches areas not mentioned in its title/body: "
                        f"{', '.join(scope_drift.unexpected_areas)}."
                    ),
                    why_it_matters=(
                        "The PR may be broader than its stated intent. Review whether the "
                        "unexpected areas belong in this PR."
                    ),
                    evidence=[
                        f"stated_areas={scope_drift.stated_areas}",
                        f"actual_areas={scope_drift.actual_areas}",
                        f"unexpected_areas={scope_drift.unexpected_areas}",
                        f"reason={scope_drift.reason}",
                    ],
                    confidence="medium",
                )
            )

        return ChangeSignal(
            files_changed=files_changed,
            lines_added=lines_added,
            lines_removed=lines_removed,
            total_changes=total,
            size_class=size_class,
            category_counts=category_counts,
            functional_areas=areas,
            scope_drift=scope_drift,
            findings=findings,
        )

    def _size_class(self, files_changed: int, total_lines: int) -> str:
        if files_changed >= self.settings.xlarge_pr_file_count or total_lines >= self.settings.large_pr_line_count * 3:
            return "xlarge"
        if files_changed >= self.settings.large_pr_file_count or total_lines >= self.settings.large_pr_line_count:
            return "large"
        if files_changed >= 5 or total_lines >= 100:
            return "medium"
        return "small"

    def _functional_areas(self, files: List[NormalizedFile]) -> List[FunctionalArea]:
        area_files: Dict[str, List[str]] = {}
        area_method: Dict[str, str] = {}
        for f in files:
            areas, method = detect_areas(f.filename, f.content)
            for a in areas:
                area_files.setdefault(a, [])
                if f.filename not in area_files[a]:
                    area_files[a].append(f.filename)
                # Prefer 'path' over 'keyword' if multiple files contribute
                if a not in area_method or method == "path":
                    area_method[a] = method
        return [
            FunctionalArea(name=a, files=area_files[a], detected_by=area_method.get(a, "path"))
            for a in sorted(area_files.keys())
        ]

    def _scope_drift(self, ctx: AnalysisContext, areas: List[FunctionalArea]) -> ScopeDriftSignal:
        stated = infer_stated_areas(ctx.meta.title, ctx.meta.body)
        actual = [a.name for a in areas]
        # Normalize: treat 'authentication' and 'authorization' as related but distinct.
        unexpected = [a for a in actual if a not in stated]
        has_drift = bool(unexpected) and len(actual) >= 2
        reason = ""
        if has_drift:
            reason = (
                f"PR title/body suggests: {stated or '(none detected)'}. "
                f"Changed files touch: {actual}. "
                f"Unexpected: {unexpected}."
            )
        return ScopeDriftSignal(
            has_drift=has_drift,
            stated_areas=stated,
            actual_areas=actual,
            unexpected_areas=unexpected,
            reason=reason,
        )
