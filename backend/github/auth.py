"""GitHub authentication.

Two modes, in priority order:
1. GitHub App: build a JWT from the App's private key, exchange it for an
   installation access token.
2. PAT fallback: use GITHUB_TOKEN directly (local dev only).

Tokens are short-lived and cached in-memory for their stated lifetime.
"""
from __future__ import annotations

import time
from typing import Optional

import httpx
import jwt

from config import Settings, get_settings

GITHUB_API_BASE = "https://api.github.com"
# Installation tokens last ~1h; we refresh slightly before expiry.
_TOKEN_REFRESH_MARGIN_SECONDS = 60
_JWT_LIFETIME_SECONDS = 9 * 60  # GitHub allows max 10 min


class GitHubAuthError(RuntimeError):
    """Raised when GitHub authentication fails."""


class GitHubAuthenticator:
    """Resolves a usable GitHub API bearer token."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._cached_installation_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    @property
    def mode(self) -> str:
        if self.settings.has_github_app:
            return "github-app"
        if self.settings.has_pat:
            return "pat"
        return "none"

    def get_token(self) -> str:
        if self.settings.has_github_app:
            return self._get_installation_token()
        if self.settings.has_pat:
            return self.settings.github_token
        raise GitHubAuthError(
            "No GitHub credentials configured. Set either GitHub App credentials "
            "(GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH, GITHUB_INSTALLATION_ID) or "
            "GITHUB_TOKEN in backend/.env."
        )

    # --- GitHub App flow ---

    def _build_app_jwt(self) -> str:
        pem = self.settings.private_key_pem
        if not pem:
            raise GitHubAuthError(
                "GitHub App private key not found. Set GITHUB_PRIVATE_KEY_PATH or "
                "GITHUB_PRIVATE_KEY."
            )
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + _JWT_LIFETIME_SECONDS,
            "iss": self.settings.github_app_id,
        }
        return jwt.encode(payload, pem, algorithm="RS256")

    def _get_installation_token(self) -> str:
        # Return cached token if still valid.
        if (
            self._cached_installation_token
            and time.time() < self._token_expires_at - _TOKEN_REFRESH_MARGIN_SECONDS
        ):
            return self._cached_installation_token

        app_jwt = self._build_app_jwt()
        installation_id = self.settings.github_installation_id
        url = f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            resp = httpx.post(url, headers=headers, timeout=15.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GitHubAuthError(
                f"Failed to create installation access token: {exc}"
            ) from exc

        data = resp.json()
        token = data.get("token")
        expires_at_str = data.get("expires_at")  # ISO 8601 UTC
        if not token:
            raise GitHubAuthError("Installation token response missing 'token' field.")

        # Parse expiry; fall back to 55 min if unusable.
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            self._token_expires_at = dt.timestamp()
        except Exception:
            self._token_expires_at = time.time() + 55 * 60

        self._cached_installation_token = token
        return token
