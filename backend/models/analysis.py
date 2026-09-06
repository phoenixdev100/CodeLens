"""Pydantic schemas for the Phase 3 analysis result.

The AnalysisResult is the structured, evidence-backed output of the
deterministic analysis engine. It is consumed by Phase 4 (AI + Risk + Priority).
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from models.schemas import PRMeta


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(BaseModel):
    """A single evidence-backed analysis finding.

    Every finding attempts to answer WHAT / WHERE / WHY / IMPACT.
    """

    id: str = Field(..., description="Stable identifier for this finding")
    category: str = Field(
        ..., description="change | critical | security | quality | tests"
    )
    severity: Severity = Severity.INFO
    title: str
    file: Optional[str] = None
    line_range: Optional[Tuple[int, int]] = None
    what_changed: str = ""
    why_it_matters: str = ""
    evidence: List[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM


class FunctionalArea(BaseModel):
    name: str
    files: List[str] = Field(default_factory=list)
    detected_by: str = Field(
        default="path", description="path | keyword | content"
    )


class ScopeDriftSignal(BaseModel):
    """Signal indicating the PR may be broader than its stated intent."""

    has_drift: bool = False
    stated_areas: List[str] = Field(
        default_factory=list,
        description="Functional areas inferred from PR title/body",
    )
    actual_areas: List[str] = Field(
        default_factory=list,
        description="Functional areas inferred from changed files",
    )
    unexpected_areas: List[str] = Field(
        default_factory=list,
        description="Actual areas not mentioned in the PR title/body",
    )
    reason: str = ""


class ChangeSignal(BaseModel):
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    total_changes: int = 0
    size_class: str = Field(
        default="small", description="small | medium | large | xlarge"
    )
    category_counts: Dict[str, int] = Field(default_factory=dict)
    functional_areas: List[FunctionalArea] = Field(default_factory=list)
    scope_drift: ScopeDriftSignal = Field(default_factory=ScopeDriftSignal)
    findings: List[Finding] = Field(default_factory=list)


class CriticalArea(BaseModel):
    name: str
    kind: str = Field(
        ..., description="authentication | authorization | payments | sensitive-data | infrastructure | business-critical"
    )
    files: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    severity: Severity = Severity.HIGH


class CriticalAreaSignal(BaseModel):
    areas: List[CriticalArea] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)


class SecurityCheckResult(BaseModel):
    """Result of a single security check category."""

    check_type: str = Field(..., description="secret-scan | injection | xss | csrf | path-traversal | ssrf | command-injection | sensitive-file | dependency")
    status: str = Field(..., description="pass | warn | fail")
    summary: str = ""
    findings: List[Finding] = Field(default_factory=list)


class SecuritySignal(BaseModel):
    findings: List[Finding] = Field(default_factory=list)
    checks: List[SecurityCheckResult] = Field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0


class QualitySignal(BaseModel):
    findings: List[Finding] = Field(default_factory=list)


class TestCoverageIndication(BaseModel):
    """A coverage *indication*, never an invented exact percentage."""

    # Prevent pytest from trying to collect this Pydantic model as a test class.
    __test__ = False

    changed_source_files: int = 0
    changed_test_files: int = 0
    source_files_with_tests: int = 0
    source_files_without_tests: int = 0
    missing_test_files: List[str] = Field(default_factory=list)
    has_reliable_coverage_report: bool = False
    coverage_note: str = Field(
        default="Test signal based on changed-file and naming-convention heuristics."
    )


class TestSignal(BaseModel):
    # Prevent pytest from trying to collect this Pydantic model as a test class.
    __test__ = False

    coverage: TestCoverageIndication = Field(default_factory=TestCoverageIndication)
    findings: List[Finding] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Top-level structured analysis output (Phase 3)."""

    phase: str = "phase-3-analysis-engine"
    meta: PRMeta
    change: ChangeSignal = Field(default_factory=ChangeSignal)
    critical: CriticalAreaSignal = Field(default_factory=CriticalAreaSignal)
    security: SecuritySignal = Field(default_factory=SecuritySignal)
    quality: QualitySignal = Field(default_factory=QualitySignal)
    tests: TestSignal = Field(default_factory=TestSignal)
    all_findings: List[Finding] = Field(default_factory=list)
    stats: Dict[str, int] = Field(default_factory=dict)
