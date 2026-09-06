"""Extract import/require statements from TypeScript/JavaScript source.

Best-effort regex-based extraction (no full AST for the MVP). Resolves relative
specifiers (./, ../) to repo-relative paths and marks bare specifiers as
external packages.

Supported forms:
  import x from './foo'
  import { a, b } from './foo'
  import * as ns from '../bar'
  import './foo'
  import type { T } from './foo'
  export { x } from './foo'
  export * from './foo'
  const x = require('./foo')
  await import('./foo')            (dynamic import)
"""
from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

from models.context import ImportEdge

# --- Regexes ---------------------------------------------------------------

# Static imports / re-exports with a from clause.
# Matches: import ... from 'x', export ... from 'x', import type ... from 'x'
_IMPORT_FROM_RE = re.compile(
    r"""^[ \t]*(?:export|import)\b[^\n;]*?\bfrom\s*['"]([^'"]+)['"]\s*;?""",
    re.MULTILINE,
)

# Bare side-effect import: import './foo'
_SIDE_EFFECT_IMPORT_RE = re.compile(
    r"""^[ \t]*import\s*['"]([^'"]+)['"]\s*;?""",
    re.MULTILINE,
)

# Dynamic import: import('./foo') or await import('./foo')
_DYNAMIC_IMPORT_RE = re.compile(
    r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

# CommonJS require: require('./foo')
_REQUIRE_RE = re.compile(
    r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

# Source-file extensions we try when resolving a specifier without an extension.
_RESOLVE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json")
_INDEX_FILES = ("index.ts", "index.tsx", "index.js", "index.jsx", "index.mjs", "index.cjs")


def extract_imports(source_file: str, content: str) -> List[ImportEdge]:
    """Extract all import/require edges from a source file's content."""
    edges: List[ImportEdge] = []
    seen: set[Tuple[str, str, str]] = set()

    def _add(spec: str, kind: str) -> None:
        key = (source_file, spec, kind)
        if key in seen:
            return
        seen.add(key)
        resolved, is_external = resolve_specifier(source_file, spec)
        edges.append(
            ImportEdge(
                source_file=source_file,
                raw_specifier=spec,
                resolved_path=resolved,
                is_external=is_external,
                import_kind=kind,
            )
        )

    for m in _IMPORT_FROM_RE.finditer(content):
        _add(m.group(1), "import")
    for m in _SIDE_EFFECT_IMPORT_RE.finditer(content):
        _add(m.group(1), "import")
    for m in _DYNAMIC_IMPORT_RE.finditer(content):
        _add(m.group(1), "dynamic-import")
    for m in _REQUIRE_RE.finditer(content):
        _add(m.group(1), "require")

    return edges


def is_relative_specifier(spec: str) -> bool:
    """True for ./, ../, / (absolute within repo) specifiers; False for bare."""
    return spec.startswith("./") or spec.startswith("../") or spec.startswith("/")


def resolve_specifier(
    source_file: str, spec: str
) -> Tuple[Optional[str], bool]:
    """Resolve a module specifier to a repo-relative path.

    Returns (resolved_path, is_external). For bare specifiers (e.g. 'react'),
    returns (None, True). For relative specifiers, attempts extension/index
    resolution. If it cannot be resolved deterministically, returns
    (best_guess_path, False) where best_guess_path is the joined path with the
    specifier as-is — the caller can treat unresolved paths as "not found".
    """
    if not is_relative_specifier(spec):
        return None, True

    base_dir = os.path.dirname(source_file.replace("\\", "/"))
    joined = os.path.normpath(os.path.join(base_dir, spec)).replace("\\", "/")

    # 1. Exact path (specifier already includes a file extension)
    if _looks_like_file(joined):
        return joined, False

    # 2. Try adding common extensions. We can't check the filesystem here (no
    #    repo clone), so we return the most plausible candidate (.ts first for
    #    TS/JS repos). The retrieval layer can later verify by fetching.
    for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        return joined + ext, False

    # 3. Fallback: return the joined path as-is (e.g. directory import).
    return joined, False


def _looks_like_file(path: str) -> bool:
    """True if the path has a file extension."""
    _, ext = os.path.splitext(path)
    return bool(ext)


def collect_external_packages(edges: List[ImportEdge]) -> List[str]:
    """Return a sorted list of distinct external package specifiers."""
    pkgs: set[str] = set()
    for e in edges:
        if e.is_external:
            # Normalize scoped package: '@scope/name/sub' -> '@scope/name'
            spec = e.raw_specifier
            if spec.startswith("@"):
                parts = spec.split("/")
                if len(parts) >= 2:
                    pkgs.add(f"{parts[0]}/{parts[1]}")
                else:
                    pkgs.add(spec)
            else:
                pkgs.add(spec.split("/")[0])
    return sorted(pkgs)
