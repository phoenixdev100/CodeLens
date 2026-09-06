"""Pydantic schemas for the risk engine (Phase 4).

The risk score is an MVP heuristic, NOT a scientifically validated model.
Weights are configurable. The result includes contributing factors so the
score is explainable.
"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class RiskWeights(BaseModel):
    """Configurable risk dimension weights. Should sum to 100."""

    change: int = 15
    scope: int = 15
    critical: int = 25
    security: int = 20
    quality: int = 10
    tests: int = 15

    @property
    def total(self) -> int:
        return self.change + self.scope + self.critical + self.security + self.quality + self.tests


class RiskDimensionScore(BaseModel):
    """Score for a single risk dimension."""

    dimension: str
    raw_score: int = Field(
        ..., ge=0, le=100, description="0-100 score for this dimension before weighting"
    )
    weight: int = Field(..., ge=0, le=100, description="Weight applied to this dimension")
    weighted_score: float = Field(
        ..., description="raw_score * weight / total_weight"
    )
    contributing_factors: List[str] = Field(default_factory=list)


class RiskResult(BaseModel):
    """Overall risk assessment result."""

    total_score: int = Field(..., ge=0, le=100, description="Weighted total risk score 0-100")
    level: str = Field(
        ..., description="LOW | MEDIUM | HIGH | CRITICAL"
    )
    dimension_scores: List[RiskDimensionScore] = Field(default_factory=list)
    top_contributors: List[str] = Field(
        default_factory=list,
        description="Human-readable list of the top factors driving the score",
    )
    weights: RiskWeights = Field(default_factory=RiskWeights)
    disclaimer: str = Field(
        default=(
            "This risk score is an MVP heuristic based on configurable weights, "
            "not a scientifically validated model. Use it as a prioritization aid, "
            "not as a definitive assessment."
        )
    )
