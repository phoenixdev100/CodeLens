"""Unit tests for the Phase 4 engine (phase4.py)."""
from __future__ import annotations

from config import Settings
from models.phase4 import Phase4Result
from phase4 import Phase4Engine
from tests.helpers import make_context, make_file, make_meta


def _settings(provider: str = "mock", api_key: str = "") -> Settings:
    return Settings(
        github_app_id="", github_private_key_path="", github_installation_id="",
        github_token="", cors_origins="http://localhost:3000",
        max_files_per_pr=300, max_files_to_retrieve=25, max_file_content_chars=50000,
        large_pr_file_count=20, xlarge_pr_file_count=50,
        large_pr_line_count=500, large_function_line_count=80, high_nesting_threshold=4,
        openai_api_key=api_key, openai_model="gpt-4o-mini",
        ai_provider=provider, ai_max_context_findings=30,
        gemini_api_key="", gemini_model="gemini-3.6-flash",
        risk_weight_change=15, risk_weight_scope=15, risk_weight_critical=25,
        risk_weight_security=20, risk_weight_quality=10, risk_weight_tests=15,
    )


def test_phase4_result_structure() -> None:
    files = [make_file("src/payment/service.ts"), make_file("src/auth/session.ts")]
    ctx = make_context(files, meta=make_meta(title="Fix payment"))
    result = Phase4Engine(_settings()).analyze(ctx)

    assert isinstance(result, Phase4Result)
    assert result.phase == "phase-4-ai-risk-priority"
    assert result.meta.title == "Fix payment"
    # Contains Phase 3 analysis
    assert result.analysis.phase == "phase-3-analysis-engine"
    # Contains AI insights
    assert result.ai_insights.provider == "mock"
    assert result.ai_insights.is_ai_generated is True
    # Contains risk
    assert 0 <= result.risk.total_score <= 100
    assert result.risk.level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    # Contains priority
    assert len(result.priority.items) > 0


def test_phase4_stats_populated() -> None:
    files = [make_file("src/payment/service.ts")]
    ctx = make_context(files)
    result = Phase4Engine(_settings()).analyze(ctx)
    assert result.stats["total_findings"] == len(result.analysis.all_findings)
    assert result.stats["risk_score"] == result.risk.total_score
    assert result.stats["risk_level"] == result.risk.level
    assert result.stats["priority_items"] == len(result.priority.items)
    assert result.stats["ai_provider"] == 0  # mock


def test_phase4_empty_pr() -> None:
    ctx = make_context([])
    result = Phase4Engine(_settings()).analyze(ctx)
    assert result.risk.level == "LOW"
    assert len(result.priority.items) == 0
    assert result.ai_insights.is_ai_generated is True


def test_phase4_uses_mock_without_key() -> None:
    files = [make_file("src/payment/service.ts")]
    ctx = make_context(files)
    result = Phase4Engine(_settings(provider="auto", api_key="")).analyze(ctx)
    assert result.ai_insights.provider == "mock"


def test_phase4_ai_insights_have_disclaimer() -> None:
    files = [make_file("src/payment/service.ts")]
    ctx = make_context(files)
    result = Phase4Engine(_settings()).analyze(ctx)
    assert "inaccurracies" in result.ai_insights.disclaimer or "verify" in result.ai_insights.disclaimer.lower()


def test_phase4_full_pr_scenario() -> None:
    """Realistic PR: payment + auth + db, no tests, scope drift."""
    files = [
        make_file("src/payment/service.ts", additions=50, deletions=10,
                  content='export function charge(amount: number) { return amount; }\n'),
        make_file("src/auth/session.ts", additions=20, deletions=5,
                  content='export function verifyToken(token: string) { return true; }\n'),
        make_file("src/db/migration.ts", additions=15, deletions=0),
    ]
    ctx = make_context(files, meta=make_meta(title="Fix payment calculation"))
    result = Phase4Engine(_settings()).analyze(ctx)

    # Risk should be elevated (critical areas + scope drift + missing tests)
    assert result.risk.total_score >= 31
    # Priority should rank payment and auth files high
    assert len(result.priority.items) >= 2
    # AI should mention the areas
    assert "payment" in result.ai_insights.pr_intent.lower() or "payment" in result.ai_insights.functional_area_interpretation.lower()
    # All findings should be traceable in priority
    all_priority_fids = set()
    for item in result.priority.items:
        all_priority_fids.update(item.supporting_finding_ids)
    # At least some findings should be referenced
    assert len(all_priority_fids) > 0


def test_phase4_risk_contributors_explainable() -> None:
    files = [make_file("src/payment/service.ts"), make_file("src/auth/session.ts")]
    ctx = make_context(files, meta=make_meta(title="Fix typo"))
    result = Phase4Engine(_settings()).analyze(ctx)
    assert len(result.risk.top_contributors) > 0
    # Each contributor should mention a dimension and its score
    for c in result.risk.top_contributors:
        assert any(dim in c for dim in ["change", "scope", "critical", "security", "quality", "tests"])


def test_phase4_meta_preserved() -> None:
    meta = make_meta(title="My Custom Title", body="Custom body")
    ctx = make_context([], meta=meta)
    result = Phase4Engine(_settings()).analyze(ctx)
    assert result.meta.title == "My Custom Title"
