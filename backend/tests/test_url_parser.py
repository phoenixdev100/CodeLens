"""Unit tests for the GitHub PR URL parser."""
from __future__ import annotations

import pytest

from github.url_parser import InvalidPRURL, parse_pr_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/owner/repo/pull/123", ("owner", "repo", 123)),
        ("http://github.com/owner/repo/pull/123", ("owner", "repo", 123)),
        ("https://github.com/owner/repo/pull/123/files", ("owner", "repo", 123)),
        ("github.com/owner/repo/pull/123", ("owner", "repo", 123)),
        ("https://github.com/My-Org/My_Repo/pull/7", ("My-Org", "My_Repo", 7)),
        ("  https://github.com/owner/repo/pull/42  ", ("owner", "repo", 42)),
    ],
)
def test_parse_valid_urls(url: str, expected) -> None:
    assert parse_pr_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/issues/123",
        "https://gitlab.com/owner/repo/pull/123",
        "https://github.com/owner/repo/pull/abc",
        "https://github.com/owner/repo/pull/",
    ],
)
def test_parse_invalid_urls(url: str) -> None:
    with pytest.raises(InvalidPRURL):
        parse_pr_url(url)
