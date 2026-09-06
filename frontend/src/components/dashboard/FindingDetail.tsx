"use client";

import { SeverityBadge, CategoryBadge } from "@/components/ui/Badge";
import { SeverityDot } from "@/components/ui/SeverityIcon";
import type { Finding, Phase4Result } from "@/types/analysis";

export function FindingDetail({
  finding,
  analysis,
  onClose,
  onViewDiff,
}: {
  finding: Finding;
  analysis: Phase4Result;
  onClose: () => void;
  onViewDiff: () => void;
}) {
  // Find AI explanation for this finding
  const aiExplanation = analysis.ai_insights.finding_explanations.find(
    (e) => e.finding_id === finding.id
  );

  // Find connected files from impact map
  const connectedFiles = analysis.analysis.change.functional_areas
    .filter((area) => finding.file && area.files.includes(finding.file))
    .flatMap((area) => area.files.filter((f) => f !== finding.file));

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Issue Details</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {/* Severity + category */}
          <div className="mb-4 flex items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <CategoryBadge category={finding.category} />
            <span className="text-xs text-slate-400" title="How confident CodeLens is about this finding">
              confidence: {finding.confidence}
            </span>
          </div>

          {/* Title */}
          <h1 className="text-lg font-bold tracking-tight text-slate-900">{finding.title}</h1>

          {/* Location */}
          {finding.file && (
            <div className="mt-2 flex items-center gap-2">
              <SeverityDot severity={finding.severity} />
              <span className="font-mono text-sm text-slate-600">{finding.file}</span>
              {finding.line_range && (
                <span className="font-mono text-xs text-slate-400">
                  · L{finding.line_range[0]}-{finding.line_range[1]}
                </span>
              )}
            </div>
          )}

          {/* What changed */}
          <Section label="What Changed">
            <p className="text-sm leading-relaxed text-slate-600">{finding.what_changed}</p>
          </Section>

          {/* Why it matters */}
          <Section label="Why This Matters">
            <p className="text-sm leading-relaxed text-slate-600">{finding.why_it_matters}</p>
          </Section>

          {/* Evidence */}
          <Section label="Evidence (code snippets that triggered this)">
            <ul className="space-y-1.5">
              {finding.evidence.map((ev, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="font-mono text-xs leading-relaxed">{ev}</span>
                </li>
              ))}
            </ul>
          </Section>

          {/* AI explanation */}
          {aiExplanation && (
            <Section label="AI Explanation">
              <p className="text-sm leading-relaxed text-slate-600">{aiExplanation.explanation}</p>
              {aiExplanation.is_inference && (
                <p className="mt-2 text-xs italic text-amber-600">
                  This is an AI-generated explanation — please verify it before acting.
                </p>
              )}
            </Section>
          )}

          {/* Connected files */}
          {connectedFiles.length > 0 && (
            <Section label="Related Files (in the same area)">
              <ul className="space-y-1">
                {Array.from(new Set(connectedFiles)).map((file) => (
                  <li key={file} className="flex items-center gap-2 font-mono text-xs text-slate-600">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
                    {file}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t border-slate-200 px-5 py-3">
          {finding.file && (
            <button
              onClick={onViewDiff}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h8m-8 5h8m-8 5h8M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
              </svg>
              View Code Changes
            </button>
          )}
        </div>
      </div>
    </>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</h3>
      {children}
    </div>
  );
}
