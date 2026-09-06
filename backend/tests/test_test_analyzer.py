"""Unit tests for analysis/tests.py (TestAnalyzer)."""
from __future__ import annotations

from analysis.tests import TestAnalyzer
from models.analysis import Severity
from models.context import FileCategory, TestMapping
from tests.helpers import make_context, make_file


def test_missing_tests_detected() -> None:
    files = [make_file("src/payment/service.ts")]
    mappings = [TestMapping(source_file="src/payment/service.ts", related_tests=[], has_tests=False)]
    ctx = make_context(files, test_mappings=mappings)
    signal = TestAnalyzer().analyze(ctx)
    missing = [f for f in signal.findings if "test-missing" in f.id]
    assert len(missing) == 1
    assert missing[0].severity == Severity.MEDIUM


def test_tests_present_signal() -> None:
    files = [
        make_file("src/payment/service.ts"),
        make_file("src/payment/service.test.ts", is_source=False, is_test=True, category=FileCategory.TEST),
    ]
    mappings = [TestMapping(source_file="src/payment/service.ts", related_tests=["src/payment/service.test.ts"], has_tests=True)]
    ctx = make_context(files, test_mappings=mappings)
    signal = TestAnalyzer().analyze(ctx)
    present = [f for f in signal.findings if "test-coverage-present" in f.id]
    assert len(present) == 1
    assert present[0].severity == Severity.INFO
    # No missing-test finding for this file
    missing = [f for f in signal.findings if "test-missing-src/payment/service.ts" in f.id]
    assert len(missing) == 0


def test_no_tests_in_pr_detected() -> None:
    files = [make_file("src/payment/service.ts")]
    mappings = [TestMapping(source_file="src/payment/service.ts", related_tests=[], has_tests=False)]
    ctx = make_context(files, test_mappings=mappings)
    signal = TestAnalyzer().analyze(ctx)
    no_tests = [f for f in signal.findings if "test-no-tests-in-pr" in f.id]
    assert len(no_tests) == 1


def test_coverage_indication_never_invents_percentage() -> None:
    files = [make_file("src/payment/service.ts")]
    ctx = make_context(files)
    signal = TestAnalyzer().analyze(ctx)
    assert signal.coverage.has_reliable_coverage_report is False
    # The note should explicitly say no exact percentage is claimed
    assert "no exact percentage" in signal.coverage.coverage_note.lower()


def test_coverage_counts() -> None:
    files = [
        make_file("src/payment/service.ts"),
        make_file("src/auth/session.ts"),
        make_file("src/payment/service.test.ts", is_source=False, is_test=True, category=FileCategory.TEST),
    ]
    mappings = [
        TestMapping(source_file="src/payment/service.ts", related_tests=["src/payment/service.test.ts"], has_tests=True),
        TestMapping(source_file="src/auth/session.ts", related_tests=[], has_tests=False),
    ]
    ctx = make_context(files, test_mappings=mappings)
    signal = TestAnalyzer().analyze(ctx)
    assert signal.coverage.changed_source_files == 2
    assert signal.coverage.changed_test_files == 1
    assert signal.coverage.source_files_with_tests == 1
    assert signal.coverage.source_files_without_tests == 1
    assert "src/auth/session.ts" in signal.coverage.missing_test_files


def test_source_file_not_in_mappings_treated_as_missing() -> None:
    files = [make_file("src/new/file.ts")]
    ctx = make_context(files, test_mappings=[])
    signal = TestAnalyzer().analyze(ctx)
    missing = [f for f in signal.findings if "test-missing" in f.id]
    assert len(missing) == 1


def test_no_source_files_no_missing_signal() -> None:
    files = [make_file("README.md", is_source=False)]
    ctx = make_context(files, test_mappings=[])
    signal = TestAnalyzer().analyze(ctx)
    missing = [f for f in signal.findings if "test-missing" in f.id]
    assert len(missing) == 0
    no_tests = [f for f in signal.findings if "test-no-tests-in-pr" in f.id]
    assert len(no_tests) == 0
