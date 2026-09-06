"""Shared heuristics for detecting functional areas from file paths and content.

Functional areas are extensible. Detection is intentionally conservative:
we prefer path-based signals over content-based ones, and label the detection
method so the UI can explain *why* an area was inferred.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Area name -> list of path substring patterns (lowercased, slash-normalized).
# Order matters only for readability; matching is exact-substring on path.
AREA_PATH_PATTERNS: Dict[str, List[str]] = {
    "authentication": ["auth", "login", "session", "token", "password", "oauth", "saml", "jwt"],
    "authorization": ["permission", "rbac", "acl", "policy", "role", "authorize", "access-control"],
    "payments": ["payment", "checkout", "billing", "invoice", "refund", "transaction", "stripe", "paypal"],
    "database": ["db", "database", "migration", "schema", "sql", "prisma", "drizzle", "knex", "sequelize", "typeorm"],
    "infrastructure": ["infra", "docker", "kubernetes", "k8s", "terraform", "ansible", "ci", "cd", "deploy", "pipeline", ".github/workflows"],
    "notifications": ["notification", "notify", "email", "mailer", "push", "webhook", "sms", "twilio", "sendgrid"],
    "api": ["api", "route", "controller", "handler", "endpoint", "rest", "graphql"],
    "frontend": ["frontend", "ui", "component", "page", "view", "client", "src/app", "src/components", "src/pages"],
    "backend": ["backend", "server", "worker", "cron", "queue", "src/server", "src/services", "/services/"],
    "sensitive-data": ["secret", "key", "credential", "crypto", "encrypt", "decrypt", "pii", "gdpr"],
}

# Keyword patterns used for content-based detection (fallback).
AREA_KEYWORD_PATTERNS: Dict[str, List[str]] = {
    "authentication": ["authenticate", "login", "jwt", "session", "password", "oauth"],
    "authorization": ["authorize", "permission", "rbac", "can(", "hasrole", "isadmin"],
    "payments": ["payment", "charge", "refund", "stripe", "checkout", "billing"],
    "sensitive-data": ["encrypt", "decrypt", "secret", "apikey", "api_key", "password"],
}


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lower()


def detect_areas_from_path(filename: str) -> List[str]:
    """Return functional areas detected from a file path."""
    norm = normalize_path(filename)
    found: List[str] = []
    for area, patterns in AREA_PATH_PATTERNS.items():
        for p in patterns:
            if p in norm:
                if area not in found:
                    found.append(area)
                break
    return found


def detect_areas_from_content(filename: str, content: str) -> List[str]:
    """Return functional areas detected from file content (keyword fallback)."""
    if not content:
        return []
    lower = content.lower()
    found: List[str] = []
    for area, keywords in AREA_KEYWORD_PATTERNS.items():
        for kw in keywords:
            if kw in lower:
                if area not in found:
                    found.append(area)
                break
    return found


def detect_areas(filename: str, content: str | None = None) -> Tuple[List[str], str]:
    """Detect functional areas for a file.

    Returns (areas, detected_by) where detected_by is 'path', 'keyword', or 'none'.
    Path-based detection takes precedence.
    """
    path_areas = detect_areas_from_path(filename)
    if path_areas:
        return path_areas, "path"
    if content:
        content_areas = detect_areas_from_content(filename, content)
        if content_areas:
            return content_areas, "keyword"
    return [], "none"


def infer_stated_areas(title: str, body: str | None = None) -> List[str]:
    """Infer intended functional areas from the PR title and body text."""
    text = f"{title} {body or ''}".lower()
    found: List[str] = []
    for area, keywords in AREA_KEYWORD_PATTERNS.items():
        for kw in keywords:
            if kw in text:
                if area not in found:
                    found.append(area)
                break
    # Also match path-style words in the title (e.g. "payment", "auth")
    for area, patterns in AREA_PATH_PATTERNS.items():
        for p in patterns:
            if p in text:
                if area not in found:
                    found.append(area)
                break
    return found
