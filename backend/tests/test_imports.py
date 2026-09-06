"""Unit tests for context/imports.py."""
from __future__ import annotations

from context.imports import (
    collect_external_packages,
    extract_imports,
    is_relative_specifier,
    resolve_specifier,
)


SAMPLE_SOURCE = """\
import { foo } from './foo';
import bar from '../bar';
import * as ns from './utils/ns';
import type { Type } from './types';
import './side-effect';
export { x } from './reexport';
const dep = require('../../deps/dep');
const dyn = await import('./dynamic');
import React from 'react';
import { debounce } from 'lodash/debounce';
import { Button } from '@ui/components/Button';
"""


def test_extract_imports_finds_all_forms() -> None:
    edges = extract_imports("src/payment/service.ts", SAMPLE_SOURCE)
    specs = {e.raw_specifier for e in edges}
    assert "./foo" in specs
    assert "../bar" in specs
    assert "./utils/ns" in specs
    assert "./types" in specs
    assert "./side-effect" in specs
    assert "./reexport" in specs
    assert "../../deps/dep" in specs
    assert "./dynamic" in specs
    assert "react" in specs
    assert "lodash/debounce" in specs
    assert "@ui/components/Button" in specs


def test_extract_imports_external_flag() -> None:
    edges = extract_imports("src/payment/service.ts", SAMPLE_SOURCE)
    by_spec = {e.raw_specifier: e for e in edges}
    assert by_spec["react"].is_external is True
    assert by_spec["lodash/debounce"].is_external is True
    assert by_spec["@ui/components/Button"].is_external is True
    assert by_spec["./foo"].is_external is False
    assert by_spec["../bar"].is_external is False


def test_extract_imports_resolves_relative_paths() -> None:
    edges = extract_imports("src/payment/service.ts", SAMPLE_SOURCE)
    by_spec = {e.raw_specifier: e for e in edges}
    assert by_spec["./foo"].resolved_path == "src/payment/foo.ts"
    assert by_spec["../bar"].resolved_path == "src/bar.ts"
    assert by_spec["../../deps/dep"].resolved_path == "deps/dep.ts"
    assert by_spec["./utils/ns"].resolved_path == "src/payment/utils/ns.ts"


def test_extract_imports_external_has_no_resolved_path() -> None:
    edges = extract_imports("src/payment/service.ts", SAMPLE_SOURCE)
    by_spec = {e.raw_specifier: e for e in edges}
    assert by_spec["react"].resolved_path is None
    assert by_spec["@ui/components/Button"].resolved_path is None


def test_extract_imports_dedupes_duplicates() -> None:
    source = "import { a } from './foo';\nimport { b } from './foo';\n"
    edges = extract_imports("src/x.ts", source)
    foo_edges = [e for e in edges if e.raw_specifier == "./foo"]
    assert len(foo_edges) == 1


def test_is_relative_specifier() -> None:
    assert is_relative_specifier("./foo") is True
    assert is_relative_specifier("../bar") is True
    assert is_relative_specifier("/abs/path") is True
    assert is_relative_specifier("react") is False
    assert is_relative_specifier("@scope/pkg") is False


def test_resolve_specifier_external() -> None:
    resolved, is_ext = resolve_specifier("src/x.ts", "react")
    assert resolved is None
    assert is_ext is True


def test_collect_external_packages_normalizes_scoped() -> None:
    edges = extract_imports("src/x.ts", SAMPLE_SOURCE)
    pkgs = collect_external_packages(edges)
    assert "react" in pkgs
    assert "lodash" in pkgs
    assert "@ui/components" in pkgs
    # Internal packages should not appear
    assert all(not p.startswith(".") for p in pkgs)


def test_extract_imports_empty_content() -> None:
    edges = extract_imports("src/x.ts", "")
    assert edges == []
