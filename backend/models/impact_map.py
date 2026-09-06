"""Pydantic schemas for the Impact Map (Phase 5).

The Impact Map is a visual graph representation of the PR's relevant context:
changed files, their connected dependencies, test files, and functional areas.
It reuses the Phase 2 DependencyGraph and Phase 4 risk/priority data.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from models.analysis import Severity


class NodeType(str, Enum):
    """Type of node in the impact map."""

    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    AREA = "area"  # functional area grouping node


class RiskColor(str, Enum):
    """Visual risk color category for a node."""

    RED = "red"        # Critical / High risk
    ORANGE = "orange"  # Medium risk
    YELLOW = "yellow"  # Needs attention
    GREEN = "green"    # Low risk / supporting


class ImpactNode(BaseModel):
    """A single node in the impact map."""

    id: str = Field(..., description="Unique node ID (file path or area name)")
    type: NodeType
    label: str = Field(..., description="Display label (short filename or area name)")
    file_path: Optional[str] = Field(
        default=None, description="Full repo-relative file path (None for area nodes)"
    )
    functional_area: Optional[str] = None
    changed: bool = Field(default=False, description="Whether this file was changed in the PR")
    risk_color: RiskColor = Field(default=RiskColor.GREEN)
    severity: Optional[Severity] = None
    finding_count: int = 0
    finding_ids: List[str] = Field(default_factory=list)
    priority_score: Optional[int] = Field(
        default=None, ge=0, le=100, description="Review priority score if available"
    )
    is_critical_area: bool = False
    additions: int = 0
    deletions: int = 0


class ImpactEdge(BaseModel):
    """A single edge in the impact map."""

    id: str = Field(..., description="Unique edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    kind: str = Field(
        ..., description="import | test | area"
    )


class ImpactMap(BaseModel):
    """The full impact map graph."""

    phase: str = "phase-5-impact-map"
    nodes: List[ImpactNode] = Field(default_factory=list)
    edges: List[ImpactEdge] = Field(default_factory=list)
    stats: Dict[str, int] = Field(default_factory=dict)
    legend: Dict[str, str] = Field(
        default_factory=lambda: {
            "red": "Critical / High risk",
            "orange": "Medium risk",
            "yellow": "Needs attention",
            "green": "Low risk / supporting",
        }
    )
