"""Smart file filtering — skip unimportant files when building context.

Not all changed files are worth fetching content for. This module identifies:
  - Lock files (package-lock.json, yarn.lock, pnpm-lock.yaml)
  - Generated files (*.min.js, *.generated.ts, dist/, build/)
  - Vendored files (node_modules/, vendor/, third_party/)
  - Binary/asset files (images, fonts, PDFs, archives)
  - Large data files (*.csv, *.json data dumps)

These files are still listed in the PR (metadata + diffs), but their content
is NOT fetched from GitHub — saving API calls and reducing latency.
"""
from __future__ import annotations

import os
import re
from typing import Tuple


# Lock files — never fetch content
_LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "composer.lock", "Gemfile.lock", "Cargo.lock", "go.sum",
    "poetry.lock", "Pipfile.lock", "uv.lock",
}

# Vendored / generated directories — skip content fetch
_SKIP_DIR_PATTERNS = [
    "node_modules/", "vendor/", "third_party/", "dist/", "build/",
    ".next/", ".nuxt/", ".output/", "out/", "public/", "static/",
    "__pycache__/", ".cache/", "coverage/", ".turbo/",
]

# File extensions that are binary/assets — never fetch content
_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".class", ".jar", ".war",
    ".pyc", ".pyo", ".o", ".a",
    ".dat", ".db", ".sqlite", ".sqlite3",
}

# Generated file patterns
_GENERATED_PATTERNS = [
    re.compile(r"\.min\.js$", re.IGNORECASE),
    re.compile(r"\.min\.css$", re.IGNORECASE),
    re.compile(r"\.generated\.", re.IGNORECASE),
    re.compile(r"\.auto\.", re.IGNORECASE),
    re.compile(r"\.bundle\.", re.IGNORECASE),
    re.compile(r"^dist/", re.IGNORECASE),
    re.compile(r"^build/", re.IGNORECASE),
    re.compile(r"\.map$", re.IGNORECASE),  # source maps
]

# Large data file extensions
_DATA_EXTS = {".csv", ".sql.gz", ".json.gz"}


def is_important_file(filename: str) -> bool:
    """Determine if a file is important enough to fetch content for.

    Returns True for source, test, config, and doc files.
    Returns False for lock, generated, vendored, binary, and data files.
    """
    normalized = filename.replace("\\", "/")
    name = os.path.basename(normalized)
    name_lower = name.lower()
    _, ext = os.path.splitext(name_lower)

    # 1. Lock files — skip
    if name_lower in _LOCK_FILES:
        return False

    # 2. Binary/asset files — skip
    if ext in _BINARY_EXTS:
        return False

    # 3. Data files — skip
    if ext in _DATA_EXTS:
        return False

    # 4. Vendored/generated directories — skip
    for pattern in _SKIP_DIR_PATTERNS:
        if pattern in normalized:
            return False

    # 5. Generated file patterns — skip
    for pattern in _GENERATED_PATTERNS:
        if pattern.search(normalized):
            return False

    # 6. Very large JSON data files (heuristic by name)
    if ext == ".json" and any(kw in name_lower for kw in ("data", "dump", "export", "seed")):
        return False

    return True


def filter_important_files(filenames: list[str]) -> Tuple[list[str], list[str]]:
    """Split filenames into (important, skipped) lists.

    Important files are worth fetching content for.
    Skipped files are still tracked in the PR but their content is not fetched.
    """
    important: list[str] = []
    skipped: list[str] = []
    for f in filenames:
        if is_important_file(f):
            important.append(f)
        else:
            skipped.append(f)
    return important, skipped


def get_skip_reason(filename: str) -> str:
    """Return a human-readable reason why a file was skipped."""
    normalized = filename.replace("\\", "/")
    name = os.path.basename(normalized)
    name_lower = name.lower()
    _, ext = os.path.splitext(name_lower)

    if name_lower in _LOCK_FILES:
        return "lock file"
    if ext in _BINARY_EXTS:
        return "binary/asset file"
    if ext in _DATA_EXTS:
        return "data file"
    for pattern in _SKIP_DIR_PATTERNS:
        if pattern in normalized:
            return f"vendored/generated directory ({pattern.strip('/')})"
    for pattern in _GENERATED_PATTERNS:
        if pattern.search(normalized):
            return "generated file"
    if ext == ".json" and any(kw in name_lower for kw in ("data", "dump", "export", "seed")):
        return "data JSON file"
    return "unknown"
