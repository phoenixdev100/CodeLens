"""Unit tests for analysis/engine.py (AnalysisEngine)."""
from __future__ import annotations

from analysis.engine import AnalysisEngine
from config import Settings
from models.context import FileCategory, TestMapping
from tests.helpers import make_context, make_file, make_meta


def _settings() -> Settings:
    return Settings(
        github_app_id="", github_private_key_path="", github_installation_id="",
        github_token="", cors_origins="http://localhost:3000",
        max_files_per_pr=300, max_files_to_retrieve=25, max_file_content_chars=50000,
        large_pr_file_count=20, xlarge_pr_file_count=50,
        large_pr_line_count=500, large_function_line_count=80, high_nesting_threshold=4,
    )


def test_engine_aggregates_all_findings() -> None:
    files = [
        make_file("src/payment/service.ts", content='const password = "supersecret123";\n'),
        make_file("src/auth/session.ts"),
    ]
    ctx = make_context(files, meta=make_meta(title="Fix payment bug", body="This PR fixes the payment calculation bug in the checkout flow."))
    result = AnalysisEngine(_settings()).analyze(ctx)

    assert result.phase == "phase-3-analysis-engine"
    # Should have findings from multiple categories
    categories = {f.category for f in result.all_findings}
    assert "security" in categories
    assert "critical" in categories
    assert "tests" in categories
    # all_findings should equal the sum of individual signals + metadata findings
    expected = (
        len(result.change.findings)
        + len(result.critical.findings)
        + len(result.security.findings)
        + len(result.quality.findings)
        + len(result.tests.findings)
    )
    # Metadata findings are added to all_findings but not to individual signals
    # So all_findings >= expected
    assert len(result.all_findings) >= expected


def test_engine_stats_populated() -> None:
    files = [make_file("src/payment/service.ts")]
    ctx = make_context(files)
    result = AnalysisEngine(_settings()).analyze(ctx)
    assert result.stats["total_findings"] == len(result.all_findings)
    assert result.stats["critical_areas"] >= 1
    assert result.stats["functional_areas"] >= 1


def test_engine_empty_context() -> None:
    ctx = make_context([], meta=make_meta(title="Fix checkout bug in payment service", body="This PR fixes the checkout bug by updating the payment service to handle edge cases properly."))
    result = AnalysisEngine(_settings()).analyze(ctx)
    # With a proper description, metadata analyzer should not produce findings
    assert len(result.all_findings) == 0
    assert result.stats["total_findings"] == 0


def test_engine_meta_preserved() -> None:
    meta = make_meta(title="My PR", body="Some body")
    ctx = make_context([], meta=meta)
    result = AnalysisEngine(_settings()).analyze(ctx)
    assert result.meta.title == "My PR"
    assert result.meta.number == 42


def test_engine_full_pr_scenario() -> None:
    """End-to-end-ish: a realistic PR touching payment + auth with no tests."""
    files = [
        make_file("src/payment/service.ts", additions=50, deletions=10,
                  content='export function charge(amount: number) { return amount; }\n'),
        make_file("src/auth/session.ts", additions=20, deletions=5,
                  content='export function verifyToken(token: string) { return true; }\n'),
        make_file("src/db/migration.ts", additions=15, deletions=0),
        make_file("package.json", category=FileCategory.CONFIG, is_source=False, additions=1, deletions=0,
                  patch_text='@@ -1,3 +1,4 @@\n {\n   "dependencies": {\n+    "lodash": "^4.17.21",\n     "react": "^18.0.0"\n   }\n }'),
    ]
    mappings = [
        TestMapping(source_file="src/payment/service.ts", related_tests=[], has_tests=False),
        TestMapping(source_file="src/auth/session.ts", related_tests=[], has_tests=False),
        TestMapping(source_file="src/db/migration.ts", related_tests=[], has_tests=False),
    ]
    ctx = make_context(files, meta=make_meta(title="Fix payment calculation"), test_mappings=mappings)
    result = AnalysisEngine(_settings()).analyze(ctx)

    # Should have critical areas (payments, authentication)
    critical_kinds = {a.kind for a in result.critical.areas}
    assert "payments" in critical_kinds
    assert "authentication" in critical_kinds

    # Should have security findings (sensitive files, dependency change)
    assert len(result.security.findings) >= 2

    # Should have test findings (missing tests)
    test_missing = [f for f in result.tests.findings if "test-missing" in f.id]
    assert len(test_missing) >= 3

    # Should detect scope drift (title says payment, but auth + db also touched)
    assert result.change.scope_drift.has_drift is True

    # Stats should be consistent
    assert result.stats["total_findings"] == len(result.all_findings)
    assert result.stats["total_findings"] > 0
