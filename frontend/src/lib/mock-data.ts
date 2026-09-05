// Mock data for UI demonstration without GitHub credentials.
// This represents a realistic PR scenario and is clearly structured
// to demonstrate all CodeLens features.

import type {
  Phase4Result,
  AnalyzeResponse,
} from "@/types/analysis";
import type { ImpactMap, ImpactNode, ImpactEdge } from "@/types/impact-map";

const mockMeta = {
  owner: "acme",
  repo: "payments-platform",
  number: 142,
  title: "Improve checkout and payment handling",
  state: "open",
  author: "sarah.chen",
  body: "This PR refactors the checkout flow, updates payment calculation logic, and adds refund support. Also includes auth token validation improvements.",
  html_url: "https://github.com/acme/payments-platform/pull/142",
  base_branch: "main",
  head_branch: "feature/checkout-refactor",
  created_at: "2026-01-15T10:30:00Z",
  updated_at: "2026-01-16T14:20:00Z",
};

const mockFindings = [
  {
    id: "critical-payments",
    category: "critical",
    severity: "critical" as const,
    title: "Critical area changed: payments",
    file: "src/payment/service.ts",
    line_range: [82, 119] as [number, number],
    what_changed: "3 file(s) in the payments area were changed.",
    why_it_matters: "Changes to payments can have serious security or business impact. Review carefully.",
    evidence: ["path contains 'payment'", "content references 'charge'", "files=['src/payment/service.ts', 'src/payment/refund.ts']"],
    confidence: "high" as const,
  },
  {
    id: "critical-authentication",
    category: "critical",
    severity: "critical" as const,
    title: "Critical area changed: authentication",
    file: "src/auth/session.ts",
    line_range: [41, 78] as [number, number],
    what_changed: "1 file(s) in the authentication area were changed.",
    why_it_matters: "Changes to authentication can have serious security or business impact. Review carefully.",
    evidence: ["path contains 'auth'", "content references 'verifyToken'", "files=['src/auth/session.ts']"],
    confidence: "high" as const,
  },
  {
    id: "sec-sensitive-src/auth/session.ts",
    category: "security",
    severity: "high" as const,
    title: "Security-sensitive file changed: src/auth/session.ts",
    file: "src/auth/session.ts",
    line_range: null,
    what_changed: "File path contains 'auth', indicating a security-sensitive area.",
    why_it_matters: "Changes to auth/session/token/crypto files can affect the security posture. Review for correctness and absence of regressions.",
    evidence: ["path contains 'auth'"],
    confidence: "high" as const,
  },
  {
    id: "sec-cred-src/auth/config.ts",
    category: "security",
    severity: "high" as const,
    title: "Possible hardcoded password in src/auth/config.ts",
    file: "src/auth/config.ts",
    line_range: null,
    what_changed: "A password appears to be assigned a literal string value.",
    why_it_matters: "Hardcoded secrets in source code are a serious security risk and should be moved to environment variables or a secret manager.",
    evidence: ["variable=password", "value_length=16", "pattern: credential assignment with string literal"],
    confidence: "medium" as const,
  },
  {
    id: "change-scope-drift",
    category: "change",
    severity: "medium" as const,
    title: "Potential scope drift detected",
    file: null,
    line_range: null,
    what_changed: "PR touches areas not mentioned in its title/body: authentication, database.",
    why_it_matters: "The PR may be broader than its stated intent. Review whether the unexpected areas belong in this PR.",
    evidence: ["stated_areas=['payments']", "actual_areas=['payments', 'authentication', 'database']", "unexpected_areas=['authentication', 'database']"],
    confidence: "medium" as const,
  },
  {
    id: "test-missing-src/payment/refund.ts",
    category: "tests",
    severity: "medium" as const,
    title: "No corresponding test change detected for src/payment/refund.ts",
    file: "src/payment/refund.ts",
    line_range: null,
    what_changed: "Production file 'src/payment/refund.ts' was changed but no related test file change was detected in this PR.",
    why_it_matters: "Changes to production code without corresponding test changes may indicate insufficient test coverage for the new behavior.",
    evidence: ["no related test file in changed files", "no test file matched by naming convention"],
    confidence: "medium" as const,
  },
  {
    id: "test-missing-src/auth/session.ts",
    category: "tests",
    severity: "medium" as const,
    title: "No corresponding test change detected for src/auth/session.ts",
    file: "src/auth/session.ts",
    line_range: null,
    what_changed: "Production file 'src/auth/session.ts' was changed but no related test file change was detected in this PR.",
    why_it_matters: "Changes to production code without corresponding test changes may indicate insufficient test coverage for the new behavior.",
    evidence: ["no related test file in changed files", "no test file matched by naming convention"],
    confidence: "medium" as const,
  },
  {
    id: "qual-largefn-src/payment/service.ts-processPayment",
    category: "quality",
    severity: "medium" as const,
    title: "Very large function: processPayment() in src/payment/service.ts",
    file: "src/payment/service.ts",
    line_range: [15, 98] as [number, number],
    what_changed: "Function 'processPayment' spans 83 lines (threshold: 80).",
    why_it_matters: "Very large functions are harder to understand, test, and maintain. Consider decomposition.",
    evidence: ["function=processPayment", "line_range=15-98", "line_count=83", "threshold=80"],
    confidence: "high" as const,
  },
  {
    id: "change-size",
    category: "change",
    severity: "medium" as const,
    title: "PR is large (42 files, +3421/-1287)",
    file: null,
    line_range: null,
    what_changed: "42 files changed, +3421 / -1287 lines (4708 total changes).",
    why_it_matters: "Large PRs are harder to review thoroughly and more likely to introduce subtle defects. Consider breaking into smaller PRs.",
    evidence: ["files_changed=42", "lines_added=3421", "lines_removed=1287", "size_class=large"],
    confidence: "high" as const,
  },
];

