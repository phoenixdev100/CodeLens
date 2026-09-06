"""Unit tests for analysis/quality.py (QualityAnalyzer)."""
from __future__ import annotations

from analysis.quality import QualityAnalyzer
from config import Settings
from models.analysis import Severity
from tests.helpers import make_context, make_file


def _settings(large_fn: int = 80, nesting: int = 4) -> Settings:
    return Settings(
        github_app_id="", github_private_key_path="", github_installation_id="",
        github_token="", cors_origins="http://localhost:3000",
        max_files_per_pr=300, max_files_to_retrieve=25, max_file_content_chars=50000,
        large_pr_file_count=20, xlarge_pr_file_count=50,
        large_pr_line_count=500, large_function_line_count=large_fn, high_nesting_threshold=nesting,
    )


LARGE_FUNCTION = """\
export function processPayment(amount: number) {
  const line1 = 1;
  const line2 = 2;
  const line3 = 3;
  const line4 = 4;
  const line5 = 5;
  const line6 = 6;
  const line7 = 7;
  const line8 = 8;
  const line9 = 9;
  const line10 = 10;
  const line11 = 11;
  const line12 = 12;
  const line13 = 13;
  const line14 = 14;
  const line15 = 15;
  const line16 = 16;
  const line17 = 17;
  const line18 = 18;
  const line19 = 19;
  const line20 = 20;
  const line21 = 21;
  const line22 = 22;
  const line23 = 23;
  const line24 = 24;
  const line25 = 25;
  const line26 = 26;
  const line27 = 27;
  const line28 = 28;
  const line29 = 29;
  const line30 = 30;
  const line31 = 31;
  const line32 = 32;
  const line33 = 33;
  const line34 = 34;
  const line35 = 35;
  const line36 = 36;
  const line37 = 37;
  const line38 = 38;
  const line39 = 39;
  const line40 = 40;
  const line41 = 41;
  const line42 = 42;
  const line43 = 43;
  const line44 = 44;
  const line45 = 45;
  const line46 = 46;
  const line47 = 47;
  const line48 = 48;
  const line49 = 49;
  const line50 = 50;
  const line51 = 51;
  const line52 = 52;
  const line53 = 53;
  const line54 = 54;
  const line55 = 55;
  const line56 = 56;
  const line57 = 57;
  const line58 = 58;
  const line59 = 59;
  const line60 = 60;
  const line61 = 61;
  const line62 = 62;
  const line63 = 63;
  const line64 = 64;
  const line65 = 65;
  const line66 = 66;
  const line67 = 67;
  const line68 = 68;
  const line69 = 69;
  const line70 = 70;
  const line71 = 71;
  const line72 = 72;
  const line73 = 73;
  const line74 = 74;
  const line75 = 75;
  const line76 = 76;
  const line77 = 77;
  const line78 = 78;
  const line79 = 79;
  const line80 = 80;
  const line81 = 81;
  const line82 = 82;
  const line83 = 83;
  const line84 = 84;
  const line85 = 85;
  return amount;
}
"""


def test_large_function_detected() -> None:
    files = [make_file("src/payment/service.ts", content=LARGE_FUNCTION)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings(large_fn=80)).analyze(ctx)
    large_fns = [f for f in signal.findings if "largefn" in f.id]
    assert len(large_fns) == 1
    assert large_fns[0].severity == Severity.MEDIUM
    assert large_fns[0].line_range is not None


def test_small_function_not_flagged() -> None:
    content = "export function add(a: number, b: number) {\n  return a + b;\n}\n"
    files = [make_file("src/utils/add.ts", content=content)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings(large_fn=80)).analyze(ctx)
    large_fns = [f for f in signal.findings if "largefn" in f.id]
    assert len(large_fns) == 0


def test_high_nesting_detected() -> None:
    patch = """@@ -1,3 +1,12 @@
 export function foo() {
+  if (a) {
+    if (b) {
+      if (c) {
+        if (d) {
+          if (e) {
+            doSomething();
+          }
+        }
+      }
+    }
+  }
 }
"""
    files = [make_file("src/deep.ts", patch_text=patch, additions=10, deletions=0)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings(nesting=4)).analyze(ctx)
    nesting = [f for f in signal.findings if "nesting" in f.id]
    assert len(nesting) == 1


def test_error_handling_removed_detected() -> None:
    patch = """@@ -1,5 +1,3 @@
 export function risky() {
-  try {
-    doWork();
-  } catch (e) {
-    handleError(e);
-  }
+  doWork();
 }
"""
    files = [make_file("src/risky.ts", patch_text=patch, additions=1, deletions=4)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings()).analyze(ctx)
    removed = [f for f in signal.findings if "errhandler-removed" in f.id]
    assert len(removed) == 1
    assert removed[0].severity == Severity.MEDIUM


def test_error_handling_added_detected() -> None:
    patch = """@@ -1,3 +1,7 @@
 export function risky() {
+  try {
+    doWork();
+  } catch (e) {
+    handleError(e);
+  }
 }
"""
    files = [make_file("src/risky.ts", patch_text=patch, additions=5, deletions=0)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings()).analyze(ctx)
    added = [f for f in signal.findings if "errhandler-added" in f.id]
    assert len(added) == 1
    assert added[0].severity == Severity.INFO


def test_large_single_file_addition_detected() -> None:
    files = [make_file("src/big.ts", additions=350, deletions=0)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings()).analyze(ctx)
    large_add = [f for f in signal.findings if "largeadd" in f.id]
    assert len(large_add) == 1


def test_no_findings_for_clean_file() -> None:
    content = "export const x = 1;\n"
    files = [make_file("src/utils/x.ts", content=content)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings()).analyze(ctx)
    assert len(signal.findings) == 0


def test_non_source_files_skipped() -> None:
    files = [make_file("README.md", is_source=False, content=LARGE_FUNCTION)]
    ctx = make_context(files)
    signal = QualityAnalyzer(_settings(large_fn=80)).analyze(ctx)
    large_fns = [f for f in signal.findings if "largefn" in f.id]
    assert len(large_fns) == 0
