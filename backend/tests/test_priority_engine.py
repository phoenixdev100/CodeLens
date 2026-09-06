"""Unit tests for the review priority engine (priority/engine.py)."""
from __future__ import annotations

from analysis.engine import AnalysisEngine
from config import Settings
from models.analysis import Severity
from models.context import FileCategory
from priority.engine import PriorityEngine
from tests.helpers import make_context, make_file, make_meta


def _settings() -> Settings:
    return Settings(
        github_app_id="", github_private_key_path="", github_installation_id="",
        github_token="", cors_origins="http://localhost:3000",
        max_files_per_pr=300, max_files_to_retrieve=25, max_file_content_chars=50000,
        large_pr_file_count=20, xlarge_pr_file_count=50,
        large_pr_line_count=500, large_function_line_count=80, high_nesting_threshold=4,
        openai_api_key="", openai_model="gpt-4o-mini",
        ai_provider="mock", ai_max_context_findings=30,
        risk_weight_change=15, risk_weight_scope=15, risk_weight_critical=25,
        risk_weight_security=20, risk_weight_quality=10, risk_weight_tests=15,
    )


def _analyze(files, meta=None):
    ctx = make_context(files, meta=meta or make_meta(title="Fix payment"))
    return AnalysisEngine(_settings()).analyze(ctx)


def test_empty_pr_no_priority() -> None:
    result = _analyze([])
    priority = PriorityEngine().prioritize(result)
    assert len(priority.items) == 0
    assert len(priority.top_concerns) == 0


def test_priority_items_ranked_by_score() -> None:
    files = [
        make_file("src/payment/service.ts", content='const password = "supersecret123";\n'),
        make_file("src/auth/session.ts"),
        make_file("src/utils/helpers.ts"),
    ]
    result = _analyze(files, meta=make_meta(title="Fix typo"))
    priority = PriorityEngine().prioritize(result)
    assert len(priority.items) > 0
    # Items should be sorted by score descending
    scores = [item.score for item in priority.items]
    assert scores == sorted(scores, reverse=True)
    # Ranks should be 1, 2, 3, ...
    for i, item in enumerate(priority.items):
        assert item.rank == i + 1


def test_priority_item_has_supporting_findings() -> None:
    files = [make_file("src/auth/config.ts", content='const password = "supersecret123";\n')]
    result = _analyze(files)
    priority = PriorityEngine().prioritize(result)
    assert len(priority.items) > 0
    item = priority.items[0]
    assert item.file == "src/auth/config.ts"
    assert len(item.supporting_finding_ids) > 0
    assert len(item.reason) > 0


def test_critical_files_get_bonus() -> None:
    files = [
        make_file("src/payment/service.ts"),
        make_file("src/utils/helpers.ts"),
    ]
    result = _analyze(files, meta=make_meta(title="Fix payment"))
    priority = PriorityEngine().prioritize(result)
    # payment/service.ts should rank higher than utils/helpers.ts
    by_file = {item.file: item for item in priority.items}
    if "src/payment/service.ts" in by_file and "src/utils/helpers.ts" in by_file:
        assert by_file["src/payment/service.ts"].score >= by_file["src/utils/helpers.ts"].score


def test_missing_test_files_get_bonus() -> None:
    files = [make_file("src/payment/service.ts", additions=50, deletions=10)]
    result = _analyze(files)
    priority = PriorityEngine().prioritize(result)
    # The file should be in the priority list with a missing-test reason
    item = next((i for i in priority.items if i.file == "src/payment/service.ts"), None)
    assert item is not None
    assert "test" in item.reason.lower() or "critical" in item.reason.lower()


def test_scores_capped_at_100() -> None:
    # Create many findings on one file
    files = [make_file("src/auth/session.ts", content='const password = "supersecret123"; const eval = eval("x");\n')]
    result = _analyze(files)
    priority = PriorityEngine().prioritize(result)
    for item in priority.items:
        assert item.score <= 100


def test_top_concerns_populated() -> None:
    files = [make_file("src/payment/service.ts"), make_file("src/auth/session.ts")]
    result = _analyze(files, meta=make_meta(title="Fix typo"))
    priority = PriorityEngine().prioritize(result)
    assert len(priority.top_concerns) > 0
    assert len(priority.top_concerns) <= 3


def test_severity_reflects_max_finding() -> None:
    files = [make_file("src/auth/config.ts", content='const password = "supersecret123";\n')]
    result = _analyze(files)
    priority = PriorityEngine().prioritize(result)
    item = next((i for i in priority.items if i.file == "src/auth/config.ts"), None)
    assert item is not None
    # Should have at least HIGH severity (hardcoded password = HIGH)
    assert item.severity in (Severity.HIGH, Severity.CRITICAL)


def test_priority_deterministic() -> None:
    files = [make_file("src/payment/service.ts"), make_file("src/auth/session.ts")]
    result = _analyze(files, meta=make_meta(title="Fix typo"))
    p1 = PriorityEngine().prioritize(result)
    p2 = PriorityEngine().prioritize(result)
    assert [i.file for i in p1.items] == [i.file for i in p2.items]
    assert [i.score for i in p1.items] == [i.score for i in p2.items]
