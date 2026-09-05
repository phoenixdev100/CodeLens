"use client";

import { useMemo, useState } from "react";

import { Card } from "@/components/ui/Card";
import { SeverityBadge, CategoryBadge } from "@/components/ui/Badge";
import { SeverityDot } from "@/components/ui/SeverityIcon";
import type { Phase4Result, Finding, Severity } from "@/types/analysis";

const CATEGORIES = ["all", "change", "critical", "security", "quality", "tests"];
const SEVERITIES: (Severity | "all")[] = ["all", "critical", "high", "medium", "low", "info"];

export function FindingsPanel({
  analysis,
  onSelectFinding,
}: {
  analysis: Phase4Result;
  onSelectFinding: (id: string) => void;
}) {
  const { all_findings } = analysis.analysis;
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [fileFilter, setFileFilter] = useState("");

  const filtered = useMemo(() => {
    return all_findings
      .filter((f) => severityFilter === "all" || f.severity === severityFilter)
      .filter((f) => categoryFilter === "all" || f.category === categoryFilter)
      .filter((f) => !fileFilter || (f.file ?? "").toLowerCase().includes(fileFilter.toLowerCase()))
      .sort((a, b) => severityRank(b.severity) - severityRank(a.severity));
  }, [all_findings, severityFilter, categoryFilter, fileFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Findings</h1>
        <p className="mt-1 text-sm text-slate-500">
          {all_findings.length} finding(s) from deterministic analysis. Click a finding for details.
        </p>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Severity</label>
            <div className="flex flex-wrap gap-1">
              {SEVERITIES.map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`rounded border px-2 py-1 text-xs font-medium transition ${
                    severityFilter === sev
                      ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {sev === "all" ? "All" : sev.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Category</label>
            <div className="flex flex-wrap gap-1">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`rounded border px-2 py-1 text-xs font-medium capitalize transition ${
                    categoryFilter === cat
                      ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-slate-500">File</label>
            <input
              type="text"
              value={fileFilter}
              onChange={(e) => setFileFilter(e.target.value)}
              placeholder="Filter by file path…"
              className="w-full rounded border border-slate-200 px-3 py-1.5 text-sm text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200"
            />
          </div>
        </div>
      </Card>

      {/* Findings list */}
      <Card padding="none">
        <div className="border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {filtered.length} finding{filtered.length !== 1 ? "s" : ""}
          </h3>
        </div>
        {filtered.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <p className="text-sm text-slate-500">No findings match the current filters.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((finding) => (
              <FindingRow
                key={finding.id}
                finding={finding}
                onClick={() => onSelectFinding(finding.id)}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function FindingRow({ finding, onClick }: { finding: Finding; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
    >
      <div className="flex shrink-0 flex-col items-center gap-1.5 pt-0.5">
        <SeverityDot severity={finding.severity} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={finding.severity} size="xs" />
          <CategoryBadge category={finding.category} />
        </div>
        <p className="mt-1.5 text-sm font-medium text-slate-900">{finding.title}</p>
        <p className="mt-0.5 font-mono text-xs text-slate-400">
          {finding.file ?? "PR-wide"}
          {finding.line_range && ` · L${finding.line_range[0]}-${finding.line_range[1]}`}
        </p>
      </div>
      <svg className="mt-1 h-4 w-4 shrink-0 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}

function severityRank(s: string): number {
  return { critical: 5, high: 4, medium: 3, low: 2, info: 1 }[s] ?? 0;
}
