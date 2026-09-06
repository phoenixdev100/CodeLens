"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    pr_url: str = Field(..., description="Full GitHub PR URL")


class PRMeta(BaseModel):
    owner: str
    repo: str
    number: int
    title: str
    state: str
    author: Optional[str] = None
    body: Optional[str] = None
    html_url: str
    base_branch: Optional[str] = None
    head_branch: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChangedFile(BaseModel):
    filename: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    previous_filename: Optional[str] = None


class DiffSummary(BaseModel):
    total_additions: int
    total_deletions: int
    total_changes: int
    files_changed: int


class AnalyzeResponse(BaseModel):
    """Phase 1 response: raw PR data only. Analysis signals come in later phases."""

    phase: str = "phase-1-github-foundation"
    meta: PRMeta
    diff_summary: DiffSummary
    files: List[ChangedFile]
    raw_diff: Optional[str] = Field(
        default=None,
        description="Unified diff for the whole PR (truncated if very large)",
    )


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    auth_mode: str  # "github-app" | "pat" | "none"
