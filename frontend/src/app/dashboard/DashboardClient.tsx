"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { fetchFullAnalysis, fetchImpactMap, analyzePR } from "@/lib/api";
import { mockPhase4Result, mockImpactMap, mockAnalyzeResponse } from "@/lib/mock-data";
import type { Phase4Result, AnalyzeResponse, Finding } from "@/types/analysis";
import type { ImpactMap } from "@/types/impact-map";

export type DashboardTab = "overview" | "risk" | "security" | "priority" | "findings" | "impact-map" | "diff";

interface DashboardData {
  analysis: Phase4Result;
  impactMap: ImpactMap | null;
  analyze: AnalyzeResponse | null;
}

type State =
  | { status: "loading"; stage: number }
  | { status: "error"; message: string; code: string }
  | { status: "success"; data: DashboardData; isMock: boolean };

const ANALYSIS_STAGES = [
  "Fetching Pull Request",
  "Reading changed files",
  "Building repository context",
  "Analyzing changes",
  "Checking critical areas",
  "Checking security",
  "Checking tests",
  "Calculating risk",
  "Generating AI insights",
];

export default function DashboardClient() {
  const params = useSearchParams();
  const prUrl = params.get("pr") ?? "";
  const demo = params.get("demo") === "1";
  const [state, setState] = useState<State>(() =>
    prUrl || demo ? { status: "loading", stage: 0 } : { status: "error", message: "No PR URL provided.", code: "no-url" }
  );
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Lazy-load states for impact map and diff data
  const [impactMapLoading, setImpactMapLoading] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);

  const fetchData = useCallback(async (url: string, isDemo: boolean, isCancelled?: () => boolean) => {
    const canSet = () => !isCancelled?.();

    if (isDemo) {
      // Demo mode — all data is instant (mock)
      for (let i = 0; i < ANALYSIS_STAGES.length; i++) {
        if (!canSet()) return;
        setState({ status: "loading", stage: i });
        await new Promise((r) => setTimeout(r, 200));
      }
      if (!canSet()) return;
      setState({
        status: "success",
        data: {
          analysis: mockPhase4Result,
          impactMap: mockImpactMap,
          analyze: mockAnalyzeResponse,
        },
        isMock: true,
      });
      return;
    }

    try {
      // Real fetch — ONLY fetch analyze-full initially (the main pipeline).
      // Impact map and diff data are loaded lazily when user visits those tabs.
      if (canSet()) setState({ status: "loading", stage: 0 });
      const analysis = await fetchFullAnalysis(url);
      if (!canSet()) return;
      setState({
        status: "success",
        data: { analysis, impactMap: null, analyze: null },
        isMock: false,
      });
    } catch (err: unknown) {
      if (!canSet()) return;
      const error = err as Error;
      const msg = error.message || "Unknown error";

      let code = "api-error";
      if (msg.includes("auth") || msg.includes("401") || msg.includes("403")) code = "auth";
      else if (msg.includes("404")) code = "not-found";
      else if (msg.includes("502") || msg.includes("GitHub")) code = "github";

      if (msg.includes("502") || msg.includes("auth")) {
        setState({
          status: "success",
          data: {
            analysis: mockPhase4Result,
            impactMap: mockImpactMap,
            analyze: mockAnalyzeResponse,
          },
          isMock: true,
        });
        return;
      }

      setState({ status: "error", message: msg, code });
    }
  }, []);

  useEffect(() => {
    if (!prUrl && !demo) return;
    let cancelled = false;
    const run = async () => {
      await fetchData(prUrl, demo, () => cancelled);
    };
    run();
    return () => { cancelled = true; };
  }, [prUrl, demo, fetchData]);

  // Lazy-load impact map when user visits the Impact Map tab
  const loadImpactMap = useCallback(async () => {
    if (state.status !== "success" || state.data.impactMap || state.isMock || impactMapLoading) return;
    setImpactMapLoading(true);
    try {
      const impactMap = await fetchImpactMap(prUrl);
      setState((prev) =>
        prev.status === "success"
          ? { ...prev, data: { ...prev.data, impactMap } }
          : prev
      );
    } catch {
      // Fallback to mock if impact map fails
      setState((prev) =>
        prev.status === "success"
          ? { ...prev, data: { ...prev.data, impactMap: mockImpactMap } }
          : prev
      );
    } finally {
      setImpactMapLoading(false);
    }
  }, [state, prUrl, impactMapLoading]);

  // Lazy-load diff data when user visits the Diff tab
  const loadDiffData = useCallback(async () => {
    if (state.status !== "success" || state.data.analyze || state.isMock || diffLoading) return;
    setDiffLoading(true);
    try {
      const analyze = await analyzePR(prUrl);
      setState((prev) =>
        prev.status === "success"
          ? { ...prev, data: { ...prev.data, analyze } }
          : prev
      );
    } catch {
      setState((prev) =>
        prev.status === "success"
          ? { ...prev, data: { ...prev.data, analyze: mockAnalyzeResponse } }
          : prev
      );
    } finally {
      setDiffLoading(false);
    }
  }, [state, prUrl, diffLoading]);

  // Trigger lazy loads when tab changes
  const handleTabChange = useCallback((tab: DashboardTab) => {
    setActiveTab(tab);
    if (tab === "impact-map") loadImpactMap();
    if (tab === "diff") loadDiffData();
  }, [loadImpactMap, loadDiffData]);

  const selectedFinding = useMemo<Finding | null>(() => {
    if (!selectedFindingId || state.status !== "success") return null;
    return state.data.analysis.analysis.all_findings.find((f) => f.id === selectedFindingId) ?? null;
  }, [selectedFindingId, state]);

  const handleSelectFinding = useCallback((id: string) => {
    setSelectedFindingId(id);
  }, []);

  const handleCloseFinding = useCallback(() => {
    setSelectedFindingId(null);
  }, []);

  const handleSelectFile = useCallback((file: string) => {
    setSelectedFile(file);
    setActiveTab("diff");
    loadDiffData();
  }, [loadDiffData]);

  if (state.status === "loading") {
    return <LoadingScreen stages={ANALYSIS_STAGES} currentStage={state.stage} prUrl={prUrl} />;
  }

  if (state.status === "error") {
    return <ErrorScreen message={state.message} code={state.code} />;
  }

  const { data, isMock } = state;

  return (
    <DashboardShell
      analysis={data.analysis}
      impactMap={data.impactMap}
      analyze={data.analyze}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      isMock={isMock}
      selectedFinding={selectedFinding}
      onSelectFinding={handleSelectFinding}
      onCloseFinding={handleCloseFinding}
      onSelectFile={handleSelectFile}
      selectedFile={selectedFile}
      impactMapLoading={impactMapLoading}
      diffLoading={diffLoading}
    />
  );
}

