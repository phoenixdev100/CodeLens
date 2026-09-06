"""Pydantic schema for the combined Phase 4 result.

Contains: Phase 3 analysis signals + AI insights + risk + review priority.
"""
from __future__ import annotations

from typing import Dict, Union

from pydantic import BaseModel, Field

from models.analysis import AnalysisResult
from models.ai import AIInsights
from models.priority import ReviewPriority
from models.risk import RiskResult
from models.schemas import PRMeta


class Phase4Result(BaseModel):
    """Top-level Phase 4 result: analysis + AI + risk + priority."""

    phase: str = "phase-4-ai-risk-priority"
    meta: PRMeta
    analysis: AnalysisResult = Field(..., description="Phase 3 deterministic analysis")
    ai_insights: AIInsights = Field(..., description="AI-derived interpretation")
    risk: RiskResult = Field(..., description="Explainable risk score")
    priority: ReviewPriority = Field(..., description="Reviewer-focused priority list")
    stats: Dict[str, Union[int, str]] = Field(default_factory=dict)