export const mockPhase4Result: Phase4Result = {
  phase: "phase-4-ai-risk-priority",
  meta: mockMeta,
  analysis: {
    phase: "phase-3-analysis-engine",
    meta: mockMeta,
    change: {
      files_changed: 42,
      lines_added: 3421,
      lines_removed: 1287,
      total_changes: 4708,
      size_class: "large",
      category_counts: { source: 28, test: 6, config: 4, doc: 3, other: 1 },
      functional_areas: [
        { name: "payments", files: ["src/payment/service.ts", "src/payment/refund.ts", "src/payment/calculator.ts"], detected_by: "path" },
        { name: "authentication", files: ["src/auth/session.ts", "src/auth/config.ts"], detected_by: "path" },
        { name: "checkout", files: ["src/checkout/controller.ts", "src/checkout/view.tsx"], detected_by: "path" },
        { name: "database", files: ["src/db/migration.ts", "src/db/schema.ts"], detected_by: "path" },
      ],
      scope_drift: {
        has_drift: true,
        stated_areas: ["payments"],
        actual_areas: ["payments", "authentication", "checkout", "database"],
        unexpected_areas: ["authentication", "checkout", "database"],
        reason: "PR title/body suggests: ['payments']. Changed files touch: ['payments', 'authentication', 'checkout', 'database']. Unexpected: ['authentication', 'checkout', 'database'].",
      },
      findings: mockFindings.filter(f => f.category === "change"),
    },
    critical: {
      areas: [
        { name: "payments", kind: "payments", files: ["src/payment/service.ts", "src/payment/refund.ts"], evidence: ["path contains 'payment'", "content references 'charge'"], severity: "critical" as const },
        { name: "authentication", kind: "authentication", files: ["src/auth/session.ts"], evidence: ["path contains 'auth'", "content references 'verifyToken'"], severity: "critical" as const },
      ],
      findings: mockFindings.filter(f => f.category === "critical"),
    },
    security: {
      findings: mockFindings.filter(f => f.category === "security"),
      checks: [
        { check_type: "secret-scan", status: "fail", summary: "1 secret(s) detected", findings: mockFindings.filter(f => f.id.includes("cred") || f.id.includes("secret")) },
        { check_type: "injection", status: "pass", summary: "No injection risks detected", findings: [] },
        { check_type: "xss-csrf", status: "pass", summary: "No XSS/CSRF risks detected", findings: [] },
        { check_type: "path-traversal-ssrf", status: "pass", summary: "No path traversal/SSRF risks detected", findings: [] },
        { check_type: "command-injection", status: "pass", summary: "No command injection risks detected", findings: [] },
        { check_type: "sensitive-file", status: "warn", summary: "2 sensitive file(s) changed", findings: mockFindings.filter(f => f.id.includes("sensitive")) },
        { check_type: "dependency", status: "warn", summary: "1 dependency change(s) flagged", findings: mockFindings.filter(f => f.id.includes("deps")) },
      ],
      total_checks: 7,
      passed_checks: 4,
      failed_checks: 3,
    },
    quality: {
      findings: mockFindings.filter(f => f.category === "quality"),
    },
    tests: {
      coverage: {
        changed_source_files: 28,
        changed_test_files: 6,
        source_files_with_tests: 18,
        source_files_without_tests: 10,
        missing_test_files: ["src/payment/refund.ts", "src/auth/session.ts", "src/auth/config.ts", "src/db/migration.ts"],
        has_reliable_coverage_report: false,
        coverage_note: "Test signal based on changed-file and naming-convention heuristics. No reliable coverage report was available; no exact percentage is claimed.",
      },
      findings: mockFindings.filter(f => f.category === "tests"),
    },
    all_findings: mockFindings,
    project_context: {
      name: "acme-store",
      description: "A modern e-commerce platform built with Next.js, FastAPI, and PostgreSQL. Handles payments, checkout, auth, and inventory.",
      language: "TypeScript",
      tech_stack: ["Next.js", "React", "TypeScript", "FastAPI", "PostgreSQL"],
      key_directories: ["src/payment", "src/auth", "src/checkout", "src/db"],
      readme_excerpt: "# ACME Store\n\nA modern e-commerce platform...\n\n## Features\n- Payment processing\n- User authentication\n- Checkout flow\n- Inventory management",
      package_info: { name: "acme-store", version: "1.4.2", framework: "Next.js, React, TypeScript", dependency_count: "47" },
    },
    stats: {
      total_findings: mockFindings.length,
      change_findings: 2,
      critical_findings: 2,
      security_findings: 2,
      quality_findings: 1,
      test_findings: 2,
      critical_areas: 2,
      functional_areas: 4,
      missing_test_files: 4,
    },
  },
  ai_insights: {
    pr_intent: "This PR (Improve checkout and payment handling) by sarah.chen changes 42 file(s) (+3421/-1287 lines). It affects: payments, authentication, checkout, database. Critical areas touched: payments, authentication.",
    functional_area_interpretation: "The PR touches 4 functional areas: payments, authentication, checkout, database. This breadth should be reviewed for intent.",
    scope_drift_reasoning: {
      assessment: "Scope drift signal detected: PR title/body suggests: ['payments']. Changed files touch: ['payments', 'authentication', 'checkout', 'database']. The auth and database changes may be unrelated to the payment fix. This is an inference based on area mismatch and should be verified by the reviewer.",
      is_inference: true,
    },
    finding_explanations: [
      { finding_id: "critical-payments", explanation: "The payment service is the core business logic for processing charges. Changes here directly affect revenue flow.", is_inference: false },
      { finding_id: "critical-authentication", explanation: "Authentication changes affect who can access the system. Token validation changes could introduce auth bypass vulnerabilities.", is_inference: false },
      { finding_id: "sec-cred-src/auth/config.ts", explanation: "A hardcoded password in source code is a critical security issue that should never reach production.", is_inference: false },
    ],
    risk_reasoning: "The PR is large (42 files), which increases review difficulty. Critical areas are affected (payments, authentication), elevating risk. Scope drift is detected, suggesting the PR may be broader than intended. 9 finding(s) were detected by deterministic analysis. (This reasoning is AI-derived and should be verified against the evidence.)",
    is_ai_generated: true,
    provider: "mock",
    disclaimer: "AI-derived insights are interpretations and may contain inaccuracies. Verify against the deterministic findings and evidence.",
  },
  risk: {
    total_score: 82,
    level: "HIGH",
    dimension_scores: [
      { dimension: "change", raw_score: 65, weight: 15, weighted_score: 9.75, contributing_factors: ["large PR: 42 files, +3421/-1287"] },
      { dimension: "scope", raw_score: 70, weight: 15, weighted_score: 10.5, contributing_factors: ["scope drift: unexpected areas ['authentication', 'checkout', 'database']"] },
      { dimension: "critical", raw_score: 100, weight: 25, weighted_score: 25.0, contributing_factors: ["payments: ['src/payment/service.ts', 'src/payment/refund.ts']", "authentication: ['src/auth/session.ts']"] },
      { dimension: "security", raw_score: 90, weight: 20, weighted_score: 18.0, contributing_factors: ["Security-sensitive file changed: src/auth/session.ts", "Possible hardcoded password in src/auth/config.ts"] },
      { dimension: "quality", raw_score: 50, weight: 10, weighted_score: 5.0, contributing_factors: ["Very large function: processPayment() in src/payment/service.ts"] },
      { dimension: "tests", raw_score: 64, weight: 15, weighted_score: 9.6, contributing_factors: ["18/28 source files have tests", "missing tests: ['src/payment/refund.ts', 'src/auth/session.ts']"] },
    ],
    top_contributors: [
      "critical (100/100, weight 25): payments: ['src/payment/service.ts', 'src/payment/refund.ts']; authentication: ['src/auth/session.ts']",
      "security (90/100, weight 20): Security-sensitive file changed: src/auth/session.ts; Possible hardcoded password in src/auth/config.ts",
      "scope (70/100, weight 15): scope drift: unexpected areas ['authentication', 'checkout', 'database']; stated: ['payments'], actual: ['payments', 'authentication', 'checkout', 'database']",
    ],
    weights: { change: 15, scope: 15, critical: 25, security: 20, quality: 10, tests: 15 },
    disclaimer: "This risk score is an MVP heuristic based on configurable weights, not a scientifically validated model. Use it as a prioritization aid, not as a definitive assessment.",
  },
  priority: {
    items: [
      { rank: 1, file: "src/payment/service.ts", score: 92, severity: "critical" as const, reason: "Critical area changed: payments; Very large function: processPayment(); no corresponding test change detected", supporting_finding_ids: ["critical-payments", "qual-largefn-src/payment/service.ts-processPayment", "test-missing-src/payment/service.ts"] },
      { rank: 2, file: "src/auth/session.ts", score: 88, severity: "critical" as const, reason: "Critical area changed: authentication; Security-sensitive file changed; no corresponding test change detected", supporting_finding_ids: ["critical-authentication", "sec-sensitive-src/auth/session.ts", "test-missing-src/auth/session.ts"] },
      { rank: 3, file: "src/auth/config.ts", score: 74, severity: "high" as const, reason: "Possible hardcoded password; no corresponding test change detected", supporting_finding_ids: ["sec-cred-src/auth/config.ts"] },
      { rank: 4, file: "src/payment/refund.ts", score: 70, severity: "critical" as const, reason: "Critical area changed: payments; no corresponding test change detected", supporting_finding_ids: ["critical-payments", "test-missing-src/payment/refund.ts"] },
      { rank: 5, file: "src/db/migration.ts", score: 45, severity: "medium" as const, reason: "no corresponding test change detected", supporting_finding_ids: ["test-missing-src/db/migration.ts"] },
    ],
    top_concerns: [
      "1. src/payment/service.ts (score 92, critical)",
      "2. src/auth/session.ts (score 88, critical)",
      "3. src/auth/config.ts (score 74, high)",
    ],
  },
  stats: {
    total_findings: mockFindings.length,
    risk_score: 82,
    risk_level: "HIGH",
    priority_items: 5,
    ai_provider: 0,
    critical_areas: 2,
  },
};

