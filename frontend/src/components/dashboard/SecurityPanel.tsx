"use client";

import { Card } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/Badge";
import { SeverityDot } from "@/components/ui/SeverityIcon";
import type { Phase4Result, SecurityCheckResult, Finding } from "@/types/analysis";

const CHECK_TYPE_LABELS: Record<string, string> = {
  "secret-scan": "Secret Scanning",
  "injection": "SQL / NoSQL Injection",
  "xss-csrf": "XSS & CSRF",
  "path-traversal-ssrf": "Path Traversal & SSRF",
  "command-injection": "Command Injection",
  "sensitive-file": "Sensitive File Changes",
  "dependency": "Dependency Audit",
};

const CHECK_TYPE_DESCRIPTIONS: Record<string, string> = {
  "secret-scan": "Checks if any passwords, API keys, or tokens were accidentally left in the code",
  "injection": "Checks if user input could be used to run unwanted database queries (SQL/NoSQL injection)",
  "xss-csrf": "Checks for cross-site scripting (XSS) and cross-site request forgery (CSRF) vulnerabilities",
  "path-traversal-ssrf": "Checks if user input could be used to access files or servers they shouldn't",
  "command-injection": "Checks if user input could be used to run system commands on the server",
  "sensitive-file": "Flags changes to files that handle authentication, sessions, tokens, or security",
  "dependency": "Checks if new or changed dependencies (packages) look suspicious or unsafe",
};

export function SecurityPanel({
  analysis,
  onSelectFinding,
}: {
  analysis: Phase4Result;
  onSelectFinding: (id: string) => void;
}) {
  const { security } = analysis.analysis;
  const checks = security.checks ?? [];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Security Checks</h1>
        <p className="mt-1 text-sm text-slate-500">
          CodeLens runs {security.total_checks} automated security checks on this PR.
          {security.failed_checks > 0 ? (
            <span className="font-medium text-red-600"> {security.failed_checks} check(s) found issues.</span>
          ) : (
            <span className="font-medium text-green-600"> All checks passed — no security issues detected.</span>
          )}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-7">
        <SummaryCard label="Total Checks" value={security.total_checks} color="text-slate-900" hint="Number of security categories scanned" />
        <SummaryCard label="Passed" value={security.passed_checks} color="text-green-600" hint="Checks that found no issues" />
        <SummaryCard label="Failed" value={security.failed_checks} color="text-red-600" hint="Checks that found potential security issues" />
        <SummaryCard label="Issues Found" value={security.findings.length} color="text-amber-600" hint="Total security issues detected" />
      </div>

      {/* Check results */}
      <div className="grid gap-4 lg:grid-cols-2">
        {checks.map((check) => (
          <CheckCard key={check.check_type} check={check} onSelectFinding={onSelectFinding} />
        ))}
      </div>

      {/* All security findings */}
      {security.findings.length > 0 && (
        <Card padding="lg">
          <h3 className="mb-1 text-sm font-semibold text-slate-900">All Security Issues</h3>
          <p className="mb-3 text-xs text-slate-400">Sorted by severity — most critical first. Click any issue for details.</p>
          <div className="space-y-2">
            {security.findings
              .slice()
              .sort((a, b) => severityRank(b.severity) - severityRank(a.severity))
              .map((finding) => (
                <button
                  key={finding.id}
                  onClick={() => onSelectFinding(finding.id)}
                  className="flex w-full items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-indigo-300 hover:bg-indigo-50/30"
                >
                  <SeverityDot severity={finding.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{finding.title}</p>
                    <p className="truncate text-xs text-slate-500">
                      {finding.file ?? "—"} · {finding.confidence} confidence
                    </p>
                  </div>
                  <SeverityBadge severity={finding.severity} />
                </button>
              ))}
          </div>
        </Card>
      )}

      <p className="text-xs text-slate-400">
        CodeLens uses automated pattern matching — it may miss some issues or flag things that aren&apos;t actually problems.
        Always verify important findings manually.
      </p>
    </div>
  );
}

function CheckCard({
  check,
  onSelectFinding,
}: {
  check: SecurityCheckResult;
  onSelectFinding: (id: string) => void;
}) {
  const label = CHECK_TYPE_LABELS[check.check_type] ?? check.check_type;
  const description = CHECK_TYPE_DESCRIPTIONS[check.check_type] ?? "";
  const statusConfig = {
    pass: { bg: "bg-green-50", border: "border-green-200", text: "text-green-700", icon: "✓", label: "PASSED" },
    warn: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", icon: "⚠", label: "REVIEW NEEDED" },
    fail: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", icon: "✗", label: "ISSUES FOUND" },
  };
  const cfg = statusConfig[check.status as keyof typeof statusConfig] ?? statusConfig.pass;

  return (
    <Card padding="none">
      {/* Header */}
      <div className={`flex items-center justify-between border-b ${cfg.border} ${cfg.bg} px-4 py-3`}>
        <div className="flex items-center gap-3">
          <span className={`text-lg font-bold ${cfg.text}`}>{cfg.icon}</span>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">{label}</h3>
            <p className="text-xs text-slate-500">{check.summary}</p>
          </div>
        </div>
        <span className={`rounded-full border ${cfg.border} ${cfg.bg} px-2.5 py-0.5 text-xs font-bold ${cfg.text}`}>
          {cfg.label}
        </span>
      </div>

      {/* Description */}
      <div className="px-4 py-2">
        <p className="text-xs text-slate-400">{description}</p>
      </div>

      {/* Findings */}
      {check.findings.length > 0 && (
        <div className="border-t border-slate-100">
          <div className="space-y-1 p-3">
            {check.findings.map((finding) => (
              <FindingRow key={finding.id} finding={finding} onClick={() => onSelectFinding(finding.id)} />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function FindingRow({ finding, onClick }: { finding: Finding; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-start gap-3 rounded-lg border border-slate-100 bg-white px-3 py-2 text-left transition hover:border-indigo-200 hover:bg-indigo-50/20"
    >
      <SeverityDot severity={finding.severity} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900">{finding.title}</p>
        <p className="mt-0.5 text-xs text-slate-500">
          {finding.file ?? "—"}
          {finding.line_range && ` :${finding.line_range[0]}`}
        </p>
        <p className="mt-1 text-xs text-slate-400">{finding.what_changed}</p>
        {finding.evidence.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {finding.evidence.slice(0, 3).map((ev, i) => (
              <span key={i} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                {ev}
              </span>
            ))}
          </div>
        )}
      </div>
      <SeverityBadge severity={finding.severity} />
    </button>
  );
}

function SummaryCard({ label, value, color, hint }: { label: string; value: number; color: string; hint?: string }) {
  return (
    <Card padding="sm" className={hint ? "cursor-help" : ""}>
      <p className="text-xs text-slate-400" title={hint}>{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
    </Card>
  );
}

function severityRank(s: string): number {
  const ranks: Record<string, number> = { critical: 5, high: 4, medium: 3, low: 2, info: 1 };
  return ranks[s] ?? 0;
}
