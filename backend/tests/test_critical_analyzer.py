"""Unit tests for analysis/critical.py (CriticalAreaAnalyzer)."""
from __future__ import annotations

from analysis.critical import CriticalAreaAnalyzer
from models.analysis import Severity
from models.context import FileCategory
from tests.helpers import make_context, make_file


def test_authentication_area_detected() -> None:
    files = [make_file("src/auth/session.ts")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    kinds = [a.kind for a in signal.areas]
    assert "authentication" in kinds
    auth = next(a for a in signal.areas if a.kind == "authentication")
    assert auth.severity == Severity.CRITICAL
    assert "src/auth/session.ts" in auth.files


def test_payments_area_detected() -> None:
    files = [make_file("src/payment/refund.ts")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    kinds = [a.kind for a in signal.areas]
    assert "payments" in kinds


def test_authorization_area_detected() -> None:
    files = [make_file("src/auth/permissions.ts")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    kinds = [a.kind for a in signal.areas]
    # permissions path matches both auth and authorization
    assert "authorization" in kinds


def test_infrastructure_area_detected() -> None:
    files = [make_file("infra/deploy.yml", category=FileCategory.CONFIG, is_source=False)]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    kinds = [a.kind for a in signal.areas]
    assert "infrastructure" in kinds


def test_sensitive_data_area_detected_by_content() -> None:
    files = [make_file("src/utils/codec.ts", content="export function encrypt(data: string) { ... }")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    kinds = [a.kind for a in signal.areas]
    assert "sensitive-data" in kinds


def test_no_critical_areas_for_utility_files() -> None:
    files = [make_file("src/utils/format.ts")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    assert len(signal.areas) == 0
    assert len(signal.findings) == 0


def test_test_files_excluded() -> None:
    files = [make_file("src/auth/session.test.ts", is_source=False, is_test=True, category=FileCategory.TEST)]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    # Test files should not trigger critical area detection
    assert len(signal.areas) == 0


def test_finding_has_evidence() -> None:
    files = [make_file("src/auth/session.ts")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    finding = next(f for f in signal.findings if f.category == "critical")
    assert len(finding.evidence) > 0
    assert finding.file == "src/auth/session.ts"


def test_business_critical_path_detected() -> None:
    files = [make_file("src/core/engine.ts")]
    ctx = make_context(files)
    signal = CriticalAreaAnalyzer().analyze(ctx)
    kinds = [a.kind for a in signal.areas]
    assert "business-critical" in kinds
