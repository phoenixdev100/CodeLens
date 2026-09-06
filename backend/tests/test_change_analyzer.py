"""Unit tests for analysis/change.py (ChangeAnalyzer)."""
from __future__ import annotations

from analysis.change import ChangeAnalyzer
from config import Settings
from models.context import FileCategory, Language
from tests.helpers import make_context, make_file, make_meta


def _settings() -> Settings:
    return Settings(
        github_app_id="", github_private_key_path="", github_installation_id="",
        github_token="", cors_origins="http://localhost:3000",
        max_files_per_pr=300, max_files_to_retrieve=25, max_file_content_chars=50000,
        large_pr_file_count=20, xlarge_pr_file_count=50,
        large_pr_line_count=500, large_function_line_count=80, high_nesting_threshold=4,
    )


def test_small_pr_classification() -> None:
    files = [make_file("src/utils/helpers.ts", additions=10, deletions=2)]
    ctx = make_context(files)
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.files_changed == 1
    assert signal.lines_added == 10
    assert signal.lines_removed == 2
    assert signal.size_class == "small"
    assert len(signal.findings) == 0


def test_large_pr_by_file_count() -> None:
    files = [make_file(f"src/file{i}.ts", additions=5, deletions=1) for i in range(25)]
    ctx = make_context(files)
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.size_class == "large"
    assert any(f.id == "change-size" for f in signal.findings)


def test_xlarge_pr_by_file_count() -> None:
    files = [make_file(f"src/file{i}.ts", additions=5, deletions=1) for i in range(55)]
    ctx = make_context(files)
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.size_class == "xlarge"
    size_finding = next(f for f in signal.findings if f.id == "change-size")
    assert size_finding.severity.value == "high"


def test_large_pr_by_line_count() -> None:
    files = [make_file("src/big.ts", additions=600, deletions=10)]
    ctx = make_context(files)
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.size_class == "large"


def test_category_counts() -> None:
    files = [
        make_file("src/a.ts", category=FileCategory.SOURCE, is_source=True, is_test=False),
        make_file("src/a.test.ts", category=FileCategory.TEST, is_source=False, is_test=True),
        make_file("README.md", category=FileCategory.DOC, is_source=False, is_test=False),
        make_file("package.json", category=FileCategory.CONFIG, is_source=False, is_test=False),
    ]
    ctx = make_context(files)
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.category_counts.get("source") == 1
    assert signal.category_counts.get("test") == 1
    assert signal.category_counts.get("doc") == 1
    assert signal.category_counts.get("config") == 1


def test_functional_areas_detected_by_path() -> None:
    files = [
        make_file("src/payment/service.ts"),
        make_file("src/auth/session.ts"),
        make_file("src/utils/helpers.ts"),
    ]
    ctx = make_context(files)
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    area_names = [a.name for a in signal.functional_areas]
    assert "payments" in area_names
    assert "authentication" in area_names


def test_scope_drift_detected() -> None:
    files = [
        make_file("src/payment/service.ts"),
        make_file("src/auth/session.ts"),
        make_file("src/db/migration.ts"),
    ]
    ctx = make_context(files, meta=make_meta(title="Fix checkout discount calculation"))
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.scope_drift.has_drift is True
    assert "authentication" in signal.scope_drift.unexpected_areas
    assert any(f.id == "change-scope-drift" for f in signal.findings)


def test_no_scope_drift_when_areas_match_title() -> None:
    files = [make_file("src/payment/service.ts")]
    ctx = make_context(files, meta=make_meta(title="Fix payment calculation"))
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    # Only one area -> has_drift requires >= 2 areas
    assert signal.scope_drift.has_drift is False


def test_empty_pr() -> None:
    ctx = make_context([])
    signal = ChangeAnalyzer(_settings()).analyze(ctx)
    assert signal.files_changed == 0
    assert signal.lines_added == 0
    assert signal.size_class == "small"
    assert len(signal.findings) == 0
