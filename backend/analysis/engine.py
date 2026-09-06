"""Analysis Engine: orchestrates all deterministic analyzers.

Consumes a Phase 2 AnalysisContext and produces a Phase 3 AnalysisResult.
No AI, no risk scoring, no review priority (Phase 4).
"""
from __future__ import annotations

from typing import List

from config import Settings, get_settings
from models.analysis import AnalysisResult, Finding
from models.context import AnalysisContext
from analysis.change import ChangeAnalyzer
from analysis.critical import CriticalAreaAnalyzer
from analysis.metadata import PRMetadataAnalyzer
from analysis.quality import QualityAnalyzer
from analysis.security import SecurityAnalyzer
from analysis.tests import TestAnalyzer


class AnalysisEngine:
    """Runs all deterministic analyzers and aggregates findings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.change = ChangeAnalyzer(self.settings)
        self.critical = CriticalAreaAnalyzer()
        self.security = SecurityAnalyzer()
        self.quality = QualityAnalyzer(self.settings)
        self.tests = TestAnalyzer()
        self.metadata = PRMetadataAnalyzer()

    def analyze(self, ctx: AnalysisContext) -> AnalysisResult:
        change_signal = self.change.analyze(ctx)
        critical_signal = self.critical.analyze(ctx)
        security_signal = self.security.analyze(ctx)
        quality_signal = self.quality.analyze(ctx)
        test_signal = self.tests.analyze(ctx)
        metadata_findings = self.metadata.analyze(ctx)

        all_findings: List[Finding] = (
            change_signal.findings
            + critical_signal.findings
            + security_signal.findings
            + quality_signal.findings
            + test_signal.findings
            + metadata_findings
        )

        stats = {
            "total_findings": len(all_findings),
            "change_findings": len(change_signal.findings) + len(metadata_findings),
            "critical_findings": len(critical_signal.findings),
            "security_findings": len(security_signal.findings),
            "quality_findings": len(quality_signal.findings),
            "test_findings": len(test_signal.findings),
            "critical_areas": len(critical_signal.areas),
            "functional_areas": len(change_signal.functional_areas),
            "missing_test_files": len(test_signal.coverage.missing_test_files),
            "security_checks_total": security_signal.total_checks,
            "security_checks_passed": security_signal.passed_checks,
            "security_checks_failed": security_signal.failed_checks,
        }

        return AnalysisResult(
            meta=ctx.meta,
            change=change_signal,
            critical=critical_signal,
            security=security_signal,
            quality=quality_signal,
            tests=test_signal,
            all_findings=all_findings,
            stats=stats,
        )
