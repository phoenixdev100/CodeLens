"""Pydantic schemas for the structured repository context (Phase 2).

The AnalysisContext is the normalized input consumed by the Phase 3 analysis
engine. It is built from the raw PR data fetched in Phase 1.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from models.schemas import PRMeta


class FileCategory(str, Enum):
    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    DOC = "doc"
    OTHER = "other"


class Language(str, Enum):
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    OTHER = "other"


class DiffHunk(BaseModel):
    """A single @@ ... @@ hunk from a unified diff patch."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str] = Field(
        default_factory=list,
        description="Raw hunk body lines (including +/-/space prefixes)",
    )
    added_line_numbers: List[int] = Field(
        default_factory=list,
        description="1-based line numbers in the new file that were added",
    )
    removed_line_numbers: List[int] = Field(
        default_factory=list,
        description="1-based line numbers in the old file that were removed",
    )


class ParsedPatch(BaseModel):
    """Result of parsing one file's unified-diff patch."""

    filename: str
    hunks: List[DiffHunk] = Field(default_factory=list)
    added_line_numbers: List[int] = Field(
        default_factory=list,
        description="All added line numbers across hunks (new file coords)",
    )
    removed_line_numbers: List[int] = Field(
        default_factory=list,
        description="All removed line numbers across hunks (old file coords)",
    )
    new_file_line_range: Optional[tuple[int, int]] = Field(
        default=None,
        description="Approx [first, last] line range in the new file that this patch touches",
    )


class NormalizedFile(BaseModel):
    """A changed file classified and normalized for analysis."""

    filename: str
    status: str
    category: FileCategory
    language: Language
    is_source: bool
    is_test: bool
    additions: int
    deletions: int
    changes: int
    previous_filename: Optional[str] = None
    patch: Optional[ParsedPatch] = None
    content: Optional[str] = Field(
        default=None,
        description="Retrieved file content (truncated to max_file_content_chars)",
    )
    content_truncated: bool = False


class ImportEdge(BaseModel):
    """A single import/require relationship from a source file."""

    source_file: str
    raw_specifier: str
    resolved_path: Optional[str] = Field(
        default=None,
        description="Repo-relative path if resolvable, else None (external)",
    )
    is_external: bool = False
    import_kind: str = Field(
        default="import",
        description="import | require | export-from | dynamic-import",
    )


class DependencyGraph(BaseModel):
    """Best-effort dependency graph for the changed TS/JS files."""

    nodes: List[str] = Field(default_factory=list, description="File paths in the graph")
    edges: List[ImportEdge] = Field(default_factory=list)
    external_packages: List[str] = Field(
        default_factory=list,
        description="Distinct bare specifiers (e.g. react, lodash) referenced",
    )


class TestMapping(BaseModel):
    """Mapping between a production source file and its related test files."""

    # Prevent pytest from trying to collect this Pydantic model as a test class.
    __test__ = False

    source_file: str
    related_tests: List[str] = Field(default_factory=list)
    has_tests: bool = False


class RetrievedContent(BaseModel):
    """A retrieved file's content with metadata."""

    filename: str
    ref: str
    content: Optional[str] = None
    truncated: bool = False
    fetched: bool = Field(
        default=False,
        description="False if the file could not be fetched (e.g. deleted, too large)",
    )
    error: Optional[str] = None


class ProjectContext(BaseModel):
    """High-level project context — what the project is, tech stack, key dirs.

    Built from README, package.json, pyproject.toml, etc. Helps the AI and
    reviewers understand the project without fetching the entire repo.
    """

    name: str = ""
    description: str = ""
    language: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    key_directories: List[str] = Field(default_factory=list)
    readme_excerpt: str = Field(
        default="",
        description="First ~2000 chars of README for project understanding",
    )
    package_info: Dict[str, str] = Field(
        default_factory=dict,
        description="Key fields from package.json/pyproject.toml (name, version, framework)",
    )


class AnalysisContext(BaseModel):
    """Top-level structured context consumed by the analysis engine (Phase 3+)."""

    phase: str = "phase-2-repository-context"
    meta: PRMeta
    head_ref: Optional[str] = None
    normalized_files: List[NormalizedFile] = Field(default_factory=list)
    parsed_diffs: List[ParsedPatch] = Field(default_factory=list)
    dependency_graph: DependencyGraph = Field(default_factory=DependencyGraph)
    test_mappings: List[TestMapping] = Field(default_factory=list)
    retrieved_contents: Dict[str, RetrievedContent] = Field(default_factory=dict)
    project_context: ProjectContext = Field(default_factory=ProjectContext)
    stats: Dict[str, int] = Field(
        default_factory=dict,
        description="Quick counts: source_files, test_files, retrieved, imports, etc.",
    )