function LoadingScreen({ stages, currentStage, prUrl }: { stages: string[]; currentStage: number; prUrl: string }) {
  return (
    <div className="flex flex-1 items-center justify-center bg-slate-50 px-6 py-20">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-4 flex items-center justify-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              CL
            </span>
            <span className="text-xl font-semibold tracking-tight text-slate-900">CodeLens</span>
          </div>
          <h2 className="text-lg font-semibold text-slate-900">Analyzing Pull Request</h2>
          <p className="mt-1 break-all text-xs text-slate-400">{prUrl}</p>
        </div>
        <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {stages.map((stage, i) => {
            const isDone = i < currentStage;
            const isActive = i === currentStage;
            return (
              <div key={stage} className="flex items-center gap-3 text-sm">
                <span className="flex h-5 w-5 items-center justify-center">
                  {isDone ? (
                    <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isActive ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-500" />
                  ) : (
                    <div className="h-2 w-2 rounded-full border border-slate-300" />
                  )}
                </span>
                <span className={isDone ? "text-slate-400 line-through" : isActive ? "font-medium text-slate-900" : "text-slate-400"}>
                  {stage}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ErrorScreen({ message, code }: { message: string; code: string }) {
  const titles: Record<string, string> = {
    "no-url": "No PR URL Provided",
    auth: "GitHub Authentication Failed",
    "not-found": "Repository Not Found",
    github: "GitHub API Error",
    "api-error": "Analysis Failed",
  };
  const title = titles[code] ?? "Analysis Failed";

  return (
    <div className="flex flex-1 items-center justify-center bg-slate-50 px-6 py-20">
      <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mb-4 flex justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <svg className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        </div>
        <h2 className="mb-2 text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mb-6 text-sm text-slate-500">{message}</p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
        >
          &larr; Back to input
        </Link>
      </div>
    </div>
  );
}
