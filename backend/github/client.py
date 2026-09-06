"""GitHub API client: fetch PR metadata, changed files, and diff."""
from __future__ import annotations

from typing import List, Optional, Tuple

import httpx

from config import Settings, get_settings
from github.auth import GitHubAuthenticator
from github.url_parser import parse_pr_url
from models.schemas import ChangedFile, DiffSummary, PRMeta

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


class GitHubAPIError(RuntimeError):
    """Raised when a GitHub API call fails."""

    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    """Thin wrapper around the GitHub REST API for PR data."""

    def __init__(
        self,
        authenticator: Optional[GitHubAuthenticator] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.authenticator = authenticator or GitHubAuthenticator(self.settings)

    def _headers(self, accept_diff: bool = False) -> dict:
        token = self.authenticator.get_token()
        headers = dict(DEFAULT_HEADERS)
        headers["Authorization"] = f"Bearer {token}"
        if accept_diff:
            headers["Accept"] = "application/vnd.github.v3.diff"
        return headers

    def fetch_pr(self, owner: str, repo: str, number: int) -> PRMeta:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{number}"
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=20.0)
        except httpx.HTTPError as exc:
            raise GitHubAPIError(f"Network error fetching PR: {exc}") from exc

        if resp.status_code == 404:
            raise GitHubAPIError(
                f"PR #{number} not found in {owner}/{repo} (or token lacks access).",
                status_code=404,
            )
        if resp.status_code == 401:
            raise GitHubAPIError(
                "GitHub authentication failed (401). Check your credentials.",
                status_code=401,
            )
        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        return PRMeta(
            owner=owner,
            repo=repo,
            number=number,
            title=data.get("title", ""),
            state=data.get("state", ""),
            author=(data.get("user") or {}).get("login"),
            body=data.get("body"),
            html_url=data.get("html_url", ""),
            base_branch=(data.get("base") or {}).get("ref"),
            head_branch=(data.get("head") or {}).get("ref"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def fetch_files(self, owner: str, repo: str, number: int) -> List[ChangedFile]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{number}/files"
        files: List[ChangedFile] = []
        page = 1
        per_page = 100
        max_files = self.settings.max_files_per_pr

        while True:
            try:
                resp = httpx.get(
                    url,
                    headers=self._headers(),
                    params={"page": page, "per_page": per_page},
                    timeout=30.0,
                )
            except httpx.HTTPError as exc:
                raise GitHubAPIError(f"Network error fetching PR files: {exc}") from exc

            if resp.status_code >= 400:
                raise GitHubAPIError(
                    f"GitHub API error {resp.status_code} fetching files: {resp.text[:200]}",
                    status_code=resp.status_code,
                )

            page_data = resp.json()
            if not page_data:
                break

            for item in page_data:
                files.append(
                    ChangedFile(
                        filename=item.get("filename", ""),
                        status=item.get("status", ""),
                        additions=item.get("additions", 0),
                        deletions=item.get("deletions", 0),
                        changes=item.get("changes", 0),
                        patch=item.get("patch"),
                        previous_filename=item.get("previous_filename"),
                    )
                )
                if len(files) >= max_files:
                    break

            if len(page_data) < per_page or len(files) >= max_files:
                break
            page += 1

        return files

    def fetch_raw_diff(self, owner: str, repo: str, number: int) -> str:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{number}"
        try:
            resp = httpx.get(url, headers=self._headers(accept_diff=True), timeout=30.0)
        except httpx.HTTPError as exc:
            raise GitHubAPIError(f"Network error fetching diff: {exc}") from exc

        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error {resp.status_code} fetching diff: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        return resp.text

    def fetch_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> Optional[str]:
        """Fetch a single file's raw content at a given ref.

        Returns None if the file does not exist (404) or is too large to be
        served as raw content. Raises GitHubAPIError for other failures.
        Uses the raw content media type.
        """
        # Use the raw media type to get plain text directly.
        headers = dict(DEFAULT_HEADERS)
        token = self.authenticator.get_token()
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/vnd.github.raw+json"
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
        try:
            resp = httpx.get(
                url, headers=headers, params={"ref": ref}, timeout=20.0
            )
        except httpx.HTTPError as exc:
            raise GitHubAPIError(f"Network error fetching file {path}: {exc}") from exc

        if resp.status_code == 404:
            return None
        if resp.status_code == 403:
            # Often "too large" or rate limit; treat as unavailable for MVP.
            return None
        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error {resp.status_code} fetching {path}: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        return resp.text

    def fetch_all(self, pr_url: str) -> Tuple[PRMeta, List[ChangedFile], str]:
        """Parse URL and fetch PR meta, files, and raw diff in one call."""
        owner, repo, number = parse_pr_url(pr_url)
        meta = self.fetch_pr(owner, repo, number)
        files = self.fetch_files(owner, repo, number)
        raw_diff = self.fetch_raw_diff(owner, repo, number)
        return meta, files, raw_diff

    def search_code(
        self,
        owner: str,
        repo: str,
        query: str,
        max_results: int = 10,
    ) -> List[str]:
        """Search for code in a repo using GitHub's code search API.

        Returns a list of file paths that match the query.
        Used for reverse dependency lookup (finding files that import changed files).
        """
        url = f"{GITHUB_API_BASE}/search/code"
        # Search within the repo for the query string
        q = f"{query} repo:{owner}/{repo}"
        try:
            resp = httpx.get(
                url,
                headers=self._headers(),
                params={"q": q, "per_page": min(max_results, 100)},
                timeout=20.0,
            )
        except httpx.HTTPError:
            return []

        if resp.status_code != 200:
            return []

        data = resp.json()
        items = data.get("items", [])
        return [item.get("path", "") for item in items[:max_results] if item.get("path")]


def summarize_diff(files: List[ChangedFile]) -> DiffSummary:
    total_add = sum(f.additions for f in files)
    total_del = sum(f.deletions for f in files)
    return DiffSummary(
        total_additions=total_add,
        total_deletions=total_del,
        total_changes=total_add + total_del,
        files_changed=len(files),
    )
