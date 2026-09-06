"""Unit tests for the AI provider abstraction (mock, openai, analyzer)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ai.analyzer import AIAnalyzer
from ai.mock import MockAIProvider
from ai.openai_provider import OpenAIProvider
from config import Settings
from models.ai import AIContextPayload, AIInsights
from models.analysis import AnalysisResult
from tests.helpers import make_context, make_file, make_meta


def _settings(provider: str = "auto", api_key: str = "") -> Settings:
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


def _make_payload() -> AIContextPayload:
    return AIContextPayload(
        pr_title="Fix payment calculation",
        pr_body="Updates the discount logic",
        pr_author="alice",
        files_changed=5,
        lines_added=120,
        lines_removed=30,
        size_class="medium",
        functional_areas=["payments", "authentication"],
        scope_drift="Unexpected areas: authentication",
        critical_areas=["payments"],
        finding_summaries=["[security/high] Hardcoded password in auth/config.ts"],
    )


# --- Mock provider tests ---

def test_mock_provider_returns_valid_insights() -> None:
    provider = MockAIProvider()
    insights = provider.analyze(_make_payload())
    assert isinstance(insights, AIInsights)
    assert insights.provider == "mock"
    assert insights.is_ai_generated is True
    assert len(insights.pr_intent) > 0
    assert len(insights.functional_area_interpretation) > 0
    assert len(insights.risk_reasoning) > 0


def test_mock_provider_scope_drift_reasoning() -> None:
    provider = MockAIProvider()
    insights = provider.analyze(_make_payload())
    assert insights.scope_drift_reasoning is not None
    assert insights.scope_drift_reasoning.is_inference is True


def test_mock_provider_no_scope_drift() -> None:
    payload = _make_payload()
    payload.scope_drift = None
    provider = MockAIProvider()
    insights = provider.analyze(payload)
    assert insights.scope_drift_reasoning is None


def test_mock_provider_finding_explanations() -> None:
    provider = MockAIProvider()
    insights = provider.analyze(_make_payload())
    assert len(insights.finding_explanations) > 0
    for fe in insights.finding_explanations:
        assert fe.finding_id
        assert fe.explanation


def test_mock_provider_empty_payload() -> None:
    payload = AIContextPayload(pr_title="Empty PR")
    provider = MockAIProvider()
    insights = provider.analyze(payload)
    assert insights.pr_intent
    assert "No specific functional areas" in insights.functional_area_interpretation


# --- OpenAI provider tests (mocked HTTP) ---

def test_openai_provider_parses_valid_response() -> None:
    provider = OpenAIProvider(api_key="fake-key", model="gpt-4o-mini")
    valid_json = json.dumps({
        "pr_intent": "Fix the payment discount calculation logic",
        "functional_area_interpretation": "The PR affects payments and authentication",
        "scope_drift_reasoning": {
            "assessment": "The auth changes may be unrelated to the payment fix",
            "is_inference": True,
        },
        "finding_explanations": [
            {"finding_id": "sec-cred-1", "explanation": "Hardcoded password is a security risk", "is_inference": False}
        ],
        "risk_reasoning": "The PR touches critical payment and auth areas",
    })
    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = valid_json
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    insights = provider.analyze(_make_payload())
    assert insights.provider == "openai"
    assert "payment" in insights.pr_intent.lower()
    assert insights.scope_drift_reasoning is not None
    assert insights.scope_drift_reasoning.is_inference is True
    assert len(insights.finding_explanations) == 1


def test_openai_provider_parses_markdown_fenced_response() -> None:
    provider = OpenAIProvider(api_key="fake-key")
    valid_json = json.dumps({
        "pr_intent": "Fix bug",
        "functional_area_interpretation": "payments",
        "scope_drift_reasoning": None,
        "finding_explanations": [],
        "risk_reasoning": "Low risk",
    })
    fenced = f"```json\n{valid_json}\n```"
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = fenced
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    insights = provider.analyze(_make_payload())
    assert insights.pr_intent == "Fix bug"


def test_openai_provider_falls_back_on_error() -> None:
    provider = OpenAIProvider(api_key="bad-key")
    # Simulate an API error
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("API error")
    provider._client = mock_client

    insights = provider.analyze(_make_payload())
    assert insights.is_ai_generated is False
    assert "AI unavailable" in insights.pr_intent
    assert "AI unavailable" in insights.risk_reasoning


def test_openai_provider_falls_back_on_invalid_json() -> None:
    provider = OpenAIProvider(api_key="fake-key")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json at all"
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    insights = provider.analyze(_make_payload())
    # Invalid JSON should trigger the degraded fallback
    assert insights.is_ai_generated is False


# --- AI Analyzer tests ---

def test_analyzer_uses_mock_when_no_key() -> None:
    settings = _settings(provider="auto", api_key="")
    analyzer = AIAnalyzer(settings)
    assert analyzer.provider.name == "mock"


def test_analyzer_uses_mock_when_forced() -> None:
    settings = _settings(provider="mock", api_key="sk-fake-key")
    analyzer = AIAnalyzer(settings)
    assert analyzer.provider.name == "mock"


def test_analyzer_uses_openai_when_key_present() -> None:
    settings = _settings(provider="auto", api_key="sk-fake-key")
    analyzer = AIAnalyzer(settings)
    assert analyzer.provider.name == "openai"


def test_analyzer_uses_openai_when_forced_with_key() -> None:
    settings = _settings(provider="openai", api_key="sk-fake-key")
    analyzer = AIAnalyzer(settings)
    assert analyzer.provider.name == "openai"


def test_analyzer_builds_compact_payload() -> None:
    settings = _settings(provider="mock")
    analyzer = AIAnalyzer(settings)
    files = [make_file("src/payment/service.ts"), make_file("src/auth/session.ts")]
    ctx = make_context(files, meta=make_meta(title="Fix payment"))
    # Run Phase 3 analysis to get an AnalysisResult
    from analysis.engine import AnalysisEngine
    result = AnalysisEngine(settings).analyze(ctx)
    payload = analyzer._build_payload(result)
    assert payload.pr_title == "Fix payment"
    assert "payments" in payload.functional_areas
    assert payload.files_changed == 2
    # Payload should NOT contain raw file contents
    assert not hasattr(payload, "file_contents")


def test_analyzer_caps_findings_in_payload() -> None:
    settings = _settings(provider="mock")
    settings.ai_max_context_findings = 2
    analyzer = AIAnalyzer(settings)
    # Create many files to generate many findings
    files = [make_file(f"src/auth/file{i}.ts") for i in range(10)]
    ctx = make_context(files)
    from analysis.engine import AnalysisEngine
    result = AnalysisEngine(settings).analyze(ctx)
    payload = analyzer._build_payload(result)
    assert len(payload.finding_summaries) <= 2


def test_analyzer_full_flow_with_mock() -> None:
    settings = _settings(provider="mock")
    analyzer = AIAnalyzer(settings)
    files = [make_file("src/payment/service.ts"), make_file("src/auth/session.ts")]
    ctx = make_context(files, meta=make_meta(title="Fix payment"))
    from analysis.engine import AnalysisEngine
    result = AnalysisEngine(settings).analyze(ctx)
    insights = analyzer.analyze(result)
    assert insights.provider == "mock"
    assert insights.is_ai_generated is True
    assert "payment" in insights.pr_intent.lower()
