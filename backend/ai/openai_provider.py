"""OpenAI AI provider.

Calls the OpenAI chat completions API with structured JSON output. Validates
the response with Pydantic. On any error, falls back to a degraded AIInsights
that indicates the failure (never raises — the pipeline must stay robust).
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from models.ai import AIContextPayload, AIInsights, FindingExplanation, ScopeDriftReasoning
from ai.prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI-based AI provider (implements AIProvider)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model
        self._client = None  # lazy init

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def analyze(self, payload: AIContextPayload) -> AIInsights:
        try:
            return self._call_openai(payload)
        except Exception as exc:
            logger.warning("OpenAI provider failed, returning degraded insights: %s", exc)
            return self._degraded(payload, str(exc))

    def _call_openai(self, payload: AIContextPayload) -> AIInsights:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": build_user_prompt(payload)},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        content = response.choices[0].message.content or ""
        return self._parse_response(content, payload)

    def _parse_response(self, content: str, payload: AIContextPayload) -> AIInsights:
        # Strip markdown code fences if present
        text = content.strip()
        if text.startswith("```"):
            # Remove first line (```json or ```) and last ```
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        data = json.loads(text)
        return self._validate(data, payload)

    def _validate(self, data: dict, payload: AIContextPayload) -> AIInsights:
        # Map the JSON to AIInsights with safe defaults
        scope_data = data.get("scope_drift_reasoning")
        scope_reasoning: Optional[ScopeDriftReasoning] = None
        if isinstance(scope_data, dict):
            scope_reasoning = ScopeDriftReasoning(
                assessment=scope_data.get("assessment", ""),
                is_inference=scope_data.get("is_inference", True),
            )

        explanations = []
        for fe in data.get("finding_explanations", []) or []:
            if isinstance(fe, dict):
                explanations.append(
                    FindingExplanation(
                        finding_id=fe.get("finding_id", "unknown"),
                        explanation=fe.get("explanation", ""),
                        is_inference=fe.get("is_inference", False),
                    )
                )

        return AIInsights(
            pr_intent=data.get("pr_intent", ""),
            functional_area_interpretation=data.get("functional_area_interpretation", ""),
            scope_drift_reasoning=scope_reasoning,
            finding_explanations=explanations,
            risk_reasoning=data.get("risk_reasoning", ""),
            is_ai_generated=True,
            provider=self.name,
        )

    def _degraded(self, payload: AIContextPayload, error: str) -> AIInsights:
        """Return a minimal AIInsights when the OpenAI call fails."""
        return AIInsights(
            pr_intent=f"[AI unavailable] {payload.pr_title}",
            functional_area_interpretation=(
                f"[AI unavailable] Areas: {', '.join(payload.functional_areas) or 'none'}"
            ),
            scope_drift_reasoning=None,
            finding_explanations=[],
            risk_reasoning=(
                f"[AI unavailable — {error[:200]}] "
                "Risk reasoning could not be generated. Rely on deterministic findings."
            ),
            is_ai_generated=False,
            provider=self.name,
            disclaimer=(
                "AI insights were unavailable due to an error. "
                "This is a degraded response; rely on the deterministic analysis."
            ),
        )
