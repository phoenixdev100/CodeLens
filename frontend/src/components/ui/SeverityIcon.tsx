// Severity indicator dot — used in file lists and tables.

import type { Severity } from "@/types/analysis";

const SEVERITY_DOT: Record<Severity, string> = {
  critical: "bg-red-500",
  high: "bg-red-500",
  medium: "bg-orange-400",
  low: "bg-yellow-400",
  info: "bg-blue-400",
};

export function SeverityDot({ severity, filled = true }: { severity: Severity | null; filled?: boolean }) {
  if (!severity) {
    return <span className="inline-block h-2 w-2 rounded-full border border-slate-300 bg-white" />;
  }
  const cls = SEVERITY_DOT[severity] ?? "bg-slate-300";
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${filled ? cls : `border-2 ${cls.replace("bg-", "border-")}`}`}
      title={severity}
    />
  );
}
