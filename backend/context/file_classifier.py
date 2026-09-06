"""Classify changed files by language and category (source/test/config/doc/other).

Focused on TypeScript/JavaScript for the MVP, but structured so additional
languages can be added later.
"""
from __future__ import annotations

import os
from typing import Tuple

from models.context import FileCategory, Language

# --- Language detection ---------------------------------------------------

_TS_EXTS = {".ts", ".tsx", ".mts", ".cts"}
_JS_EXTS = {".js", ".jsx", ".mjs", ".cjs"}
_SOURCE_EXTS = _TS_EXTS | _JS_EXTS

# Files that are config/infrastructure rather than application source.
_CONFIG_NAMES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "jsconfig.json",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    ".eslintrc.cjs",
    ".eslintrc.mjs",
    ".prettierrc",
    ".prettierrc.js",
    ".prettierrc.json",
    "vite.config.ts",
    "vite.config.js",
    "vite.config.mjs",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "webpack.config.js",
    "webpack.config.ts",
    "jest.config.js",
    "jest.config.ts",
    "vitest.config.ts",
    "vitest.config.js",
    "rollup.config.js",
    "rollup.config.mjs",
    "babel.config.js",
    "babel.config.json",
    ".babelrc",
    "turbo.json",
    "pnpm-workspace.yaml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".dockerignore",
    ".gitignore",
    ".env.example",
    ".nvmrc",
}
_CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".env", ".lock", ".config"}
_CONFIG_NAMES_LOWER = {n.lower() for n in _CONFIG_NAMES}

_DOC_EXTS = {".md", ".mdx", ".txt", ".rst", ".rst.txt"}


def detect_language(filename: str) -> Language:
    """Detect the programming language from a filename's extension."""
    _, ext = os.path.splitext(filename.lower())
    if ext in _TS_EXTS:
        return Language.TYPESCRIPT
    if ext in _JS_EXTS:
        return Language.JAVASCRIPT
    return Language.OTHER


def is_test_file(filename: str) -> bool:
    """Heuristically determine whether a file is a test file.

    Conventions covered:
      - *.test.{ts,tsx,js,jsx,mjs,cjs}
      - *.spec.{ts,tsx,js,jsx,mjs,cjs}
      - paths containing __tests__/, /test/, /tests/
      - *.stories.{ts,tsx,js,jsx} (treated as test-adjacent for MVP)
    """
    base = filename.lower().replace("\\", "/")
    name = os.path.basename(base)
    _stem, ext = os.path.splitext(name)
    if ext not in _SOURCE_EXTS:
        return False
    if name.endswith((".test.ts", ".test.tsx", ".test.js", ".test.jsx", ".test.mjs", ".test.cjs")):
        return True
    if name.endswith((".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx", ".spec.mjs", ".spec.cjs")):
        return True
    if name.endswith((".stories.ts", ".stories.tsx", ".stories.js", ".stories.jsx")):
        return True
    # Path-based conventions
    if "/__tests__/" in base or base.startswith("__tests__/"):
        return True
    if "/test/" in base or "/tests/" in base:
        return True
    # e.g. test-foo.ts or foo.test.ts already covered; cover test/foo.ts
    if base.startswith("test/") or base.startswith("tests/"):
        return True
    return False


def is_config_file(filename: str) -> bool:
    normalized = filename.replace("\\", "/")
    name = os.path.basename(normalized)
    name_lower = name.lower()
    if name in _CONFIG_NAMES or name_lower in _CONFIG_NAMES_LOWER:
        return True
    _stem, ext = os.path.splitext(name_lower)
    # Treat .config.{ts,js} as config
    if name_lower.endswith(".config.ts") or name_lower.endswith(".config.js") or name_lower.endswith(".config.mjs"):
        return True
    if ext in _CONFIG_EXTS and not is_test_file(filename):
        # package.json etc. already covered; lockfiles, yaml configs
        return True
    return False


def is_doc_file(filename: str) -> bool:
    _stem, ext = os.path.splitext(filename.lower())
    return ext in _DOC_EXTS


def classify_file(filename: str) -> Tuple[FileCategory, Language, bool, bool]:
    """Return (category, language, is_source, is_test) for a changed file."""
    language = detect_language(filename)

    if is_test_file(filename):
        return FileCategory.TEST, language, False, True

    if is_config_file(filename):
        return FileCategory.CONFIG, language, False, False

    if is_doc_file(filename):
        return FileCategory.DOC, Language.OTHER, False, False

    # Source = TS/JS non-test, non-config files
    if language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
        return FileCategory.SOURCE, language, True, False

    return FileCategory.OTHER, language, False, False
