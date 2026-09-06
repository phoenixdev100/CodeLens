"""AI Analyzer: orchestrates provider selection and builds the context payload.

Selects the AI provider based on config (OpenAI if key present, else mock).
Builds a compact AIContextPayload from the AnalysisResult — NOT the whole repo.
"""
from __future__ import annotations

from typing import List

from config import Settings, get_settings
from models.ai import AIContextPayload, AIInsights
from models.analysis import AnalysisResult
from ai.mock import MockAIProvider
from ai.openai_provider import OpenAIProvider
from ai.gemini_provider import GeminiProvider
from ai.provider import AIProvider


class AIAnalyzer:
    """Builds AI context and calls the configured provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider = self._select_provider()

    def _select_provider(self) -> AIProvider:
        mode = self.settings.effective_ai_provider
        if mode == "openai" and self.settings.has_openai:
            return OpenAIProvider(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
            )
        if mode == "gemini" and self.settings.has_gemini:
            return GeminiProvider(
                api_key=self.settings.gemini_api_key,
                model=self.settings.gemini_model,
            )
        return MockAIProvider()

    def analyze(self, result: AnalysisResult) -> AIInsights:
        payload = self._build_payload(result)
        return self.provider.analyze(payload)

    def _build_payload(self, result: AnalysisResult) -> AIContextPayload:
        # Compact finding summaries (capped)
        summaries: List[str] = []
        for f in result.all_findings[: self.settings.ai_max_context_findings]:
            loc = f" ({f.file})" if f.file else ""
            summaries.append(f"[{f.category}/{f.severity.value}] {f.title}{loc}")

        scope_drift_text = None
        sd = result.change.scope_drift
        if sd.has_drift:
            scope_drift_text = sd.reason or (
                f"Unexpected areas: {', '.join(sd.unexpected_areas)}"
            )

        critical_areas = [a.kind for a in result.critical.areas]
        functional_areas = [a.name for a in result.change.functional_areas]

        return AIContextPayload(
            pr_title=result.meta.title,
            pr_body=result.meta.body,
            pr_author=result.meta.author,
            files_changed=result.change.files_changed,
            lines_added=result.change.lines_added,
            lines_removed=result.change.lines_removed,
            size_class=result.change.size_class,
            functional_areas=functional_areas,
            scope_drift=scope_drift_text,
            critical_areas=critical_areas,
            finding_summaries=summaries,
        )
