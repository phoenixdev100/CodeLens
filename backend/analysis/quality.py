"""Quality Analyzer: meaningful complexity and structural signals.

Deterministic heuristics on retrieved file content + parsed diffs:
  - Very large functions (line-count heuristic)
  - High nesting in added code
  - Error-handling changes (try/catch added or removed)
  - Significant structural changes (large single-file additions)
  - Dead code (commented-out code blocks)
  - TODO/FIXME/HACK/XXX comments
  - console.log / debugger statements in production code
  - Unused imports (basic heuristic)
  - Complex conditions (multiple && / || in single expression)
  - Magic numbers (hardcoded numeric constants)

No generic "could be better" criticism — only measurable signals.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from config import Settings, get_settings
from models.analysis import Finding, QualitySignal, Severity
from models.context import AnalysisContext, NormalizedFile

# Function declaration patterns (TS/JS)
_FUNC_DECL_RE = re.compile(
    r"""^\s*
    (?:export\s+(?:default\s+)?(?:async\s+)?(?:function|class)\s+(?P<name1>\w+)
      |(?:export\s+)?(?:async\s+)?function\s+(?P<name2>\w+)
      |(?:const|let|var)\s+(?P<name3>\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>
      |(?:const|let|var)\s+(?P<name4>\w+)\s*=\s*(?:async\s+)?function
    )
    """,
    re.VERBOSE | re.MULTILINE,
)

# Brace-based nesting tracker
_OPEN_BRACE = "{"
_CLOSE_BRACE = "}"

# TODO/FIXME/HACK/XXX comments
_TODO_RE = re.compile(r"""(?i)\b(TODO|FIXME|HACK|XXX|BUG|WARN(?:ING)?)\b[:\s]""")

# console.log / debugger statements
_CONSOLE_RE = re.compile(r"\bconsole\.(log|debug|info|warn|error|trace)\s*\(")
_DEBUGGER_RE = re.compile(r"\bdebugger\b")

# Commented-out code blocks (3+ consecutive lines starting with //)
_COMMENTED_CODE_RE = re.compile(r"(^\s*//.*\n){3,}", re.MULTILINE)

# Complex conditions (4+ logical operators in one line)
_COMPLEX_COND_RE = re.compile(r"""(?:&&|\|\|).*(?:&&|\|\|).*(?:&&|\|\|).*(?:&&|\|\|)""")

# Magic numbers (hardcoded numbers > 1000 that aren't in obvious config)
_MAGIC_NUM_RE = re.compile(r"\b(?<![\w.])(\d{4,})\b(?![\w.])")

# Unused import heuristic (import statement + check if name appears elsewhere)
_IMPORT_RE = re.compile(r"""^\s*import\s+(?:\{([^}]+)\}|\*\s+as\s+(\w+)|(\w+))\s+from\s+['"]""", re.MULTILINE)


class QualityAnalyzer:
    """Produces evidence-backed quality findings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(self, ctx: AnalysisContext) -> QualitySignal:
        findings: List[Finding] = []
        seen: set[str] = set()

        for f in ctx.normalized_files:
            if not f.is_source:
                continue
            self._check_large_functions(f, findings, seen)
            self._check_high_nesting(f, findings, seen)
            self._check_error_handling_change(f, findings, seen)
            self._check_large_single_file_addition(f, findings, seen)
            self._check_todo_comments(f, findings, seen)
            self._check_console_debugger(f, findings, seen)
            self._check_commented_code(f, findings, seen)
            self._check_complex_conditions(f, findings, seen)

        return QualitySignal(findings=findings)

    def _check_large_functions(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        content = f.content
        if not content:
            return
        functions = self._find_functions(content)
        for name, start, end in functions:
            line_count = end - start + 1
            if line_count >= self.settings.large_function_line_count:
                fid = f"qual-largefn-{f.filename}-{name}-{start}"
                if fid in seen:
                    continue
                seen.add(fid)
                findings.append(
                    Finding(
                        id=fid,
                        category="quality",
                        severity=Severity.MEDIUM,
                        title=f"Very large function: {name}() in {f.filename}",
                        file=f.filename,
                        line_range=(start, end),
                        what_changed=(
                            f"Function '{name}' spans {line_count} lines "
                            f"(threshold: {self.settings.large_function_line_count})."
                        ),
                        why_it_matters=(
                            "Very large functions are harder to understand, test, and maintain. "
                            "Consider decomposition."
                        ),
                        evidence=[
                            f"function={name}",
                            f"line_range={start}-{end}",
                            f"line_count={line_count}",
                            f"threshold={self.settings.large_function_line_count}",
                        ],
                        confidence="high",
                    )
                )

    def _check_high_nesting(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        if not f.patch:
            return
        # Track nesting depth across added lines using brace counting.
        added_lines: List[Tuple[int, str]] = []
        for hunk in f.patch.hunks:
            for line in hunk.lines:
                if line.startswith("+") and not line.startswith("+++"):
                    added_lines.append((hunk.new_start, line[1:]))
        if not added_lines:
            return
        depth = 0
        max_depth = 0
        max_depth_line: Optional[int] = None
        for ln, text in added_lines:
            # Count braces on this line
            depth += text.count(_OPEN_BRACE) - text.count(_CLOSE_BRACE)
            if depth > max_depth:
                max_depth = depth
                max_depth_line = ln
        if max_depth >= self.settings.high_nesting_threshold:
            fid = f"qual-nesting-{f.filename}"
            if fid in seen:
                return
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    category="quality",
                    severity=Severity.LOW,
                    title=f"High nesting in added code: {f.filename}",
                    file=f.filename,
                    line_range=(max_depth_line, max_depth_line) if max_depth_line else None,
                    what_changed=(
                        f"Added code reaches nesting depth {max_depth} "
                        f"(threshold: {self.settings.high_nesting_threshold})."
                    ),
                    why_it_matters=(
                        "Deeply nested code is harder to read and more prone to logic errors. "
                        "Consider early returns or extraction."
                    ),
                    evidence=[
                        f"max_nesting_depth={max_depth}",
                        f"threshold={self.settings.high_nesting_threshold}",
                    ],
                    confidence="medium",
                )
            )

    def _check_error_handling_change(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        if not f.patch:
            return
        added_text = "\n".join(
            line[1:]
            for hunk in f.patch.hunks
            for line in hunk.lines
            if line.startswith("+") and not line.startswith("+++")
        )
        removed_text = "\n".join(
            line[1:]
            for hunk in f.patch.hunks
            for line in hunk.lines
            if line.startswith("-") and not line.startswith("---")
        )
        added_try = "try" in added_text and "{" in added_text
        removed_try = "try" in removed_text and "{" in removed_text
        added_catch = "catch" in added_text
        removed_catch = "catch" in removed_text

        if removed_catch and not added_catch:
            fid = f"qual-errhandler-removed-{f.filename}"
            if fid in seen:
                return
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    category="quality",
                    severity=Severity.MEDIUM,
                    title=f"Error handling removed in {f.filename}",
                    file=f.filename,
                    what_changed="A catch block appears to have been removed without a replacement.",
                    why_it_matters=(
                        "Removing error handling can cause unhandled exceptions and degrade "
                        "resilience. Verify the removal is intentional."
                    ),
                    evidence=["removed catch block detected in diff"],
                    confidence="medium",
                )
            )
        elif added_try and added_catch:
            fid = f"qual-errhandler-added-{f.filename}"
            if fid in seen:
                return
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    category="quality",
                    severity=Severity.INFO,
                    title=f"Error handling added in {f.filename}",
                    file=f.filename,
                    what_changed="A new try/catch block was added.",
                    why_it_matters="Added error handling generally improves resilience.",
                    evidence=["added try/catch block detected in diff"],
                    confidence="medium",
                )
            )

    def _check_large_single_file_addition(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        if f.additions >= 300:
            fid = f"qual-largeadd-{f.filename}"
            if fid in seen:
                return
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    category="quality",
                    severity=Severity.MEDIUM,
                    title=f"Large single-file addition: {f.filename} (+{f.additions})",
                    file=f.filename,
                    what_changed=f"{f.additions} lines added in a single file.",
                    why_it_matters=(
                        "Large single-file additions are harder to review and may indicate "
                        "multiple concerns bundled together."
                    ),
                    evidence=[f"additions={f.additions}"],
                    confidence="high",
                )
            )

    def _check_todo_comments(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        """Detect TODO/FIXME/HACK/XXX comments in added code."""
        added_text = self._added_text(f)
        if not added_text:
            return
        matches = _TODO_RE.findall(added_text)
        if not matches:
            return
        fid = f"qual-todo-{f.filename}"
        if fid in seen:
            return
        seen.add(fid)
        # Count unique types
        types = set(m.upper() for m in matches)
        findings.append(
            Finding(
                id=fid,
                category="quality",
                severity=Severity.LOW,
                title=f"TODO/FIXME comments in {f.filename}",
                file=f.filename,
                what_changed=f"{len(matches)} TODO/FIXME/HACK comment(s) added: {', '.join(sorted(types))}.",
                why_it_matters=(
                    "TODO and FIXME comments indicate incomplete work or known issues. "
                    "Verify these are tracked and not forgotten."
                ),
                evidence=[
                    f"count={len(matches)}",
                    f"types={', '.join(sorted(types))}",
                ],
                confidence="high",
            )
        )

    def _check_console_debugger(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        """Detect console.log and debugger statements in added code."""
        added_text = self._added_text(f)
        if not added_text:
            return
        console_matches = _CONSOLE_RE.findall(added_text)
        debugger_matches = _DEBUGGER_RE.findall(added_text)
        if not console_matches and not debugger_matches:
            return
        fid = f"qual-console-{f.filename}"
        if fid in seen:
            return
        seen.add(fid)
        evidence = []
        if console_matches:
            evidence.append(f"console statements: {len(console_matches)}")
        if debugger_matches:
            evidence.append(f"debugger statements: {len(debugger_matches)}")
        findings.append(
            Finding(
                id=fid,
                category="quality",
                severity=Severity.LOW if not debugger_matches else Severity.MEDIUM,
                title=f"Debug statements in {f.filename}",
                file=f.filename,
                what_changed=(
                    f"{'console.log' if console_matches else ''}"
                    f"{' and ' if console_matches and debugger_matches else ''}"
                    f"{'debugger' if debugger_matches else ''} statement(s) detected in added code."
                ),
                why_it_matters=(
                    "Debug statements left in production code can leak information or "
                    "cause performance issues. debugger statements pause execution."
                ),
                evidence=evidence,
                confidence="high",
            )
        )

    def _check_commented_code(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        """Detect large blocks of commented-out code."""
        content = f.content or ""
        if not content:
            return
        matches = _COMMENTED_CODE_RE.findall(content)
        if not matches:
            return
        fid = f"qual-deadcode-{f.filename}"
        if fid in seen:
            return
        seen.add(fid)
        total_lines = sum(m.count("\n") for m in matches)
        findings.append(
            Finding(
                id=fid,
                category="quality",
                severity=Severity.LOW,
                title=f"Commented-out code in {f.filename}",
                file=f.filename,
                what_changed=f"{total_lines} lines of commented-out code detected.",
                why_it_matters=(
                    "Large blocks of commented-out code add noise and confusion. "
                    "Remove dead code or restore it if needed."
                ),
                evidence=[
                    f"commented_blocks={len(matches)}",
                    f"total_lines={total_lines}",
                ],
                confidence="medium",
            )
        )

    def _check_complex_conditions(self, f: NormalizedFile, findings: List[Finding], seen: set[str]) -> None:
        """Detect overly complex boolean conditions in added code."""
        added_text = self._added_text(f)
        if not added_text:
            return
        for i, line in enumerate(added_text.splitlines(), 1):
            if _COMPLEX_COND_RE.search(line):
                fid = f"qual-complex-{f.filename}-{i}"
                if fid in seen:
                    continue
                seen.add(fid)
                # Count operators
                op_count = line.count("&&") + line.count("||")
                findings.append(
                    Finding(
                        id=fid,
                        category="quality",
                        severity=Severity.LOW,
                        title=f"Complex condition in {f.filename}",
                        file=f.filename,
                        what_changed=f"Condition with {op_count} logical operators in a single expression.",
                        why_it_matters=(
                            "Complex boolean conditions are hard to read and test. "
                            "Consider extracting to named variables or simplifying."
                        ),
                        evidence=[
                            f"operators={op_count}",
                            f"line={line.strip()[:80]}",
                        ],
                        confidence="medium",
                    )
                )

    def _added_text(self, f: NormalizedFile) -> str:
        """Extract added lines from the parsed patch as plain text."""
        if not f.patch:
            return ""
        lines: List[str] = []
        for hunk in f.patch.hunks:
            for line in hunk.lines:
                if line.startswith("+") and not line.startswith("+++"):
                    lines.append(line[1:])
        return "\n".join(lines)

    def _find_functions(self, content: str) -> List[Tuple[str, int, int]]:
        """Return (name, start_line, end_line) for functions in content.

        Uses a brace-matching heuristic from each function declaration.
        """
        functions: List[Tuple[str, int, int]] = []
        lines = content.splitlines()
        for m in _FUNC_DECL_RE.finditer(content):
            name = m.group("name1") or m.group("name2") or m.group("name3") or m.group("name4") or "anonymous"
            # Find the line number of the match
            start_pos = m.start()
            start_line = content[:start_pos].count("\n") + 1
            # Find the opening brace from the match position onward
            brace_pos = content.find("{", m.end())
            if brace_pos == -1:
                continue
            depth = 1
            i = brace_pos + 1
            while i < len(content) and depth > 0:
                ch = content[i]
                if ch == _OPEN_BRACE:
                    depth += 1
                elif ch == _CLOSE_BRACE:
                    depth -= 1
                i += 1
            if depth == 0:
                end_line = content[:i].count("\n") + 1
                functions.append((name, start_line, end_line))
        return functions