const mockImpactNodes: ImpactNode[] = [
  { id: "area:payments", type: "area", label: "payments", file_path: null, functional_area: "payments", changed: false, risk_color: "red", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 0, deletions: 0 },
  { id: "area:authentication", type: "area", label: "authentication", file_path: null, functional_area: "authentication", changed: false, risk_color: "red", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 0, deletions: 0 },
  { id: "area:checkout", type: "area", label: "checkout", file_path: null, functional_area: "checkout", changed: false, risk_color: "orange", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 0, deletions: 0 },
  { id: "area:database", type: "area", label: "database", file_path: null, functional_area: "database", changed: false, risk_color: "yellow", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 0, deletions: 0 },
  { id: "src/payment/service.ts", type: "source", label: "service.ts", file_path: "src/payment/service.ts", functional_area: "payments", changed: true, risk_color: "red", severity: "critical", finding_count: 3, finding_ids: ["critical-payments", "qual-largefn-src/payment/service.ts-processPayment"], priority_score: 92, is_critical_area: true, additions: 85, deletions: 22 },
  { id: "src/payment/refund.ts", type: "source", label: "refund.ts", file_path: "src/payment/refund.ts", functional_area: "payments", changed: true, risk_color: "red", severity: "critical", finding_count: 2, finding_ids: ["critical-payments", "test-missing-src/payment/refund.ts"], priority_score: 70, is_critical_area: true, additions: 45, deletions: 8 },
  { id: "src/payment/calculator.ts", type: "source", label: "calculator.ts", file_path: "src/payment/calculator.ts", functional_area: "payments", changed: true, risk_color: "green", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: true, additions: 30, deletions: 5 },
  { id: "src/auth/session.ts", type: "source", label: "session.ts", file_path: "src/auth/session.ts", functional_area: "authentication", changed: true, risk_color: "red", severity: "critical", finding_count: 3, finding_ids: ["critical-authentication", "sec-sensitive-src/auth/session.ts", "test-missing-src/auth/session.ts"], priority_score: 88, is_critical_area: true, additions: 38, deletions: 12 },
  { id: "src/auth/config.ts", type: "source", label: "config.ts", file_path: "src/auth/config.ts", functional_area: "authentication", changed: true, risk_color: "red", severity: "high", finding_count: 1, finding_ids: ["sec-cred-src/auth/config.ts"], priority_score: 74, is_critical_area: false, additions: 15, deletions: 3 },
  { id: "src/checkout/controller.ts", type: "source", label: "controller.ts", file_path: "src/checkout/controller.ts", functional_area: "checkout", changed: true, risk_color: "orange", severity: "medium", finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 60, deletions: 18 },
  { id: "src/checkout/view.tsx", type: "source", label: "view.tsx", file_path: "src/checkout/view.tsx", functional_area: "checkout", changed: true, risk_color: "green", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 42, deletions: 10 },
  { id: "src/db/migration.ts", type: "source", label: "migration.ts", file_path: "src/db/migration.ts", functional_area: "database", changed: true, risk_color: "yellow", severity: "low", finding_count: 1, finding_ids: ["test-missing-src/db/migration.ts"], priority_score: 45, is_critical_area: false, additions: 25, deletions: 0 },
  { id: "src/db/schema.ts", type: "source", label: "schema.ts", file_path: "src/db/schema.ts", functional_area: "database", changed: true, risk_color: "green", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 18, deletions: 4 },
  { id: "src/payment/service.test.ts", type: "test", label: "service.test.ts", file_path: "src/payment/service.test.ts", functional_area: "payments", changed: true, risk_color: "green", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 28, deletions: 5 },
  { id: "src/checkout/controller.test.ts", type: "test", label: "controller.test.ts", file_path: "src/checkout/controller.test.ts", functional_area: "checkout", changed: true, risk_color: "green", severity: null, finding_count: 0, finding_ids: [], priority_score: null, is_critical_area: false, additions: 20, deletions: 2 },
];

