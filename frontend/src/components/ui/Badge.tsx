// Reusable badge component for severity, risk level, and status indicators.

import type { Severity } from "@/types/analysis";

const SEVERITY_STYLES: Record<Severity, { bg: string; text: string; border: string; label: string }> = {
  critical: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", label: "CRITICAL" },
  high: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", label: "HIGH" },
  medium: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200", label: "MEDIUM" },
  low: { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200", label: "LOW" },
  info: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", label: "INFO" },
};

const RISK_LEVEL_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: "bg-red-50", text: "text-red-700", border: "border-red-300" },
  HIGH: { bg: "bg-red-50", text: "text-red-700", border: "border-red-300" },
  MEDIUM: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-300" },
  LOW: { bg: "bg-green-50", text: "text-green-700", border: "border-green-300" },
};

export function SeverityBadge({ severity, size = "sm" }: { severity: Severity; size?: "sm" | "xs" }) {
  const s = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.info;
  const sizeCls = size === "xs" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs";
  return (
    <span
      className={`inline-flex items-center rounded border font-semibold uppercase tracking-wide ${s.bg} ${s.text} ${s.border} ${sizeCls}`}
    >
      {s.label}
    </span>
  );
}

export function RiskLevelBadge({ level, score }: { level: string; score?: number }) {
  const s = RISK_LEVEL_STYLES[level] ?? RISK_LEVEL_STYLES.LOW;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-bold uppercase tracking-wide ${s.bg} ${s.text} ${s.border}`}
    >
      {level}
      {score != null && <span className="font-mono text-xs opacity-80">{score}/100</span>}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  const styles: Record<string, string> = {
    change: "bg-slate-100 text-slate-700 border-slate-200",
    critical: "bg-red-50 text-red-700 border-red-200",
    security: "bg-orange-50 text-orange-700 border-orange-200",
    quality: "bg-purple-50 text-purple-700 border-purple-200",
    tests: "bg-blue-50 text-blue-700 border-blue-200",
  };
  const cls = styles[category] ?? "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {category}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    added: "bg-green-50 text-green-700 border-green-200",
    modified: "bg-yellow-50 text-yellow-700 border-yellow-200",
    removed: "bg-red-50 text-red-700 border-red-200",
    renamed: "bg-blue-50 text-blue-700 border-blue-200",
  };
  const cls = styles[status] ?? "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
