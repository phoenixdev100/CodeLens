"""Build the structured AnalysisContext from raw PR data.

Orchestrates:
  1. File classification (source/test/config/doc/other)
  2. Diff parsing (per-file patches -> structured hunks)
  3. Project context (README, package.json — what the project is)
  4. Smart content retrieval (only important files, skip lock/generated/binary)
  5. Import/dependency detection (TS/JS -> dependency graph)
  6. Reverse dependency lookup (who imports the changed files)
  7. Test mapping (production source file -> related test files)
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from config import Settings, get_settings
from context.diff_parser import parse_patch
from context.file_classifier import classify_file
from context.file_filter import filter_important_files, get_skip_reason, is_important_file
from context.imports import collect_external_packages, extract_imports
from context.project_context import ProjectContextFetcher
from context.retrieval import ContentRetriever
from github.client import GitHubClient
from models.context import (
    AnalysisContext,
    DependencyGraph,
    ImportEdge,
    NormalizedFile,
    ProjectContext,
    TestMapping,
)
from models.schemas import ChangedFile, PRMeta


class ContextBuilder:
    """Transforms raw PR data into a structured AnalysisContext."""

    def __init__(
        self,
        client: GitHubClient,
        settings: Optional[Settings] = None,
    ) -> None:
        self.client = client
        self.settings = settings or get_settings()

    def build(
        self,
        meta: PRMeta,
        files: List[ChangedFile],
        raw_diff: Optional[str] = None,
    ) -> AnalysisContext:
        head_ref = meta.head_branch or "HEAD"

        # 1. Classify + 2. parse diffs
        normalized: List[NormalizedFile] = []
        parsed_diffs = []
        for f in files:
            category, language, is_source, is_test = classify_file(f.filename)
            parsed = parse_patch(f.filename, f.patch)
            if parsed is not None:
                parsed_diffs.append(parsed)
            normalized.append(
                NormalizedFile(
                    filename=f.filename,
                    status=f.status,
                    category=category,
                    language=language,
                    is_source=is_source,
                    is_test=is_test,
                    additions=f.additions,
                    deletions=f.deletions,
                    changes=f.changes,
                    previous_filename=f.previous_filename,
                    patch=parsed,
                )
            )

        # 3. Project context — fetch README, package.json to understand project
        project_context = self._fetch_project_context(meta, normalized)

        # 4. Smart content retrieval — only fetch important files
        #    Skip lock files, generated files, binary files, vendored dirs
        all_filenames = [nf.filename for nf in normalized]
        important_filenames, skipped_filenames = filter_important_files(all_filenames)

        retriever = ContentRetriever(
            self.client, meta.owner, meta.repo, head_ref, self.settings
        )
        # Only fetch content for important source/test files
        source_test_important = [
            nf.filename for nf in normalized
            if (nf.is_source or nf.is_test) and is_important_file(nf.filename)
        ]
        retrieved = retriever.fetch_many(source_test_important)

        # Attach retrieved content to normalized files.
        for nf in normalized:
            if nf.filename in retrieved:
                rc = retrieved[nf.filename]
                nf.content = rc.content
                nf.content_truncated = rc.truncated

        # 5. Import/dependency detection from retrieved source content.
        all_edges: List[ImportEdge] = []
        for nf in normalized:
            if not nf.is_source or not nf.content:
                continue
            edges = extract_imports(nf.filename, nf.content)
            all_edges.extend(edges)

        # Fetch a capped number of import-referenced files (forward deps).
        referenced_internal: List[str] = []
        seen: Set[str] = set(retrieved.keys())
        for edge in all_edges:
            if edge.is_external or not edge.resolved_path:
                continue
            rp = edge.resolved_path
            if rp not in seen and is_important_file(rp):
                referenced_internal.append(rp)
                seen.add(rp)
        # Deduplicate while preserving order.
        referenced_internal = list(dict.fromkeys(referenced_internal))
        extra = retriever.fetch_many(referenced_internal)
        retrieved.update(extra)

        # 6. Reverse dependency lookup — find files that import changed files
        #    (who uses this? = blast radius). Uses GitHub code search.
        reverse_deps = self._find_reverse_dependencies(meta, normalized)
        # Fetch a few reverse-dep files for context (shares the budget)
        reverse_to_fetch = [f for f in reverse_deps if f not in seen and is_important_file(f)]
        reverse_to_fetch = reverse_to_fetch[:5]  # cap at 5 to save API calls
        if reverse_to_fetch:
            extra_rev = retriever.fetch_many(reverse_to_fetch)
            retrieved.update(extra_rev)

        # Build dependency graph.
        nodes: Set[str] = set()
        for nf in normalized:
            if nf.is_source or nf.is_test:
                nodes.add(nf.filename)
        for edge in all_edges:
            nodes.add(edge.source_file)
            if edge.resolved_path:
                nodes.add(edge.resolved_path)
        # Add reverse deps to graph nodes
        for rd in reverse_deps:
            nodes.add(rd)
        external_pkgs = collect_external_packages(all_edges)
        dep_graph = DependencyGraph(
            nodes=sorted(nodes),
            edges=all_edges,
            external_packages=external_pkgs,
        )

        # 7. Test mapping — for each changed source file, find related tests
        test_files = [nf.filename for nf in normalized if nf.is_test]
        source_files = [nf.filename for nf in normalized if nf.is_source]
        test_mappings = _build_test_mappings(source_files, test_files)

        # Stats
        stats = {
            "files_total": len(normalized),
            "source_files": sum(1 for nf in normalized if nf.is_source),
            "test_files": sum(1 for nf in normalized if nf.is_test),
            "config_files": sum(1 for nf in normalized if nf.category.value == "config"),
            "doc_files": sum(1 for nf in normalized if nf.category.value == "doc"),
            "retrieved": sum(1 for rc in retrieved.values() if rc.fetched),
            "import_edges": len(all_edges),
            "external_packages": len(external_pkgs),
            "test_mappings_with_tests": sum(1 for tm in test_mappings if tm.has_tests),
            "files_skipped_content": len(skipped_filenames),
            "reverse_deps_found": len(reverse_deps),
        }

        return AnalysisContext(
            meta=meta,
            head_ref=head_ref,
            normalized_files=normalized,
            parsed_diffs=parsed_diffs,
            dependency_graph=dep_graph,
            test_mappings=test_mappings,
            retrieved_contents=retrieved,
            project_context=project_context,
            stats=stats,
        )

    def _fetch_project_context(
        self, meta: PRMeta, normalized: List[NormalizedFile]
    ) -> ProjectContext:
        """Fetch project-level context (README, package.json)."""
        try:
            fetcher = ProjectContextFetcher(self.client, self.settings)
            changed_paths = [nf.filename for nf in normalized]
            return fetcher.fetch(meta.owner, meta.repo, meta.head_branch or "HEAD", changed_paths)
        except Exception:
            # Project context is nice-to-have, not critical
            return ProjectContext()

    def _find_reverse_dependencies(
        self, meta: PRMeta, normalized: List[NormalizedFile]
    ) -> List[str]:
        """Find files that import the changed source files (reverse deps).

        Uses GitHub code search to find files that reference the changed files.
        This gives us the 'blast radius' — who will be affected by this change.
        """
        reverse_deps: List[str] = []
        seen: Set[str] = set()

        # Only search for reverse deps of changed source files
        source_files = [nf.filename for nf in normalized if nf.is_source and is_important_file(nf.filename)]
        # Cap at 5 searches to avoid rate limits
        for src in source_files[:5]:
            # Extract the module name (without extension) for searching
            module_name = src.rsplit("/", 1)[-1] if "/" in src else src
            module_name = module_name.rsplit(".", 1)[0] if "." in module_name else module_name

            # Search for imports of this file
            try:
                results = self.client.search_code(
                    meta.owner, meta.repo, f"import.*{module_name}", max_results=5
                )
                for path in results:
                    if path and path not in seen and path != src:
                        seen.add(path)
                        reverse_deps.append(path)
            except Exception:
                continue

        return reverse_deps[:15]  # cap total reverse deps


def _build_test_mappings(
    source_files: List[str], test_files: List[str]
) -> List[TestMapping]:
    """Map each production source file to related test files by convention.

    Conventions:
      src/foo/bar.ts -> src/foo/bar.test.ts, src/foo/bar.spec.ts
      src/foo/bar.ts -> src/foo/__tests__/bar.test.ts
      src/foo/bar.tsx -> src/foo/bar.test.tsx, ...
    Also matches any changed test file whose stem (minus .test/.spec) equals
    the source file's stem.
    """
    mappings: List[TestMapping] = []
    test_set = set(test_files)

    for src in source_files:
        related: List[str] = []
        base, ext = _split_ext(src)
        directory = src.rsplit("/", 1)[0] if "/" in src else ""

        # Same-directory test variants
        candidates = [
            f"{base}.test{ext}",
            f"{base}.spec{ext}",
            f"{base}.test.ts",
            f"{base}.test.tsx",
            f"{base}.spec.ts",
            f"{base}.spec.tsx",
        ]
        # __tests__ directory variants
        if directory:
            name_only = src.rsplit("/", 1)[1]
            stem, _ = _split_ext(name_only)
            candidates.extend(
                [
                    f"{directory}/__tests__/{stem}.test{ext}",
                    f"{directory}/__tests__/{stem}.spec{ext}",
                    f"{directory}/__tests__/{stem}.test.ts",
                    f"{directory}/__tests__/{stem}.test.tsx",
                ]
            )
        else:
            stem, _ = _split_ext(src)
            candidates.extend(
                [
                    f"__tests__/{stem}.test{ext}",
                    f"__tests__/{stem}.spec{ext}",
                ]
            )

        for c in candidates:
            if c in test_set and c not in related:
                related.append(c)

        # Also match any changed test file by stem equality (minus .test/.spec)
        src_stem = _stem_only(src)
        for tf in test_files:
            if tf in related:
                continue
            if _stem_only(tf) == src_stem:
                related.append(tf)

        mappings.append(
            TestMapping(source_file=src, related_tests=related, has_tests=bool(related))
        )

    return mappings


def _split_ext(path: str):
    idx = path.rfind(".")
    if idx == -1:
        return path, ""
    return path[:idx], path[idx:]


def _stem_only(path: str) -> str:
    """Return the file stem with test/spec suffixes removed.

    e.g. 'src/foo/bar.test.ts' -> 'src/foo/bar'
         'src/foo/bar.spec.tsx' -> 'src/foo/bar'
         'src/foo/bar.ts' -> 'src/foo/bar'
    """
    # Strip extension
    base, _ = _split_ext(path)
    # Strip .test / .spec suffix
    for suffix in (".test", ".spec", ".stories"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base