const mockImpactEdges: ImpactEdge[] = [
  { id: "e1", source: "area:payments", target: "src/payment/service.ts", kind: "area" },
  { id: "e2", source: "area:payments", target: "src/payment/refund.ts", kind: "area" },
  { id: "e3", source: "area:payments", target: "src/payment/calculator.ts", kind: "area" },
  { id: "e4", source: "area:authentication", target: "src/auth/session.ts", kind: "area" },
  { id: "e5", source: "area:authentication", target: "src/auth/config.ts", kind: "area" },
  { id: "e6", source: "area:checkout", target: "src/checkout/controller.ts", kind: "area" },
  { id: "e7", source: "area:checkout", target: "src/checkout/view.tsx", kind: "area" },
  { id: "e8", source: "area:database", target: "src/db/migration.ts", kind: "area" },
  { id: "e9", source: "area:database", target: "src/db/schema.ts", kind: "area" },
  { id: "e10", source: "src/payment/service.ts", target: "src/payment/calculator.ts", kind: "import" },
  { id: "e11", source: "src/payment/service.ts", target: "src/payment/refund.ts", kind: "import" },
  { id: "e12", source: "src/checkout/controller.ts", target: "src/payment/service.ts", kind: "import" },
  { id: "e13", source: "src/auth/session.ts", target: "src/auth/config.ts", kind: "import" },
  { id: "e14", source: "src/payment/service.ts", target: "src/payment/service.test.ts", kind: "test" },
  { id: "e15", source: "src/checkout/controller.ts", target: "src/checkout/controller.test.ts", kind: "test" },
];

