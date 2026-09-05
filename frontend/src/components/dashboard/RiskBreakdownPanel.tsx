"use client";

import { Card, CardHeader } from "@/components/ui/Card";
import { RiskMeter, RiskBar } from "@/components/ui/RiskMeter";
import type { Phase4Result } from "@/types/analysis";

export function RiskBreakdownPanel({ analysis }: { analysis: Phase4Result }) {
  const { risk, ai_insights } = analysis;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Risk Analysis</h1>
        <p className="mt-1 text-sm text-slate-500">
          Explainable risk score based on six weighted dimensions.
        </p>
      </div>

      {/* Risk hero */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="flex flex-col items-center justify-center">
          <RiskMeter score={risk.total_score} level={risk.level} size="lg" />
        </Card>

        <Card className="md:col-span-2">
          <CardHeader title="Top Risk Contributors" subtitle="Primary factors driving the score" />
          <ul className="space-y-3">
            {risk.top_contributors.map((contrib, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                <span className="leading-relaxed">{contrib}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Dimension breakdown */}
      <Card>
        <CardHeader title="Risk Dimensions" subtitle="Raw scores (0-100) with configurable weights" />
        <div className="grid gap-5 md:grid-cols-2">
          {risk.dimension_scores.map((dim) => (
            <div key={dim.dimension} className="space-y-2">
              <RiskBar
                label={formatDimension(dim.dimension)}
                rawScore={dim.raw_score}
                weight={dim.weight}
                weightedScore={dim.weighted_score}
              />
              {dim.contributing_factors.length > 0 && (
                <ul className="ml-4 space-y-0.5 text-xs text-slate-400">
                  {dim.contributing_factors.map((factor, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-slate-300" />
                      {factor}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* AI risk reasoning */}
      <Card>
        <CardHeader title="AI Risk Reasoning" subtitle={`Provider: ${ai_insights.provider}`} />
        <p className="text-sm leading-relaxed text-slate-600">{ai_insights.risk_reasoning}</p>
        {ai_insights.scope_drift_reasoning && (
          <div className="mt-4 rounded-md border border-orange-200 bg-orange-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-orange-700">Scope Drift Assessment</p>
            <p className="mt-1 text-sm text-orange-800">{ai_insights.scope_drift_reasoning.assessment}</p>
          </div>
        )}
        <p className="mt-3 text-[10px] text-slate-400">{ai_insights.disclaimer}</p>
      </Card>

      {/* Disclaimer */}
      <Card className="border-amber-200 bg-amber-50">
        <p className="text-xs text-amber-800">
          <strong>Disclaimer:</strong> {risk.disclaimer}
        </p>
      </Card>
    </div>
  );
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
