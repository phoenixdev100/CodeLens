"""Unit tests for context/diff_parser.py."""
from __future__ import annotations

from context.diff_parser import parse_patch


SAMPLE_PATCH = """@@ -1,5 +1,7 @@
 import { foo } from './bar';
-export function oldFunc() {
-  return 1;
+export function newFunc() {
+  return 2;
+  return 3;
 }
 const x = 1;
@@ -10,3 +12,4 @@
 const y = 2;
 const z = 3;
+const w = 4;
 const a = 5;
"""


def test_parse_patch_basic() -> None:
    result = parse_patch("src/foo.ts", SAMPLE_PATCH)
    assert result is not None
    assert result.filename == "src/foo.ts"
    assert len(result.hunks) == 2

    h0 = result.hunks[0]
    assert h0.old_start == 1
    assert h0.old_count == 5
    assert h0.new_start == 1
    assert h0.new_count == 7
    # 2 removed, 3 added in first hunk
    assert len(h0.removed_line_numbers) == 2
    assert len(h0.added_line_numbers) == 3
    # Added lines start at new_start=1
    assert h0.added_line_numbers == [2, 3, 4]
    assert h0.removed_line_numbers == [2, 3]

    h1 = result.hunks[1]
    assert h1.old_start == 10
    assert h1.new_start == 12
    assert h1.added_line_numbers == [14]
    assert h1.removed_line_numbers == []


def test_parse_patch_aggregated_lines() -> None:
    result = parse_patch("src/foo.ts", SAMPLE_PATCH)
    assert result is not None
    assert result.added_line_numbers == [2, 3, 4, 14]
    assert result.removed_line_numbers == [2, 3]
    assert result.new_file_line_range == (2, 14)


def test_parse_patch_none_for_empty() -> None:
    assert parse_patch("src/foo.ts", None) is None
    assert parse_patch("src/foo.ts", "") is None
    assert parse_patch("src/foo.ts", "no hunk header here\n") is None


def test_parse_patch_single_line_counts() -> None:
    # Hunk header with implicit count of 1 (no context line, just add/remove)
    patch = "@@ -5 +5 @@\n-old\n+new\n"
    result = parse_patch("a.ts", patch)
    assert result is not None
    h = result.hunks[0]
    assert h.old_count == 1
    assert h.new_count == 1
    assert h.removed_line_numbers == [5]
    assert h.added_line_numbers == [5]


def test_parse_patch_no_newline_meta_line() -> None:
    patch = "@@ -1,2 +1,2 @@\n line1\n-old\n+new\n\\ No newline at end of file\n"
    result = parse_patch("a.ts", patch)
    assert result is not None
    h = result.hunks[0]
    # The "\\ No newline" line should not affect line counters
    assert h.removed_line_numbers == [2]
    assert h.added_line_numbers == [2]
