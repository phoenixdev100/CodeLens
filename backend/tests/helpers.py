"""Shared helpers for building synthetic AnalysisContext in tests."""
from __future__ import annotations

from typing import List, Optional

from models.context import (
    AnalysisContext,
    DependencyGraph,
    DiffHunk,
    FileCategory,
    Language,
    NormalizedFile,
    ParsedPatch,
    TestMapping,
)
from models.schemas import PRMeta


def make_meta(
    title: str = "Fix checkout discount calculation",
    body: Optional[str] = "This PR fixes the checkout discount calculation by updating the payment service to handle edge cases properly. Added tests for the new logic.",
) -> PRMeta:
    return PRMeta(
        owner="acme",
        repo="app",
        number=42,
        title=title,
        state="open",
        author="alice",
        body=body,
        html_url="https://github.com/acme/app/pull/42",
        base_branch="main",
        head_branch="feature/x",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def make_file(
    filename: str,
    status: str = "modified",
    additions: int = 5,
    deletions: int = 2,
    category: FileCategory = FileCategory.SOURCE,
    language: Language = Language.TYPESCRIPT,
    is_source: bool = True,
    is_test: bool = False,
    content: Optional[str] = None,
    patch_text: Optional[str] = None,
) -> NormalizedFile:
    patch = _parse_simple_patch(filename, patch_text) if patch_text else None
    return NormalizedFile(
        filename=filename,
        status=status,
        category=category,
        language=language,
        is_source=is_source,
        is_test=is_test,
        additions=additions,
        deletions=deletions,
        changes=additions + deletions,
        patch=patch,
        content=content,
    )


def make_context(
    files: List[NormalizedFile],
    meta: Optional[PRMeta] = None,
    test_mappings: Optional[List[TestMapping]] = None,
) -> AnalysisContext:
    return AnalysisContext(
        meta=meta or make_meta(),
        head_ref="feature/x",
        normalized_files=files,
        parsed_diffs=[f.patch for f in files if f.patch],
        dependency_graph=DependencyGraph(),
        test_mappings=test_mappings or [],
        retrieved_contents={},
        stats={},
    )


def _parse_simple_patch(filename: str, patch_text: str) -> ParsedPatch:
    """Minimal patch parser for test fixtures (reuses the real parser)."""
    from context.diff_parser import parse_patch

    result = parse_patch(filename, patch_text)
    if result is None:
        return ParsedPatch(filename=filename)
    return result
