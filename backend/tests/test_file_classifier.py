"""Unit tests for context/file_classifier.py."""
from __future__ import annotations

import pytest

from context.file_classifier import (
    classify_file,
    detect_language,
    is_config_file,
    is_doc_file,
    is_test_file,
)
from models.context import FileCategory, Language


@pytest.mark.parametrize(
    "filename,expected_lang",
    [
        ("src/foo.ts", Language.TYPESCRIPT),
        ("src/foo.tsx", Language.TYPESCRIPT),
        ("src/foo.mts", Language.TYPESCRIPT),
        ("src/foo.cts", Language.TYPESCRIPT),
        ("src/foo.js", Language.JAVASCRIPT),
        ("src/foo.jsx", Language.JAVASCRIPT),
        ("src/foo.mjs", Language.JAVASCRIPT),
        ("src/foo.cjs", Language.JAVASCRIPT),
        ("README.md", Language.OTHER),
        ("package.json", Language.OTHER),
        ("schema.sql", Language.OTHER),
    ],
)
def test_detect_language(filename: str, expected_lang: Language) -> None:
    assert detect_language(filename) == expected_lang


@pytest.mark.parametrize(
    "filename",
    [
        "src/foo.test.ts",
        "src/foo.test.tsx",
        "src/foo.spec.ts",
        "src/foo.spec.js",
        "src/foo.test.mjs",
        "src/foo.test.cjs",
        "src/__tests__/foo.ts",
        "src/__tests__/foo.test.ts",
        "test/foo.ts",
        "tests/foo.ts",
        "src/foo/bar.spec.tsx",
        "src/components/Button.stories.tsx",
    ],
)
def test_is_test_file_true(filename: str) -> None:
    assert is_test_file(filename) is True


@pytest.mark.parametrize(
    "filename",
    [
        "src/foo.ts",
        "src/foo.js",
        "src/foo.test.md",  # not a source ext
        "package.json",
        "README.md",
    ],
)
def test_is_test_file_false(filename: str) -> None:
    assert is_test_file(filename) is False


@pytest.mark.parametrize(
    "filename",
    [
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "next.config.mjs",
        "jest.config.js",
        ".eslintrc.json",
        "docker-compose.yml",
        "pnpm-lock.yaml",
        "Dockerfile",
        ".env.example",
    ],
)
def test_is_config_file_true(filename: str) -> None:
    assert is_config_file(filename) is True


@pytest.mark.parametrize(
    "filename",
    [
        "src/foo.ts",
        "src/foo.test.ts",
        "README.md",
    ],
)
def test_is_config_file_false(filename: str) -> None:
    assert is_config_file(filename) is False


@pytest.mark.parametrize(
    "filename",
    ["README.md", "docs/guide.mdx", "NOTES.txt", "CHANGELOG.md"],
)
def test_is_doc_file_true(filename: str) -> None:
    assert is_doc_file(filename) is True


def test_classify_source_file() -> None:
    cat, lang, is_src, is_test = classify_file("src/payment/service.ts")
    assert cat == FileCategory.SOURCE
    assert lang == Language.TYPESCRIPT
    assert is_src is True
    assert is_test is False


def test_classify_test_file() -> None:
    cat, lang, is_src, is_test = classify_file("src/payment/service.test.ts")
    assert cat == FileCategory.TEST
    assert lang == Language.TYPESCRIPT
    assert is_src is False
    assert is_test is True


def test_classify_config_file() -> None:
    cat, lang, is_src, is_test = classify_file("vite.config.ts")
    assert cat == FileCategory.CONFIG
    assert is_src is False
    assert is_test is False


def test_classify_doc_file() -> None:
    cat, lang, is_src, is_test = classify_file("README.md")
    assert cat == FileCategory.DOC
    assert lang == Language.OTHER


def test_classify_other_file() -> None:
    cat, lang, is_src, is_test = classify_file("migrations/001.sql")
    assert cat == FileCategory.OTHER
    assert lang == Language.OTHER
    assert is_src is False
    assert is_test is False
