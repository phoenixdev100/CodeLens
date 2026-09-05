"use client";

import type { DashboardTab } from "@/app/dashboard/DashboardClient";
import { Card, CardHeader } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/Badge";
import { RiskMeter, RiskBar } from "@/components/ui/RiskMeter";
import { SeverityDot } from "@/components/ui/SeverityIcon";
import type { Phase4Result } from "@/types/analysis";
import type { ImpactMap } from "@/types/impact-map";

export function OverviewPanel({
  analysis,
  impactMap,
  onTabChange,
  onSelectFinding,
  onSelectFile,
}: {
  analysis: Phase4Result;
  impactMap: ImpactMap | null;
  onTabChange: (tab: DashboardTab) => void;
  onSelectFinding: (id: string) => void;
  onSelectFile: (file: string) => void;
}) {
  const { meta, risk, priority, ai_insights, analysis: result } = analysis;
  const { change } = result;
  const topFindings = [...result.all_findings]
    .sort((a, b) => severityRank(b.severity) - severityRank(a.severity))
    .slice(0, 4);
  const topPriority = priority.items.slice(0, 5);

  return (
    <div className="space-y-6">
      {/* PR title + risk hero */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">{meta.title}</h1>
              <p className="mt-1 text-sm text-slate-500">
                {meta.owner}/{meta.repo} · PR #{meta.number}
                {meta.author && ` · ${meta.author}`}
                {meta.head_branch && ` · ${meta.head_branch} → ${meta.base_branch ?? "main"}`}
              </p>
              {meta.body && (
                <p className="mt-3 line-clamp-2 text-sm text-slate-600">{meta.body}</p>
              )}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {change.size_class.toUpperCase()} PR
            </span>
            {change.scope_drift.has_drift && (
              <span className="rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-xs font-medium text-orange-700">
                Scope Drift
              </span>
            )}
            {result.critical.areas.length > 0 && (
              <span className="rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
                {result.critical.areas.length} Critical Area{result.critical.areas.length > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </Card>

        <Card className="flex flex-col items-center justify-center">
          <RiskMeter score={risk.total_score} level={risk.level} size="md" />
          <p className="mt-3 text-center text-[10px] text-slate-400">
            MVP heuristic — not scientifically validated
          </p>
        </Card>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Files Changed" value={change.files_changed} />
        <StatCard label="Additions" value={`+${formatNum(change.lines_added)}`} color="text-green-600" />
        <StatCard label="Deletions" value={`-${formatNum(change.lines_removed)}`} color="text-red-600" />
        <StatCard label="PR Size" value={change.size_class.toUpperCase()} />
      </div>

      {/* Project context */}
      {result.project_context && result.project_context.name && (
        <Card>
          <CardHeader
            title="Project Context"
            subtitle={`What this project is — fetched from README & package files`}
          />
          <div className="space-y-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">
                {result.project_context.name}
              </p>
              {result.project_context.description && (
                <p className="mt-1 text-sm text-slate-600">
                  {result.project_context.description}
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {result.project_context.language && (
                <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
                  {result.project_context.language}
                </span>
              )}
              {result.project_context.tech_stack.map((tech) => (
                <span
                  key={tech}
                  className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600"
                >
                  {tech}
                </span>
              ))}
              {result.project_context.package_info.framework && (
                <span className="rounded-full border border-purple-200 bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700">
                  {result.project_context.package_info.framework}
                </span>
              )}
            </div>
            {result.project_context.key_directories.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-400">Key directories touched:</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {result.project_context.key_directories.map((dir) => (
                    <span
                      key={dir}
                      className="rounded bg-slate-50 px-2 py-0.5 font-mono text-[11px] text-slate-500"
                    >
                      {dir}/
                    </span>
                  ))}
                </div>
              </div>
            )}
            {result.project_context.readme_excerpt && (
              <details className="group">
                <summary className="cursor-pointer text-xs font-medium text-indigo-600 hover:text-indigo-700">
                  Show README excerpt
                </summary>
                <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-600 whitespace-pre-wrap">
                  {result.project_context.readme_excerpt}
                </pre>
              </details>
            )}
          </div>
        </Card>
      )}

      {/* Affected areas + risk contributors */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title="Affected Areas" subtitle={`${change.functional_areas.length} functional area(s) detected`} />
          <div className="flex flex-wrap gap-2">
            {change.functional_areas.map((area) => {
              const isCritical = result.critical.areas.some((ca) => ca.name === area.name);
              return (
                <button
                  key={area.name}
                  onClick={() => onTabChange("impact-map")}
                  className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition hover:shadow-sm ${
                    isCritical
                      ? "border-red-200 bg-red-50 text-red-700"
                      : "border-slate-200 bg-slate-50 text-slate-700"
                  }`}
                >
                  <SeverityDot severity={isCritical ? "critical" : null} />
                  <span className="capitalize">{area.name}</span>
                  <span className="text-xs text-slate-400">{area.files.length} file{area.files.length > 1 ? "s" : ""}</span>
                </button>
              );
            })}
          </div>
          {change.scope_drift.has_drift && (
            <div className="mt-3 rounded-md border border-orange-200 bg-orange-50 p-2.5 text-xs text-orange-700">
              <strong>Scope drift:</strong> PR title suggests {change.scope_drift.stated_areas.join(", ") || "specific areas"},
              but changes touch {change.scope_drift.actual_areas.join(", ")}.
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Top Risk Contributors" subtitle="Factors driving the risk score" />
          <ul className="space-y-2">
            {risk.top_contributors.slice(0, 4).map((contrib, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                <span className="leading-relaxed">{contrib}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Risk breakdown preview */}
      <Card>
        <CardHeader
          title="Risk Analysis"
          subtitle="Six-dimension risk breakdown"
          action={
            <button
              onClick={() => onTabChange("risk")}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
            >
              View details →
            </button>
          }
        />
        <div className="grid gap-4 md:grid-cols-2">
          {risk.dimension_scores.map((dim) => (
            <RiskBar
              key={dim.dimension}
              label={formatDimension(dim.dimension)}
              rawScore={dim.raw_score}
              weight={dim.weight}
              weightedScore={dim.weighted_score}
            />
          ))}
        </div>
      </Card>

      {/* Review priority + top findings */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader
            title="Review First"
            subtitle="Where to focus your review"
            action={
              <button
                onClick={() => onTabChange("priority")}
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                All →
              </button>
            }
          />
          <div className="space-y-1.5">
            {topPriority.map((item) => (
              <button
                key={item.rank}
                onClick={() => onSelectFile(item.file)}
                className="flex w-full items-center gap-3 rounded-lg border border-slate-100 px-3 py-2 text-left transition hover:border-slate-200 hover:bg-slate-50"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">
                  {item.rank}
                </span>
                <SeverityDot severity={item.severity} />
                <span className="flex-1 truncate font-mono text-xs text-slate-700">{item.file}</span>
                <span className="font-mono text-sm font-bold text-slate-900">{item.score}</span>
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Top Findings"
            subtitle={`${result.all_findings.length} total finding(s)`}
            action={
              <button
                onClick={() => onTabChange("findings")}
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                All →
              </button>
            }
          />
          <div className="space-y-2">
            {topFindings.map((finding) => (
              <button
                key={finding.id}
                onClick={() => onSelectFinding(finding.id)}
                className="flex w-full items-start gap-3 rounded-lg border border-slate-100 px-3 py-2 text-left transition hover:border-slate-200 hover:bg-slate-50"
              >
                <div className="flex shrink-0 flex-col items-center gap-1">
                  <SeverityBadge severity={finding.severity} size="xs" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{finding.title}</p>
                  <p className="mt-0.5 truncate font-mono text-xs text-slate-400">
                    {finding.file ?? "PR-wide"}
                    {finding.line_range && ` · L${finding.line_range[0]}-${finding.line_range[1]}`}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* AI insights */}
      <Card>
        <CardHeader
          title="AI Interpretation"
          subtitle={`Provider: ${ai_insights.provider}`}
        />
        <div className="space-y-3 text-sm text-slate-600">
          <div>
            <span className="font-semibold text-slate-700">PR Intent: </span>
            {ai_insights.pr_intent}
          </div>
          <div>
            <span className="font-semibold text-slate-700">Risk Reasoning: </span>
            {ai_insights.risk_reasoning}
          </div>
        </div>
        <p className="mt-3 text-[10px] text-slate-400">{ai_insights.disclaimer}</p>
      </Card>

      {/* Impact map preview */}
      <Card padding="none">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Impact Map Preview</h3>
            <p className="mt-0.5 text-xs text-slate-500">
              {impactMap
                ? `${impactMap.stats.total_nodes ?? 0} nodes · ${impactMap.stats.total_edges ?? 0} edges`
                : "Click to load impact map"}
            </p>
          </div>
          <button
            onClick={() => onTabChange("impact-map")}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
          >
            Open map →
          </button>
        </div>
        <div className="flex flex-wrap gap-3 p-4">
          {impactMap ? (
            impactMap.nodes.filter((n) => n.type !== "area").slice(0, 8).map((node) => (
              <div
                key={node.id}
                className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs ${
                  node.changed ? "border-slate-300 bg-white" : "border-slate-100 bg-slate-50"
                }`}
              >
                <SeverityDot severity={node.severity} />
                <span className="font-mono text-slate-600">{node.label}</span>
                {node.changed && <span className="text-amber-600">*</span>}
              </div>
            ))
          ) : (
            <button
              onClick={() => onTabChange("impact-map")}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 py-6 text-sm text-slate-400 transition hover:border-indigo-300 hover:text-indigo-500"
            >
              Load Impact Map →
            </button>
          )}
        </div>
      </Card>
    </div>
  );
}

function StatCard({ label, value, color = "text-slate-900" }: { label: string; value: string | number; color?: string }) {
  return (
    <Card padding="sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
    </Card>
  );
}

function severityRank(s: string): number {
  return { critical: 5, high: 4, medium: 3, low: 2, info: 1 }[s] ?? 0;
}

function formatNum(n: number): string {
  return n.toLocaleString();
}

function formatDimension(d: string): string {
  const labels: Record<string, string> = {
    change: "Change Size",
    scope: "Scope / Drift",
    critical: "Critical Functionality",
    security: "Security",
    quality: "Code Quality",
    tests: "Tests",
  };
  return labels[d] ?? d;
}
