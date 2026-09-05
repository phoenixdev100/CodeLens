"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Please paste a GitHub Pull Request URL.");
      return;
    }
    setError(null);
    router.push(`/dashboard?pr=${encodeURIComponent(trimmed)}`);
  }

  function handleDemo() {
    setError(null);
    router.push(`/dashboard?demo=1`);
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-slate-50 px-6 py-20">
      <main className="flex w-full max-w-2xl flex-col items-center text-center">
        {/* Logo */}
        <div className="mb-8 flex items-center gap-2.5">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            CL
          </span>
          <span className="text-2xl font-semibold tracking-tight text-slate-900">CodeLens</span>
        </div>

        {/* Headline */}
        <h1 className="mb-4 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Understand your PR
          <br />
          before you review it.
        </h1>

        <p className="mb-10 max-w-lg text-base text-slate-500">
          Paste a GitHub Pull Request URL. CodeLens analyzes the change, identifies
          risk, maps affected files, and shows where you should focus your review.
        </p>

        {/* Input form */}
        <form onSubmit={handleSubmit} className="flex w-full flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo/pull/123"
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            autoFocus
          />
          <button
            type="submit"
            className="rounded-lg bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-500 active:bg-indigo-700"
          >
            Analyze PR
          </button>
        </form>

        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}

        {/* Demo link */}
        <button
          onClick={handleDemo}
          className="mt-4 text-sm text-slate-400 transition hover:text-slate-600"
        >
          or try a demo with sample data →
        </button>

        {/* Feature summary */}
        <div className="mt-16 grid w-full grid-cols-2 gap-4 sm:grid-cols-4">
          <FeatureCard
            icon="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            title="Change Understanding"
            desc="What changed and why"
          />
          <FeatureCard
            icon="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            title="Risk Analysis"
            desc="Six-dimension scoring"
          />
          <FeatureCard
            icon="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
            title="Impact Visualization"
            desc="Dependency graph"
          />
          <FeatureCard
            icon="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
            title="Review Prioritization"
            desc="Where to look first"
          />
        </div>

        <p className="mt-12 text-xs text-slate-400">
          CodeLens provides intelligence and prioritization — it does not replace human code review.
        </p>
      </main>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm">
      <svg className="mb-2 h-5 w-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
      </svg>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-0.5 text-xs text-slate-500">{desc}</p>
    </div>
  );
}
