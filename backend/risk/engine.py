"""Risk Engine: computes an explainable, weighted risk score from Phase 3 signals.

The score is an MVP heuristic, NOT a scientifically validated model.
Weights are configurable via Settings. Each dimension produces a 0-100 raw
score that is weighted by its configured weight. The result includes
contributing factors so the score is explainable.

Dimensions:
  change   — PR size (files, lines)
  scope    — scope drift
  critical — critical areas affected
  security — security findings
  quality  — quality findings
  tests    — test coverage signal

Levels:
  0-30   LOW
  31-60  MEDIUM
  61-80  HIGH
  81-100 CRITICAL
"""
from __future__ import annotations

from typing import List

from config import Settings, get_settings
from models.analysis import AnalysisResult, Severity
from models.risk import RiskDimensionScore, RiskResult, RiskWeights


# Severity -> numeric weight for aggregation
_SEVERITY_SCORES = {
    Severity.INFO: 10,
    Severity.LOW: 25,
    Severity.MEDIUM: 50,
    Severity.HIGH: 75,
    Severity.CRITICAL: 100,
}


class RiskEngine:
    """Computes the weighted risk score from an AnalysisResult."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.weights = RiskWeights(
            change=self.settings.risk_weight_change,
            scope=self.settings.risk_weight_scope,
            critical=self.settings.risk_weight_critical,
            security=self.settings.risk_weight_security,
            quality=self.settings.risk_weight_quality,
            tests=self.settings.risk_weight_tests,
        )

    def assess(self, result: AnalysisResult) -> RiskResult:
        dims: List[RiskDimensionScore] = []
        dims.append(self._score_change(result))
        dims.append(self._score_scope(result))
        dims.append(self._score_critical(result))
        dims.append(self._score_security(result))
        dims.append(self._score_quality(result))
        dims.append(self._score_tests(result))

        total_weight = self.weights.total
        if total_weight == 0:
            total_weight = 1  # avoid division by zero

        total = 0
        for d in dims:
            total += d.weighted_score
        total_score = min(100, max(0, round(total)))

        level = self._level(total_score)

        # Top contributors: dimensions with weighted_score > 0, sorted desc
        top = sorted(dims, key=lambda d: d.weighted_score, reverse=True)
        top_contributors = []
        for d in top:
            if d.weighted_score <= 0:
                continue
            factors_str = "; ".join(d.contributing_factors[:2]) if d.contributing_factors else "n/a"
            top_contributors.append(f"{d.dimension} ({d.raw_score}/100, weight {d.weight}): {factors_str}")

        return RiskResult(
            total_score=total_score,
            level=level,
            dimension_scores=dims,
            top_contributors=top_contributors[:5],
            weights=self.weights,
        )

    def _level(self, score: int) -> str:
        if score >= 81:
            return "CRITICAL"
        if score >= 61:
            return "HIGH"
        if score >= 31:
            return "MEDIUM"
        return "LOW"

    def _score_change(self, result: AnalysisResult) -> RiskDimensionScore:
        c = result.change
        factors: List[str] = []
        score = 0
        if c.size_class == "xlarge":
            score = 90
            factors.append(f"xlarge PR: {c.files_changed} files, +{c.lines_added}/-{c.lines_removed}")
        elif c.size_class == "large":
            score = 65
            factors.append(f"large PR: {c.files_changed} files, +{c.lines_added}/-{c.lines_removed}")
        elif c.size_class == "medium":
            score = 35
            factors.append(f"medium PR: {c.files_changed} files")
        else:
            score = 15
            factors.append(f"small PR: {c.files_changed} files")

        weight = self.weights.change
        return RiskDimensionScore(
            dimension="change",
            raw_score=score,
            weight=weight,
            weighted_score=score * weight / 100,
            contributing_factors=factors,
        )

    def _score_scope(self, result: AnalysisResult) -> RiskDimensionScore:
        sd = result.change.scope_drift
        factors: List[str] = []
        if sd.has_drift:
            score = 70
            factors.append(f"scope drift: unexpected areas {sd.unexpected_areas}")
            factors.append(f"stated: {sd.stated_areas}, actual: {sd.actual_areas}")
        else:
            score = 10
            factors.append("no scope drift detected")

        weight = self.weights.scope
        return RiskDimensionScore(
            dimension="scope",
            raw_score=score,
            weight=weight,
            weighted_score=score * weight / 100,
            contributing_factors=factors,
        )

    def _score_critical(self, result: AnalysisResult) -> RiskDimensionScore:
        areas = result.critical.areas
        factors: List[str] = []
        if not areas:
            score = 5
            factors.append("no critical areas affected")
        else:
            # Score based on number and severity of critical areas
            max_sev = max(
                (_SEVERITY_SCORES.get(a.severity, 50) for a in areas),
                default=0,
            )
            count_factor = min(len(areas) * 10, 30)
            score = min(100, max_sev + count_factor)
            for a in areas:
                factors.append(f"{a.kind}: {a.files[:3]}")

        weight = self.weights.critical
        return RiskDimensionScore(
            dimension="critical",
            raw_score=score,
            weight=weight,
            weighted_score=score * weight / 100,
            contributing_factors=factors,
        )

    def _score_security(self, result: AnalysisResult) -> RiskDimensionScore:
        findings = result.security.findings
        factors: List[str] = []
        if not findings:
            score = 5
            factors.append("no security findings")
        else:
            max_sev = max(
                (_SEVERITY_SCORES.get(f.severity, 25) for f in findings),
                default=0,
            )
            count_factor = min(len(findings) * 5, 20)
            score = min(100, max_sev + count_factor)
            for f in findings[:5]:
                factors.append(f"{f.title}")

        weight = self.weights.security
        return RiskDimensionScore(
            dimension="security",
            raw_score=score,
            weight=weight,
            weighted_score=score * weight / 100,
            contributing_factors=factors,
        )

    def _score_quality(self, result: AnalysisResult) -> RiskDimensionScore:
        findings = result.quality.findings
        factors: List[str] = []
        if not findings:
            score = 10
            factors.append("no quality findings")
        else:
            max_sev = max(
                (_SEVERITY_SCORES.get(f.severity, 25) for f in findings),
                default=0,
            )
            count_factor = min(len(findings) * 5, 20)
            score = min(100, max_sev + count_factor)
            for f in findings[:5]:
                factors.append(f"{f.title}")

        weight = self.weights.quality
        return RiskDimensionScore(
            dimension="quality",
            raw_score=score,
            weight=weight,
            weighted_score=score * weight / 100,
            contributing_factors=factors,
        )

    def _score_tests(self, result: AnalysisResult) -> RiskDimensionScore:
        cov = result.tests.coverage
        factors: List[str] = []
        if cov.changed_source_files == 0:
            score = 10
            factors.append("no source files changed")
        else:
            ratio = cov.source_files_with_tests / cov.changed_source_files if cov.changed_source_files else 0
            # Higher ratio = lower risk
            score = round((1 - ratio) * 100)
            factors.append(
                f"{cov.source_files_with_tests}/{cov.changed_source_files} source files have tests"
            )
            if cov.missing_test_files:
                factors.append(f"missing tests: {cov.missing_test_files[:5]}")

        weight = self.weights.tests
        return RiskDimensionScore(
            dimension="tests",
            raw_score=score,
            weight=weight,
            weighted_score=score * weight / 100,
            contributing_factors=factors,
        )
