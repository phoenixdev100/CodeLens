"""Retrieve file contents from GitHub for repository context.

Fetches the raw content of files at the PR head ref via the existing
GitHubClient. Includes in-memory caching (per builder run) and size caps.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from config import Settings, get_settings
from github.client import GitHubClient
from models.context import RetrievedContent


class ContentRetriever:
    """Fetches and caches file contents from GitHub at a given ref."""

    def __init__(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        ref: str,
        settings: Optional[Settings] = None,
    ) -> None:
        self.client = client
        self.owner = owner
        self.repo = repo
        self.ref = ref
        self.settings = settings or get_settings()
        self._cache: Dict[str, RetrievedContent] = {}
        self._total_fetched = 0

    def fetch(self, path: str) -> RetrievedContent:
        """Fetch a single file's content. Returns a RetrievedContent record."""
        if path in self._cache:
            return self._cache[path]

        self._total_fetched += 1
        result = RetrievedContent(filename=path, ref=self.ref)
        try:
            content = self.client.fetch_file_content(
                self.owner, self.repo, path, self.ref
            )
        except Exception as exc:  # noqa: BLE001 - keep retrieval resilient
            result.error = str(exc)[:300]
            result.fetched = False
            self._cache[path] = result
            return result

        if content is None:
            result.fetched = False
            result.error = "File not found or unavailable at ref"
        else:
            max_chars = self.settings.max_file_content_chars
            if len(content) > max_chars:
                result.content = content[:max_chars]
                result.truncated = True
            else:
                result.content = content
                result.truncated = False
            result.fetched = True

        self._cache[path] = result
        return result

    def fetch_many(self, paths: List[str], cap: Optional[int] = None) -> Dict[str, RetrievedContent]:
        """Fetch multiple files, respecting the configured retrieval cap.

        `cap` overrides settings.max_files_to_retrieve if provided. The cap
        applies to the total number of fetches across all calls to this
        retriever (cached hits don't count).
        """
        limit = cap if cap is not None else self.settings.max_files_to_retrieve
        out: Dict[str, RetrievedContent] = {}
        for path in paths:
            if self._total_fetched >= limit:
                break
            # Cached hits don't count against the fetch budget.
            if path in self._cache:
                out[path] = self._cache[path]
                continue
            out[path] = self.fetch(path)
        return out
