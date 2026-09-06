"""Pydantic schemas for review priority (Phase 4)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from models.analysis import Severity


class PriorityItem(BaseModel):
    """A single file/area in the review priority list."""

    rank: int = Field(..., ge=1, description="1-based rank (1 = review first)")
    file: str
    score: int = Field(..., ge=0, le=100, description="Priority score 0-100")
    severity: Severity = Severity.INFO
    reason: str = Field(..., description="Why this file is prioritized")
    supporting_finding_ids: List[str] = Field(
        default_factory=list,
        description="IDs of the findings that support this priority",
    )


class ReviewPriority(BaseModel):
    """Reviewer-focused priority list."""

    items: List[PriorityItem] = Field(default_factory=list)
    top_concerns: List[str] = Field(
        default_factory=list,
        description="Short human-readable summary of the top review concerns",
    )
