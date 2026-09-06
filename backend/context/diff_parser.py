"""Parse unified-diff patch strings into structured hunks.

Each per-file `patch` from GitHub looks like:

    @@ -82,7 +82,12 @@ def foo():
     context line
    -removed line
    +added line
     context line

We extract hunk headers (old/new start + count) and track added/removed line
numbers in the new/old file coordinate spaces.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from models.context import DiffHunk, ParsedPatch

# Matches: @@ -start,count +start,count @@ optional section
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


def parse_patch(filename: str, patch: Optional[str]) -> Optional[ParsedPatch]:
    """Parse a single file's unified-diff patch string.

    Returns None if the patch is missing or contains no hunks.
    """
    if not patch:
        return None

    hunks: List[DiffHunk] = []
    current: Optional[DiffHunk] = None
    old_line = 0
    new_line = 0

    for raw in patch.splitlines():
        if raw.startswith("@@"):
            # Flush previous hunk
            if current is not None:
                hunks.append(current)
            m = _HUNK_HEADER_RE.match(raw)
            if not m:
                # Malformed header; skip line
                current = None
                continue
            old_start = int(m.group("old_start"))
            old_count = int(m.group("old_count")) if m.group("old_count") else 1
            new_start = int(m.group("new_start"))
            new_count = int(m.group("new_count")) if m.group("new_count") else 1
            current = DiffHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
            )
            old_line = old_start
            new_line = new_start
            continue

        if current is None:
            # Lines before the first hunk header (e.g. "diff --git" preamble)
            continue

        current.lines.append(raw)

        if raw.startswith("+++") or raw.startswith("---"):
            # File header lines (e.g. +++ b/foo.ts) — not content lines
            continue
        elif raw.startswith("+"):
            current.added_line_numbers.append(new_line)
            new_line += 1
        elif raw.startswith("-"):
            current.removed_line_numbers.append(old_line)
            old_line += 1
        elif raw.startswith(" ") or raw == "":
            # Context line (or empty line treated as context)
            old_line += 1
            new_line += 1
        elif raw.startswith("\\"):
            # e.g. "\ No newline at end of file" — meta line, skip
            continue

    if current is not None:
        hunks.append(current)

    if not hunks:
        return None

    all_added = [n for h in hunks for n in h.added_line_numbers]
    all_removed = [n for h in hunks for n in h.removed_line_numbers]
    new_range = _compute_new_range(hunks)

    return ParsedPatch(
        filename=filename,
        hunks=hunks,
        added_line_numbers=all_added,
        removed_line_numbers=all_removed,
        new_file_line_range=new_range,
    )


def _compute_new_range(hunks: List[DiffHunk]) -> Optional[Tuple[int, int]]:
    """Approximate [first, last] touched line range in the new file."""
    nums: List[int] = []
    for h in hunks:
        if h.added_line_numbers:
            nums.extend(h.added_line_numbers)
        elif h.new_count > 0:
            # No additions but hunk modifies context — use new_start..new_start+new_count-1
            nums.extend(range(h.new_start, h.new_start + h.new_count))
    if not nums:
        return None
    return (min(nums), max(nums))
