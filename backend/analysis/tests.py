"""Test Analyzer: test signals using Phase 2 test mappings.

Never invents an exact coverage percentage. Reports a "test coverage indication"
based on changed-file and naming-convention heuristics.
"""
from __future__ import annotations

from typing import List

from models.analysis import Finding, Severity, TestCoverageIndication, TestSignal
from models.context import AnalysisContext, NormalizedFile


class TestAnalyzer:
    """Produces test signals from the AnalysisContext."""

    def analyze(self, ctx: AnalysisContext) -> TestSignal:
        source_files = [f for f in ctx.normalized_files if f.is_source]
        test_files = [f for f in ctx.normalized_files if f.is_test]

        # Use Phase 2 test mappings
        mapping_by_src = {tm.source_file: tm for tm in ctx.test_mappings}
        with_tests = [tm.source_file for tm in ctx.test_mappings if tm.has_tests]
        without_tests = [tm.source_file for tm in ctx.test_mappings if not tm.has_tests]

        # Also catch source files not in mappings (e.g. no mapping built)
        mapped_srcs = set(mapping_by_src.keys())
        for f in source_files:
            if f.filename not in mapped_srcs:
                without_tests.append(f.filename)

        coverage = TestCoverageIndication(
            changed_source_files=len(source_files),
            changed_test_files=len(test_files),
            source_files_with_tests=len(with_tests),
            source_files_without_tests=len(without_tests),
            missing_test_files=without_tests,
            has_reliable_coverage_report=False,
            coverage_note=(
                "Test signal based on changed-file and naming-convention heuristics. "
                "No reliable coverage report was available; no exact percentage is claimed."
            ),
        )

        findings: List[Finding] = []

        # Missing tests for changed source files
        if without_tests:
            # Group into one finding per file for clarity, but cap at a reasonable number
            for src in without_tests[:20]:
                findings.append(
                    Finding(
                        id=f"test-missing-{src}",
                        category="tests",
                        severity=Severity.MEDIUM,
                        title=f"No corresponding test change detected for {src}",
                        file=src,
                        what_changed=(
                            f"Production file '{src}' was changed but no related test file "
                            f"change was detected in this PR."
                        ),
                        why_it_matters=(
                            "Changes to production code without corresponding test changes "
                            "may indicate insufficient test coverage for the new behavior."
                        ),
                        evidence=[
                            "no related test file in changed files",
                            "no test file matched by naming convention",
                        ],
                        confidence="medium",
                    )
                )

        # Positive signal: tests added for source changes
        if with_tests:
            findings.append(
                Finding(
                    id="test-coverage-present",
                    category="tests",
                    severity=Severity.INFO,
                    title=f"Test changes detected for {len(with_tests)} source file(s)",
                    what_changed=(
                        f"{len(with_tests)} changed source file(s) have corresponding test "
                        f"changes in this PR."
                    ),
                    why_it_matters=(
                        "Corresponding test changes increase confidence in the production change."
                    ),
                    evidence=[f"source_files_with_tests={len(with_tests)}"] + with_tests[:10],
                    confidence="high",
                )
            )

        # No tests at all in a PR that changes source files
        if source_files and not test_files:
            findings.append(
                Finding(
                    id="test-no-tests-in-pr",
                    category="tests",
                    severity=Severity.MEDIUM,
                    title="PR changes production code but includes no test files",
                    what_changed=(
                        f"{len(source_files)} production file(s) changed, but 0 test files "
                        f"are included in this PR."
                    ),
                    why_it_matters=(
                        "PRs that change production code without any tests are riskier to merge. "
                        "Consider adding tests."
                    ),
                    evidence=[
                        f"changed_source_files={len(source_files)}",
                        "changed_test_files=0",
                    ],
                    confidence="high",
                )
            )

        return TestSignal(coverage=coverage, findings=findings)
