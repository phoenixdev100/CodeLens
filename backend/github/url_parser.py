"""Parse a GitHub PR URL into (owner, repo, pr_number)."""
from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import urlparse

# Accept:
#   https://github.com/owner/repo/pull/123
#   https://github.com/owner/repo/pull/123/files
#   http(s)://github.com/owner/repo/pull/123
#   github.com/owner/repo/pull/123
_PR_URL_RE = re.compile(
    r"^(?:https?://)?github\.com/(?P<owner>[A-Za-z0-9_.\-]+)/(?P<repo>[A-Za-z0-9_.\-]+)/pull/(?P<number>\d+)(?:/.*)?$",
    re.IGNORECASE,
)


class InvalidPRURL(ValueError):
    """Raised when a PR URL cannot be parsed."""


def parse_pr_url(url: str) -> Tuple[str, str, int]:
    """Return (owner, repo, pr_number) from a GitHub PR URL.

    Raises InvalidPRURL if the URL is not a valid GitHub PR URL.
    """
    if not url or not isinstance(url, str):
        raise InvalidPRURL("PR URL is required")

    cleaned = url.strip()
    # Strip trailing whitespace and normalize
    parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
    path = parsed.path or cleaned

    match = _PR_URL_RE.match(cleaned)
    if not match:
        # Try matching just the path portion
        match = _PR_URL_RE.match(path)
    if not match:
        raise InvalidPRURL(
            f"Expected a GitHub PR URL like "
            f"'https://github.com/owner/repo/pull/123', got: {url!r}"
        )

    owner = match.group("owner")
    repo = match.group("repo")
    number = int(match.group("number"))
    return owner, repo, number
