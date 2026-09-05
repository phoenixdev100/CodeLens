import type { AnalyzeResponse, ErrorResponse, HealthResponse } from "@/types";
import type { ImpactMap } from "@/types/impact-map";
import type { Phase4Result } from "@/types/analysis";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/api/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

export async function analyzePR(prUrl: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl }),
    cache: "no-store",
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = data as ErrorResponse | null;
    const message =
      err?.detail || err?.error || `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return data as AnalyzeResponse;
}

export async function fetchFullAnalysis(prUrl: string): Promise<Phase4Result> {
  const res = await fetch(`${API_URL}/api/analyze-full`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl }),
    cache: "no-store",
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = data as ErrorResponse | null;
    const message =
      err?.detail || err?.error || `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return data as Phase4Result;
}

export async function fetchImpactMap(prUrl: string): Promise<ImpactMap> {
  const res = await fetch(`${API_URL}/api/impact-map`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl }),
    cache: "no-store",
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = data as ErrorResponse | null;
    const message =
      err?.detail || err?.error || `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return data as ImpactMap;
}
