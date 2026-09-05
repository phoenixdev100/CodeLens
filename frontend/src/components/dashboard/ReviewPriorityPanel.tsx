"use client";

import { Card, CardHeader } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/Badge";
import { SeverityDot } from "@/components/ui/SeverityIcon";
import type { Phase4Result } from "@/types/analysis";

export function ReviewPriorityPanel({
  analysis,
  onSelectFinding,
  onSelectFile,
}: {
  analysis: Phase4Result;
  onSelectFinding: (id: string) => void;
  onSelectFile: (file: string) => void;
}) {
  const { priority } = analysis;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Review Priority</h1>
        <p className="mt-1 text-sm text-slate-500">
          Where to focus your review first. Ranked by priority score.
        </p>
      </div>

      {priority.top_concerns.length > 0 && (
        <Card className="border-indigo-100 bg-indigo-50/50">
          <CardHeader title="Top Concerns" subtitle="Summary of the most important review areas" />
          <ul className="space-y-1.5">
            {priority.top_concerns.map((concern, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                {concern}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card padding="none">
        <div className="border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">Priority Ranking</h3>
          <p className="mt-0.5 text-xs text-slate-500">{priority.items.length} file(s) ranked</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2.5 text-left">#</th>
                <th className="px-4 py-2.5 text-left">File</th>
                <th className="px-4 py-2.5 text-left">Severity</th>
                <th className="px-4 py-2.5 text-right">Score</th>
                <th className="px-4 py-2.5 text-left">Reason</th>
                <th className="px-4 py-2.5 text-right">Findings</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {priority.items.map((item) => (
                <tr
                  key={item.rank}
                  className="group transition hover:bg-slate-50"
                >
                  <td className="px-4 py-3">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">
                      {item.rank}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <SeverityDot severity={item.severity} />
                      <button
                        onClick={() => onSelectFile(item.file)}
                        className="font-mono text-xs text-slate-700 transition hover:text-indigo-600 hover:underline"
                      >
                        {item.file}
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={item.severity} size="xs" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-base font-bold text-slate-900">{item.score}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-slate-600">{item.reason}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-xs text-slate-500">{item.supporting_finding_ids.length}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2 opacity-0 transition group-hover:opacity-100">
                      {item.supporting_finding_ids.length > 0 && (
                        <button
                          onClick={() => onSelectFinding(item.supporting_finding_ids[0])}
                          className="rounded border border-slate-200 px-2 py-0.5 text-xs text-slate-600 transition hover:bg-slate-100"
                        >
                          Finding
                        </button>
                      )}
                      <button
                        onClick={() => onSelectFile(item.file)}
                        className="rounded border border-slate-200 px-2 py-0.5 text-xs text-slate-600 transition hover:bg-slate-100"
                      >
                        Diff
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {priority.items.length === 0 && (
        <Card className="text-center">
          <p className="text-sm text-slate-500">No priority items detected for this PR.</p>
        </Card>
      )}
    </div>
  );
}
