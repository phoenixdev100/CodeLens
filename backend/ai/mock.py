"""Deterministic mock AI provider.

Produces structured AIInsights by deriving them from the AnalysisResult — no
network, no API key required. This is the fallback when OpenAI is not
configured, and is used in tests.

The mock provider is intentionally deterministic so that tests and demos work
without any external dependency.
"""
from __future__ import annotations

from typing import List

from models.ai import AIContextPayload, AIInsights, FindingExplanation, ScopeDriftReasoning


class MockAIProvider:
    """Deterministic mock AI provider (implements AIProvider)."""

    @property
    def name(self) -> str:
        return "mock"

    def analyze(self, payload: AIContextPayload) -> AIInsights:
        pr_intent = self._derive_intent(payload)
        area_interp = self._derive_area_interpretation(payload)
        scope_reasoning = self._derive_scope_reasoning(payload)
        explanations = self._derive_explanations(payload)
        risk_reasoning = self._derive_risk_reasoning(payload)

        return AIInsights(
            pr_intent=pr_intent,
            functional_area_interpretation=area_interp,
            scope_drift_reasoning=scope_reasoning,
            finding_explanations=explanations,
            risk_reasoning=risk_reasoning,
            is_ai_generated=True,
            provider=self.name,
        )

    def _derive_intent(self, p: AIContextPayload) -> str:
        parts = [f"This PR ({p.pr_title})"]
        if p.pr_author:
            parts.append(f"by {p.pr_author}")
        parts.append(f"changes {p.files_changed} file(s) (+{p.lines_added}/-{p.lines_removed} lines).")
        if p.functional_areas:
            parts.append(f"It affects: {', '.join(p.functional_areas)}.")
        if p.critical_areas:
            parts.append(f"Critical areas touched: {', '.join(p.critical_areas)}.")
        return " ".join(parts)

    def _derive_area_interpretation(self, p: AIContextPayload) -> str:
        if not p.functional_areas:
            return "No specific functional areas were detected from the changed files."
        if len(p.functional_areas) == 1:
            return f"The PR appears focused on the '{p.functional_areas[0]}' area."
        return (
            f"The PR touches {len(p.functional_areas)} functional areas: "
            f"{', '.join(p.functional_areas)}. This breadth should be reviewed for intent."
        )

    def _derive_scope_reasoning(self, p: AIContextPayload) -> ScopeDriftReasoning | None:
        if not p.scope_drift:
            return None
        return ScopeDriftReasoning(
            assessment=(
                f"Scope drift signal detected: {p.scope_drift}. "
                f"The PR may be broader than its stated intent. "
                f"This is an inference based on area mismatch and should be verified by the reviewer."
            ),
            is_inference=True,
        )

    def _derive_explanations(self, p: AIContextPayload) -> List[FindingExplanation]:
        explanations: List[FindingExplanation] = []
        for summary in p.finding_summaries[:10]:
            # Extract a pseudo finding ID from the summary (mock heuristic)
            fid = f"mock-{hash(summary) % 10000}"
            explanations.append(
                FindingExplanation(
                    finding_id=fid,
                    explanation=f"[Mock] {summary}. This finding is derived from deterministic analysis.",
                    is_inference=False,
                )
            )
        return explanations

    def _derive_risk_reasoning(self, p: AIContextPayload) -> str:
        reasons: List[str] = []
        if p.size_class in ("large", "xlarge"):
            reasons.append(f"The PR is {p.size_class} ({p.files_changed} files), which increases review difficulty.")
        if p.critical_areas:
            reasons.append(f"Critical areas are affected ({', '.join(p.critical_areas)}), elevating risk.")
        if p.scope_drift:
            reasons.append("Scope drift is detected, suggesting the PR may be broader than intended.")
        if not p.finding_summaries:
            reasons.append("No significant findings were detected, suggesting relatively low risk.")
        else:
            reasons.append(f"{len(p.finding_summaries)} finding(s) were detected by deterministic analysis.")
        return " ".join(reasons) + " (This reasoning is AI-derived and should be verified against the evidence.)"
