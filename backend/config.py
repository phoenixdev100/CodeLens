"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GitHub App credentials
    github_app_id: str = Field(default="", description="GitHub App ID (numeric string)")
    github_private_key_path: str = Field(
        default="", description="Path to the App's private key (.pem)"
    )
    github_private_key: str = Field(
        default="", description="Raw PEM private key content (alternative to path)"
    )
    github_installation_id: str = Field(
        default="", description="Installation ID for the App"
    )

    # PAT fallback (local dev)
    github_token: str = Field(default="", description="Personal Access Token fallback")

    # Server
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated allowed CORS origins",
    )

    # Safety caps
    max_files_per_pr: int = Field(default=300, ge=1, le=3000)

    # Phase 2 — repository context retrieval caps
    max_files_to_retrieve: int = Field(
        default=25, ge=0, le=500,
        description="Max number of file contents to fetch from GitHub for context",
    )
    max_file_content_chars: int = Field(
        default=50_000, ge=100, le=2_000_000,
        description="Per-file content char cap (truncated beyond this)",
    )

    # Phase 3 — analysis thresholds (tunable heuristics)
    large_pr_file_count: int = Field(
        default=20, ge=1, le=10_000,
        description="File count at/above which a PR is considered 'large'",
    )
    xlarge_pr_file_count: int = Field(
        default=50, ge=1, le=10_000,
        description="File count at/above which a PR is considered 'xlarge'",
    )
    large_pr_line_count: int = Field(
        default=500, ge=1, le=1_000_000,
        description="Total changed lines at/above which a PR is considered 'large'",
    )
    large_function_line_count: int = Field(
        default=80, ge=10, le=10_000,
        description="Line count at/above which a function is considered 'very large'",
    )
    high_nesting_threshold: int = Field(
        default=4, ge=2, le=20,
        description="Nesting depth at/above which added code is flagged as high-nesting",
    )

    # Phase 4 — AI provider
    openai_api_key: str = Field(default="", description="OpenAI API key (empty = use mock provider)")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    ai_provider: str = Field(
        default="auto",
        description="auto | openai | gemini | mock. 'auto' uses openai if key is set, else mock.",
    )
    ai_max_context_findings: int = Field(
        default=30, ge=1, le=200,
        description="Max findings to include in the AI context payload",
    )

    # Phase 4 — Gemini AI provider (free tier alternative)
    gemini_api_key: str = Field(default="", description="Google Gemini API key (empty = not used)")
    gemini_model: str = Field(default="gemini-1.5-pro", description="Gemini model name")

    # Phase 4 — risk engine weights (must sum to 100)
    risk_weight_change: int = Field(default=15, ge=0, le=100)
    risk_weight_scope: int = Field(default=15, ge=0, le=100)
    risk_weight_critical: int = Field(default=25, ge=0, le=100)
    risk_weight_security: int = Field(default=20, ge=0, le=100)
    risk_weight_quality: int = Field(default=10, ge=0, le=100)
    risk_weight_tests: int = Field(default=15, ge=0, le=100)

    @field_validator("github_app_id", "github_installation_id", "github_token", "openai_api_key", "gemini_api_key", mode="before")
    @classmethod
    def _strip(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_github_app(self) -> bool:
        return bool(self.github_app_id and self.github_installation_id and self.private_key_pem)

    @property
    def has_pat(self) -> bool:
        return bool(self.github_token)

    @property
    def private_key_pem(self) -> str:
        """Resolve the private key PEM content from env or file path."""
        if self.github_private_key:
            return self.github_private_key
        if self.github_private_key_path:
            path = Path(self.github_private_key_path)
            if path.is_file():
                return path.read_text(encoding="utf-8")
        return ""

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def effective_ai_provider(self) -> str:
        """Resolve which AI provider to use: 'openai', 'gemini', or 'mock'."""
        if self.ai_provider == "mock":
            return "mock"
        if self.ai_provider == "openai":
            return "openai"
        if self.ai_provider == "gemini":
            return "gemini"
        # auto — prefer openai, then gemini, then mock
        if self.has_openai:
            return "openai"
        if self.has_gemini:
            return "gemini"
        return "mock"

    @property
    def risk_weights(self) -> dict:
        """Return risk weights as a dict."""
        return {
            "change": self.risk_weight_change,
            "scope": self.risk_weight_scope,
            "critical": self.risk_weight_critical,
            "security": self.risk_weight_security,
            "quality": self.risk_weight_quality,
            "tests": self.risk_weight_tests,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
