"""Unit tests for the risk engine (risk/engine.py)."""
from __future__ import annotations

from analysis.engine import AnalysisEngine
from config import Settings
from models.analysis import Severity
from risk.engine import RiskEngine
from tests.helpers import make_context, make_file, make_meta


def _settings(**overrides) -> Settings:
    defaults = dict(
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
    defaults.update(overrides)
    return Settings(**defaults)


def _analyze(files, settings=None, meta=None):
    ctx = make_context(files, meta=meta or make_meta(title="Fix payment"))
    engine = AnalysisEngine(settings or _settings())
    return engine.analyze(ctx)


def test_low_risk_for_small_clean_pr() -> None:
    files = [make_file("src/utils/helpers.ts", additions=5, deletions=1)]
    result = _analyze(files)
    risk = RiskEngine(_settings()).assess(result)
    assert risk.total_score <= 30
    assert risk.level == "LOW"


def test_high_risk_for_large_pr_with_critical_areas() -> None:
    files = [make_file(f"src/payment/file{i}.ts", additions=30, deletions=5) for i in range(25)]
    result = _analyze(files, meta=make_meta(title="Fix typo"))
    risk = RiskEngine(_settings()).assess(result)
    assert risk.total_score >= 31
    assert risk.level in ("MEDIUM", "HIGH", "CRITICAL")


def test_risk_levels_boundaries() -> None:
    engine = RiskEngine(_settings())
    assert engine._level(0) == "LOW"
    assert engine._level(30) == "LOW"
    assert engine._level(31) == "MEDIUM"
    assert engine._level(60) == "MEDIUM"
    assert engine._level(61) == "HIGH"
    assert engine._level(80) == "HIGH"
    assert engine._level(81) == "CRITICAL"
    assert engine._level(100) == "CRITICAL"


def test_risk_dimension_scores_present() -> None:
    files = [make_file("src/payment/service.ts")]
    result = _analyze(files)
    risk = RiskEngine(_settings()).assess(result)
    dims = {d.dimension for d in risk.dimension_scores}
    assert dims == {"change", "scope", "critical", "security", "quality", "tests"}


def test_risk_contributing_factors_populated() -> None:
    files = [make_file("src/payment/service.ts", additions=50, deletions=10)]
    result = _analyze(files, meta=make_meta(title="Fix typo"))
    risk = RiskEngine(_settings()).assess(result)
    assert len(risk.top_contributors) > 0
    # Each contributor should mention a dimension
    assert any("critical" in c or "change" in c or "scope" in c for c in risk.top_contributors)


def test_risk_weights_configurable() -> None:
    # Set critical weight to 100, others to 0
    settings = _settings(
        risk_weight_change=0, risk_weight_scope=0, risk_weight_critical=100,
        risk_weight_security=0, risk_weight_quality=0, risk_weight_tests=0,
    )
    files = [make_file("src/payment/service.ts")]
    result = _analyze(files, settings=settings)
    risk = RiskEngine(settings).assess(result)
    # With only critical weight, score should be driven entirely by critical dimension
    critical_dim = next(d for d in risk.dimension_scores if d.dimension == "critical")
    assert critical_dim.weight == 100
    change_dim = next(d for d in risk.dimension_scores if d.dimension == "change")
    assert change_dim.weight == 0
    assert change_dim.weighted_score == 0


def test_risk_disclaimer_present() -> None:
    files = [make_file("src/utils/helpers.ts")]
    result = _analyze(files)
    risk = RiskEngine(_settings()).assess(result)
    assert "MVP heuristic" in risk.disclaimer
    assert "not a scientifically validated" in risk.disclaimer


def test_risk_score_in_range() -> None:
    files = [make_file(f"src/auth/file{i}.ts", additions=20, deletions=5) for i in range(30)]
    result = _analyze(files, meta=make_meta(title="x"))
    risk = RiskEngine(_settings()).assess(result)
    assert 0 <= risk.total_score <= 100


def test_empty_pr_low_risk() -> None:
    result = _analyze([])
    risk = RiskEngine(_settings()).assess(result)
    assert risk.total_score <= 30
    assert risk.level == "LOW"


def test_security_findings_increase_risk() -> None:
    # File with hardcoded password
    files = [make_file("src/auth/config.ts", content='const password = "supersecret123";\n')]
    result = _analyze(files)
    risk = RiskEngine(_settings()).assess(result)
    sec_dim = next(d for d in risk.dimension_scores if d.dimension == "security")
    assert sec_dim.raw_score > 10  # More than "no findings"


def test_missing_tests_increase_risk() -> None:
    files = [make_file("src/payment/service.ts", additions=50, deletions=10)]
    result = _analyze(files)
    risk = RiskEngine(_settings()).assess(result)
    test_dim = next(d for d in risk.dimension_scores if d.dimension == "tests")
    assert test_dim.raw_score > 50  # High because no tests