export const mockImpactMap: ImpactMap = {
  phase: "phase-5-impact-map",
  nodes: mockImpactNodes,
  edges: mockImpactEdges,
  stats: {
    total_nodes: mockImpactNodes.length,
    total_edges: mockImpactEdges.length,
    changed_files: 10,
    file_nodes: 10,
    area_nodes: 4,
    red_nodes: 5,
    orange_nodes: 1,
    yellow_nodes: 1,
    green_nodes: 7,
  },
  legend: {
    red: "Critical / High risk",
    orange: "Medium risk",
    yellow: "Needs attention",
    green: "Low risk / supporting",
  },
};

const mockDiff = `diff --git a/src/payment/service.ts b/src/payment/service.ts
index 1a2b3c4..5d6e7f8 100644
--- a/src/payment/service.ts
+++ b/src/payment/service.ts
@@ -80,20 +82,38 @@ export class PaymentService {
-  async processPayment(amount: number): Promise<PaymentResult> {
-    const total = amount;
-    return { success: true, amount: total };
+  async processPayment(amount: number, options?: PaymentOptions): Promise<PaymentResult> {
+    const discount = options?.discount ?? 0;
+    const total = amount - (amount * discount);
+    if (total < 0) {
+      throw new PaymentError("Invalid payment amount after discount");
+    }
+    const result = await this.gateway.charge(total);
+    return { success: result.ok, amount: total, transactionId: result.id };
   }
diff --git a/src/auth/session.ts b/src/auth/session.ts
index 2b3c4d5..6e7f8a9 100644
--- a/src/auth/session.ts
+++ b/src/auth/session.ts
@@ -39,15 +41,20 @@ export class SessionManager {
-  verifyToken(token: string): boolean {
-    return token.length > 0;
+  verifyToken(token: string): boolean {
+    if (!token || token.length < 10) {
+      return false;
+    }
+    try {
+      const payload = jwt.verify(token, this.secret);
+      return payload.exp > Date.now() / 1000;
+    } catch {
+      return false;
+    }
   }
diff --git a/src/payment/refund.ts b/src/payment/refund.ts
new file mode 100644
--- /dev/null
+++ b/src/payment/refund.ts
@@ -0,0 +1,25 @@
+export class RefundService {
+  async processRefund(transactionId: string, amount: number): Promise<RefundResult> {
+    const tx = await this.findTransaction(transactionId);
+    if (!tx) {
+      throw new RefundError("Transaction not found");
+    }
+    if (amount > tx.amount) {
+      throw new RefundError("Refund amount exceeds original payment");
+    }
+    return await this.gateway.refund(transactionId, amount);
+  }
+}
`;

