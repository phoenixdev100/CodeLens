"""Unit tests for analysis/security.py (SecurityAnalyzer)."""
from __future__ import annotations

from analysis.security import SecurityAnalyzer
from models.analysis import Severity
from models.context import FileCategory
from tests.helpers import make_context, make_file


def test_hardcoded_password_detected() -> None:
    content = 'const password = "supersecret123";\n'
    files = [make_file("src/auth/config.ts", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    cred = [f for f in signal.findings if "cred" in f.id]
    assert len(cred) == 1
    assert cred[0].severity == Severity.HIGH


def test_hardcoded_api_key_detected() -> None:
    content = 'const API_KEY = "sk_live_1234567890abcdef";\n'
    files = [make_file("src/services/api.ts", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    cred = [f for f in signal.findings if "cred" in f.id]
    assert len(cred) == 1


def test_no_false_positive_for_short_values() -> None:
    content = 'const password = "short";\n'  # < 6 chars
    files = [make_file("src/auth/config.ts", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    cred = [f for f in signal.findings if "cred" in f.id]
    assert len(cred) == 0


def test_eval_detected() -> None:
    content = "export function run(code: string) { eval(code); }\n"
    files = [make_file("src/utils/eval.ts", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    # eval is now detected by xss-csrf check (code injection) or command injection
    assert any("eval" in f.title.lower() for f in signal.findings)


def test_innerhtml_detected() -> None:
    content = "el.innerHTML = userInput;\n"
    files = [make_file("src/components/widget.tsx", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    assert any("innerhtml" in f.title.lower() for f in signal.findings)


def test_sql_concat_detected() -> None:
    content = 'const q = "SELECT * FROM users WHERE id = " + userId;\n'
    files = [make_file("src/db/query.ts", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    assert any("sql" in f.title.lower() for f in signal.findings)


def test_sensitive_file_change_detected() -> None:
    files = [make_file("src/auth/session.ts")]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    sensitive = [f for f in signal.findings if "sensitive" in f.id]
    assert len(sensitive) == 1
    assert sensitive[0].severity == Severity.HIGH


def test_dependency_change_detected() -> None:
    patch = (
        '@@ -1,3 +1,5 @@\n'
        ' {\n'
        '   "dependencies": {\n'
        '+    "lodash": "^4.17.21",\n'
        '+    "axios": "^1.0.0",\n'
        '     "react": "^18.0.0"\n'
        '   }\n'
        ' }\n'
    )
    files = [make_file(
        "package.json",
        category=FileCategory.CONFIG,
        is_source=False,
        additions=2,
        deletions=0,
        patch_text=patch,
    )]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    deps = [f for f in signal.findings if "deps" in f.id]
    assert len(deps) == 1
    assert deps[0].severity == Severity.LOW


def test_no_findings_for_clean_file() -> None:
    content = "export const add = (a: number, b: number) => a + b;\n"
    files = [make_file("src/utils/add.ts", content=content)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    assert len(signal.findings) == 0


def test_test_files_excluded() -> None:
    content = 'const password = "supersecret123";\n'
    files = [make_file("src/auth/config.test.ts", content=content, is_source=False, is_test=True, category=FileCategory.TEST)]
    ctx = make_context(files)
    signal = SecurityAnalyzer().analyze(ctx)
    cred = [f for f in signal.findings if "cred" in f.id]
    assert len(cred) == 0
