"""Unit tests for context/builder.py using a fake GitHub client (no network)."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from config import Settings
from context.builder import ContextBuilder, _build_test_mappings, _stem_only
from github.client import GitHubClient
from models.schemas import ChangedFile, PRMeta


class FakeGitHubClient(GitHubClient):
    """A GitHubClient stub that serves file contents from an in-memory dict."""

    def __init__(self, file_contents: Dict[str, str]) -> None:
        # Bypass real auth/init — we only override fetch_file_content.
        self._fake_contents = file_contents

    def fetch_file_content(  # type: ignore[override]
        self, owner: str, repo: str, path: str, ref: str
    ) -> Optional[str]:
        return self._fake_contents.get(path)

    # Unused by builder except fetch_file_content; keep stubs for safety.
    def fetch_all(self, pr_url: str) -> Tuple[PRMeta, List[ChangedFile], str]:  # type: ignore[override]
        raise NotImplementedError


def _make_meta() -> PRMeta:
    return PRMeta(
        owner="acme",
        repo="app",
        number=42,
        title="Payment refactor",
        state="open",
        author="alice",
        body=None,
        html_url="https://github.com/acme/app/pull/42",
        base_branch="main",
        head_branch="feature/payment",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _make_files() -> List[ChangedFile]:
    return [
        ChangedFile(
            filename="src/payment/service.ts",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
            patch="@@ -1,3 +1,5 @@\n line\n-old\n+new\n+new2\n line\n",
        ),
        ChangedFile(
            filename="src/payment/service.test.ts",
            status="modified",
            additions=2,
            deletions=0,
            changes=2,
            patch="@@ -1,2 +1,4 @@\n line\n+test1\n+test2\n line\n",
        ),
        ChangedFile(
            filename="src/utils/helpers.ts",
            status="added",
            additions=10,
            deletions=0,
            changes=10,
            patch="@@ -0,0 +1,10 @@\n+export const x = 1;\n+export const y = 2;\n",
        ),
        ChangedFile(
            filename="README.md",
            status="modified",
            additions=3,
            deletions=1,
            changes=4,
            patch="@@ -1,3 +1,5 @@\n# Title\n+new line\n line\n",
        ),
        ChangedFile(
            filename="package.json",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            patch=None,  # no patch for binary/large
        ),
    ]


def _make_settings() -> Settings:
    return Settings(
        github_app_id="",
        github_private_key_path="",
        github_installation_id="",
        github_token="",
        cors_origins="http://localhost:3000",
        max_files_per_pr=300,
        max_files_to_retrieve=25,
        max_file_content_chars=50000,
    )


def test_builder_classifies_files() -> None:
    contents = {
        "src/payment/service.ts": "import { x } from '../utils/helpers';\n",
        "src/payment/service.test.ts": "import { svc } from './service';\n",
        "src/utils/helpers.ts": "export const x = 1;\n",
    }
    client = FakeGitHubClient(contents)
    builder = ContextBuilder(client=client, settings=_make_settings())
    ctx = builder.build(_make_meta(), _make_files())

    by_name = {nf.filename: nf for nf in ctx.normalized_files}
    assert by_name["src/payment/service.ts"].is_source is True
    assert by_name["src/payment/service.ts"].is_test is False
    assert by_name["src/payment/service.test.ts"].is_test is True
    assert by_name["README.md"].category.value == "doc"
    assert by_name["package.json"].category.value == "config"


def test_builder_parses_diffs() -> None:
    client = FakeGitHubClient({})
    builder = ContextBuilder(client=client, settings=_make_settings())
    ctx = builder.build(_make_meta(), _make_files())

    by_file = {p.filename: p for p in ctx.parsed_diffs}
    assert "src/payment/service.ts" in by_file
    svc = by_file["src/payment/service.ts"]
    assert len(svc.hunks) == 1
    assert svc.added_line_numbers == [2, 3]
    assert svc.removed_line_numbers == [2]

    helpers = by_file["src/utils/helpers.ts"]
    # Patch has 2 added lines (1,2); range is computed from actual added lines
    assert helpers.new_file_line_range == (1, 2)


def test_builder_retrieves_contents() -> None:
    contents = {
        "src/payment/service.ts": "import { x } from '../utils/helpers';\n",
        "src/payment/service.test.ts": "import { svc } from './service';\n",
        "src/utils/helpers.ts": "export const x = 1;\n",
    }
    client = FakeGitHubClient(contents)
    builder = ContextBuilder(client=client, settings=_make_settings())
    ctx = builder.build(_make_meta(), _make_files())

    # Changed source/test files should be retrieved.
    assert ctx.retrieved_contents["src/payment/service.ts"].fetched is True
    assert ctx.retrieved_contents["src/payment/service.ts"].content == contents["src/payment/service.ts"]
    assert ctx.retrieved_contents["src/utils/helpers.ts"].fetched is True
    # README.md and package.json are not source/test, not retrieved.
    assert "README.md" not in ctx.retrieved_contents


def test_builder_builds_dependency_graph() -> None:
    contents = {
        "src/payment/service.ts": (
            "import { x } from '../utils/helpers';\n"
            "import React from 'react';\n"
        ),
        "src/payment/service.test.ts": "import { svc } from './service';\n",
        "src/utils/helpers.ts": "export const x = 1;\n",
    }
    client = FakeGitHubClient(contents)
    builder = ContextBuilder(client=client, settings=_make_settings())
    ctx = builder.build(_make_meta(), _make_files())

    assert "src/payment/service.ts" in ctx.dependency_graph.nodes
    assert "src/utils/helpers.ts" in ctx.dependency_graph.nodes
    assert "react" in ctx.dependency_graph.external_packages

    # The import edge from service.ts -> helpers.ts should be present and resolved.
    internal_edges = [
        e for e in ctx.dependency_graph.edges
        if e.source_file == "src/payment/service.ts" and not e.is_external
    ]
    assert any(e.resolved_path == "src/utils/helpers.ts" for e in internal_edges)


def test_builder_test_mappings() -> None:
    client = FakeGitHubClient({})
    builder = ContextBuilder(client=client, settings=_make_settings())
    ctx = builder.build(_make_meta(), _make_files())

    by_src = {tm.source_file: tm for tm in ctx.test_mappings}
    # service.ts has a matching service.test.ts
    assert by_src["src/payment/service.ts"].has_tests is True
    assert "src/payment/service.test.ts" in by_src["src/payment/service.ts"].related_tests
    # helpers.ts has no test in the changed files
    assert by_src["src/utils/helpers.ts"].has_tests is False


def test_builder_stats() -> None:
    client = FakeGitHubClient({})
    builder = ContextBuilder(client=client, settings=_make_settings())
    ctx = builder.build(_make_meta(), _make_files())

    assert ctx.stats["files_total"] == 5
    assert ctx.stats["source_files"] == 2
    assert ctx.stats["test_files"] == 1
    assert ctx.stats["config_files"] == 1
    assert ctx.stats["doc_files"] == 1
    assert ctx.stats["test_mappings_with_tests"] == 1


def test_builder_respects_retrieval_cap() -> None:
    contents = {
        "src/payment/service.ts": "import { x } from '../utils/helpers';\n",
        "src/payment/service.test.ts": "import { svc } from './service';\n",
        "src/utils/helpers.ts": "export const x = 1;\n",
    }
    client = FakeGitHubClient(contents)
    settings = _make_settings()
    settings.max_files_to_retrieve = 1  # only 1 fetch allowed
    builder = ContextBuilder(client=client, settings=settings)
    ctx = builder.build(_make_meta(), _make_files())

    # Only 1 file should be fetched (the first source/test file).
    fetched = sum(1 for rc in ctx.retrieved_contents.values() if rc.fetched)
    assert fetched == 1


def test_stem_only() -> None:
    assert _stem_only("src/foo/bar.test.ts") == "src/foo/bar"
    assert _stem_only("src/foo/bar.spec.tsx") == "src/foo/bar"
    assert _stem_only("src/foo/bar.ts") == "src/foo/bar"
    assert _stem_only("src/foo/bar.stories.tsx") == "src/foo/bar"


def test_build_test_mappings_conventions() -> None:
    sources = ["src/payment/service.ts", "src/utils/helpers.ts"]
    tests = ["src/payment/service.test.ts", "src/payment/__tests__/service.spec.ts"]
    mappings = _build_test_mappings(sources, tests)
    by_src = {tm.source_file: tm for tm in mappings}
    assert by_src["src/payment/service.ts"].has_tests is True
    assert "src/payment/service.test.ts" in by_src["src/payment/service.ts"].related_tests
    assert "src/payment/__tests__/service.spec.ts" in by_src["src/payment/service.ts"].related_tests
    assert by_src["src/utils/helpers.ts"].has_tests is False
