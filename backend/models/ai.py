"""Pydantic schemas for AI-derived insights (Phase 4).

AI output is structured and validated. AI must not replace deterministic
analysis — it provides interpretation and reasoning. Inferences that cannot
be directly verified are marked as such.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FindingExplanation(BaseModel):
    """AI explanation for a specific deterministic finding."""

    finding_id: str
    explanation: str = Field(
        ..., description="Plain-language explanation of why this finding matters"
    )
    is_inference: bool = Field(
        default=False,
        description="True if the explanation contains unverifiable AI reasoning",
    )


class ScopeDriftReasoning(BaseModel):
    """AI reasoning about scope drift."""

    assessment: str = Field(
        ..., description="Is the scope drift real, or a false positive? Why?"
    )
    is_inference: bool = True


class AIInsights(BaseModel):
    """Structured AI insights for a PR. All fields are AI-derived."""

    pr_intent: str = Field(
        ..., description="AI's understanding of what the PR is trying to accomplish"
    )
    functional_area_interpretation: str = Field(
        ..., description="AI's interpretation of the affected functional areas"
    )
    scope_drift_reasoning: Optional[ScopeDriftReasoning] = Field(
        default=None, description="AI reasoning about scope drift (if present)"
    )
    finding_explanations: List[FindingExplanation] = Field(default_factory=list)
    risk_reasoning: str = Field(
        ..., description="AI's narrative explanation of the overall risk"
    )
    is_ai_generated: bool = Field(
        default=True, description="Always True for AI output; distinguishes from deterministic"
    )
    provider: str = Field(
        ..., description="openai | mock"
    )
    disclaimer: str = Field(
        default=(
            "AI-derived insights are interpretations and may contain inaccuracies. "
            "Verify against the deterministic findings and evidence."
        )
    )


class AIContextPayload(BaseModel):
    """The compact context sent to the AI provider (NOT the whole repo)."""

    pr_title: str
    pr_body: Optional[str] = None
    pr_author: Optional[str] = None
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    size_class: str = "small"
    functional_areas: List[str] = Field(default_factory=list)
    scope_drift: Optional[str] = None
    critical_areas: List[str] = Field(default_factory=list)
    finding_summaries: List[str] = Field(
        default_factory=list,
        description="Compact one-line summaries of the top findings",
    )
