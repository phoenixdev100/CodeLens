"use client";

import Link from "next/link";

import type { DashboardTab } from "@/app/dashboard/DashboardClient";
import { RiskLevelBadge } from "@/components/ui/Badge";
import type { Phase4Result, AnalyzeResponse, Finding } from "@/types/analysis";
import type { ImpactMap } from "@/types/impact-map";

import { OverviewPanel } from "./OverviewPanel";
import { RiskBreakdownPanel } from "./RiskBreakdownPanel";
import { ReviewPriorityPanel } from "./ReviewPriorityPanel";
import { FindingsPanel } from "./FindingsPanel";
import { ImpactMapPanel } from "./ImpactMapPanel";
import { DiffPanel } from "./DiffPanel";
import { FindingDetail } from "./FindingDetail";
import { SecurityPanel } from "./SecurityPanel";

const NAV_ITEMS: { id: DashboardTab; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { id: "risk", label: "Risk Analysis", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { id: "security", label: "Security", icon: "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" },
  { id: "priority", label: "Review Priority", icon: "M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" },
  { id: "findings", label: "Findings", icon: "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" },
  { id: "impact-map", label: "Impact Map", icon: "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" },
  { id: "diff", label: "Diff", icon: "M8 7h8m-8 5h8m-8 5h8M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" },
];

export function DashboardShell({
  analysis,
  impactMap,
  analyze,
  activeTab,
  onTabChange,
  isMock,
  selectedFinding,
  onSelectFinding,
  onCloseFinding,
  onSelectFile,
  selectedFile,
  impactMapLoading,
  diffLoading,
}: {
  analysis: Phase4Result;
  impactMap: ImpactMap | null;
  analyze: AnalyzeResponse | null;
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
  isMock: boolean;
  selectedFinding: Finding | null;
  onSelectFinding: (id: string) => void;
  onCloseFinding: () => void;
  onSelectFile: (file: string) => void;
  selectedFile: string | null;
  impactMapLoading?: boolean;
  diffLoading?: boolean;
}) {
  const { meta, risk } = analysis;

  return (
    <div className="flex flex-1 flex-col bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-xs font-bold text-white">
                CL
              </span>
              <span className="text-lg font-semibold tracking-tight text-slate-900">CodeLens</span>
            </Link>
            <div className="hidden items-center gap-3 border-l border-slate-200 pl-6 md:flex">
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-slate-900">
                  {meta.title}
                </span>
                <span className="text-xs text-slate-500">
                  {meta.owner}/{meta.repo} #{meta.number}
                  {meta.author && ` · ${meta.author}`}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {isMock && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                Demo Mode
              </span>
            )}
            <RiskLevelBadge level={risk.level} score={risk.total_score} />
            <a
              href={meta.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 transition hover:text-slate-600"
              title="View on GitHub"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
            <Link
              href="/"
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              New Analysis
            </Link>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <nav className="sticky top-16 hidden h-[calc(100vh-4rem)] w-56 shrink-0 border-r border-slate-200 bg-white py-4 md:block">
          <ul className="space-y-1 px-3">
            {NAV_ITEMS.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => onTabChange(item.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    activeTab === item.id
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                  </svg>
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-6 px-4">
            <p className="text-[10px] leading-relaxed text-slate-400">
              CodeLens provides intelligence and prioritization. It does not replace human code review.
            </p>
          </div>
        </nav>

        {/* Mobile nav */}
        <div className="absolute left-0 right-0 top-16 z-20 md:hidden">
          <div className="flex overflow-x-auto border-b border-slate-200 bg-white px-2">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`whitespace-nowrap px-3 py-2.5 text-xs font-medium transition ${
                  activeTab === item.id ? "border-b-2 border-indigo-500 text-indigo-700" : "text-slate-500"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Main content */}
        <main className="flex-1 overflow-x-hidden px-4 pt-14 md:px-8 md:pt-6">
          <div className="mx-auto max-w-6xl py-6">
            {activeTab === "overview" && (
              <OverviewPanel
                analysis={analysis}
                impactMap={impactMap}
                onTabChange={onTabChange}
                onSelectFinding={onSelectFinding}
                onSelectFile={onSelectFile}
              />
            )}
            {activeTab === "risk" && <RiskBreakdownPanel analysis={analysis} />}
            {activeTab === "security" && (
              <SecurityPanel
                analysis={analysis}
                onSelectFinding={onSelectFinding}
              />
            )}
            {activeTab === "priority" && (
              <ReviewPriorityPanel
                analysis={analysis}
                onSelectFinding={onSelectFinding}
                onSelectFile={onSelectFile}
              />
            )}
            {activeTab === "findings" && (
              <FindingsPanel
                analysis={analysis}
                onSelectFinding={onSelectFinding}
              />
            )}
            {activeTab === "impact-map" && (
              impactMap ? (
                <ImpactMapPanel data={impactMap} />
              ) : impactMapLoading ? (
                <TabLoading label="Building Impact Map" />
              ) : (
                <TabLoading label="Loading Impact Map" />
              )
            )}
            {activeTab === "diff" && (
              analyze ? (
                <DiffPanel
                  analyze={analyze}
                  analysis={analysis}
                  selectedFile={selectedFile}
                />
              ) : diffLoading ? (
                <TabLoading label="Fetching PR files & diffs" />
              ) : (
                <TabLoading label="Loading diff data" />
              )
            )}
          </div>
        </main>
      </div>

      {/* Finding detail drawer */}
      {selectedFinding && (
        <FindingDetail
          finding={selectedFinding}
          analysis={analysis}
          onClose={onCloseFinding}
          onViewDiff={() => {
            if (selectedFinding.file) {
              onSelectFile(selectedFinding.file);
            }
          }}
        />
      )}
    </div>
  );
}

function TabLoading({ label }: { label: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-3">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-500" />
      <p className="text-sm text-slate-500">{label}...</p>
    </div>
  );
}