export const mockAnalyzeResponse: AnalyzeResponse = {
  phase: "phase-1-github-foundation",
  meta: mockMeta,
  diff_summary: {
    total_additions: 3421,
    total_deletions: 1287,
    total_changes: 4708,
    files_changed: 42,
  },
  files: [
    { filename: "src/payment/service.ts", status: "modified", additions: 85, deletions: 22, changes: 107, patch: mockDiff.split("diff --git")[1] ?? null, previous_filename: null },
    { filename: "src/auth/session.ts", status: "modified", additions: 38, deletions: 12, changes: 50, patch: mockDiff.split("diff --git")[2] ?? null, previous_filename: null },
    { filename: "src/payment/refund.ts", status: "added", additions: 25, deletions: 0, changes: 25, patch: mockDiff.split("diff --git")[3] ?? null, previous_filename: null },
    { filename: "src/checkout/controller.ts", status: "modified", additions: 60, deletions: 18, changes: 78, patch: null, previous_filename: null },
    { filename: "src/checkout/view.tsx", status: "modified", additions: 42, deletions: 10, changes: 52, patch: null, previous_filename: null },
    { filename: "src/auth/config.ts", status: "modified", additions: 15, deletions: 3, changes: 18, patch: null, previous_filename: null },
    { filename: "src/db/migration.ts", status: "added", additions: 25, deletions: 0, changes: 25, patch: null, previous_filename: null },
    { filename: "src/db/schema.ts", status: "modified", additions: 18, deletions: 4, changes: 22, patch: null, previous_filename: null },
    { filename: "src/payment/calculator.ts", status: "modified", additions: 30, deletions: 5, changes: 35, patch: null, previous_filename: null },
    { filename: "src/payment/service.test.ts", status: "modified", additions: 28, deletions: 5, changes: 33, patch: null, previous_filename: null },
  ],
  raw_diff: mockDiff,
};
