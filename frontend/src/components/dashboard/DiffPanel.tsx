"use client";

import { useMemo, useState, useRef } from "react";

import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { SeverityDot } from "@/components/ui/SeverityIcon";
import type { AnalyzeResponse, Phase4Result } from "@/types/analysis";

export function DiffPanel({
  analyze,
  analysis,
  selectedFile,
}: {
  analyze: AnalyzeResponse;
  analysis: Phase4Result;
  selectedFile: string | null;
}) {
  const files = analyze.files;
  const [internalActiveFile, setInternalActiveFile] = useState<string | null>(null);

  // Use selectedFile if provided, otherwise fall back to internal state
  const activeFile = selectedFile ?? internalActiveFile ?? files[0]?.filename ?? null;

  const activeFileData = useMemo(
    () => files.find((f) => f.filename === activeFile) ?? null,
    [files, activeFile]
  );

  // Build a map of file -> severity from findings
  const fileSeverity = useMemo(() => {
    const m = new Map<string, string>();
    for (const f of analysis.analysis.all_findings) {
      if (f.file) {
        const existing = m.get(f.file);
        if (!existing || severityRank(f.severity) > severityRank(existing)) {
          m.set(f.file, f.severity);
        }
      }
    }
    return m;
  }, [analysis]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Diff</h1>
        <p className="mt-1 text-sm text-slate-500">
          {files.length} changed file(s). Click a file to view its diff.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-[240px_1fr]">
        {/* File sidebar */}
        <Card padding="none" className="h-fit">
          <div className="border-b border-slate-200 px-3 py-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Changed Files</h3>
          </div>
          <ul className="max-h-[600px] divide-y divide-slate-100 overflow-y-auto">
            {files.map((file) => {
              const sev = fileSeverity.get(file.filename);
              const isActive = activeFile === file.filename;
              return (
                <li key={file.filename}>
                  <button
                    onClick={() => setInternalActiveFile(file.filename)}
                    className={`flex w-full items-center gap-2 px-3 py-2 text-left transition ${
                      isActive ? "bg-indigo-50" : "hover:bg-slate-50"
                    }`}
                  >
                    <SeverityDot severity={sev as never} />
                    <div className="flex-1 min-w-0">
                      <p className="truncate font-mono text-xs text-slate-700">{file.filename}</p>
                      <p className="text-[10px] text-slate-400">
                        +{file.additions} -{file.deletions}
                      </p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>

        {/* Diff content */}
        <Card padding="none" className="min-w-0">
          {activeFileData ? (
            <DiffContent file={activeFileData} findings={analysis.analysis.all_findings.filter((f) => f.file === activeFileData.filename)} />
          ) : (
            <div className="px-4 py-12 text-center text-sm text-slate-500">
              Select a file to view its diff.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function DiffContent({
  file,
  findings,
}: {
  file: { filename: string; status: string; additions: number; deletions: number; patch: string | null };
  findings: { id: string; title: string; line_range: [number, number] | null }[];
}) {
  const diffRef = useRef<HTMLDivElement>(null);
  const highlightLines = useMemo(() => {
    const lines = new Set<number>();
    for (const f of findings) {
      if (f.line_range) {
        for (let l = f.line_range[0]; l <= f.line_range[1]; l++) {
          lines.add(l);
        }
      }
    }
    return lines;
  }, [findings]);

  const parsedLines = useMemo(() => parseDiff(file.patch), [file]);

  return (
    <div ref={diffRef}>
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-medium text-slate-900">{file.filename}</span>
          <StatusBadge status={file.status} />
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="font-mono text-green-600">+{file.additions}</span>
          <span className="font-mono text-red-600">-{file.deletions}</span>
        </div>
      </div>

      {/* Finding markers */}
      {findings.length > 0 && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2">
          <p className="text-xs font-medium text-amber-700">
            {findings.length} finding(s) on this file:
          </p>
          <ul className="mt-1 space-y-0.5">
            {findings.map((f) => (
              <li key={f.id} className="text-xs text-amber-600">
                • {f.title}
                {f.line_range && ` (L${f.line_range[0]}-${f.line_range[1]})`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Diff lines */}
      <div className="overflow-x-auto">
        <pre className="text-xs leading-relaxed">
          <code className="block">
            {parsedLines.length === 0 ? (
              <div className="px-4 py-8 text-center text-slate-400">
                Diff not available for this file.
              </div>
            ) : (
              parsedLines.map((line, i) => (
                <div
                  key={i}
                  className={`flex px-0 ${
                    line.type === "add"
                      ? "bg-green-50"
                      : line.type === "del"
                      ? "bg-red-50"
                      : line.type === "hunk"
                      ? "bg-slate-100 text-slate-500"
                      : ""
                  } ${highlightLines.has(line.lineNumber ?? 0) ? "border-l-2 border-amber-400" : ""}`}
                >
                  <span className="w-12 shrink-0 select-none px-2 text-right text-slate-300">
                    {line.lineNumber ?? ""}
                  </span>
                  <span
                    className={`w-6 shrink-0 select-none px-1 text-center ${
                      line.type === "add"
                        ? "text-green-600"
                        : line.type === "del"
                        ? "text-red-600"
                        : "text-slate-300"
                    }`}
                  >
                    {line.type === "add" ? "+" : line.type === "del" ? "-" : line.type === "hunk" ? "@" : " "}
                  </span>
                  <span
                    className={`flex-1 whitespace-pre px-2 ${
                      line.type === "add"
                        ? "text-green-800"
                        : line.type === "del"
                        ? "text-red-800"
                        : line.type === "hunk"
                        ? "text-slate-500"
                        : "text-slate-700"
                    }`}
                  >
                    {line.content}
                  </span>
                </div>
              ))
            )}
          </code>
        </pre>
      </div>
    </div>
  );
}

interface DiffLine {
  type: "add" | "del" | "ctx" | "hunk" | "meta";
  content: string;
  lineNumber: number | null;
}

function parseDiff(patch: string | null): DiffLine[] {
  if (!patch) return [];
  const lines = patch.split("\n");
  const result: DiffLine[] = [];
  let newLineNum = 0;

  for (const line of lines) {
    if (line.startsWith("@@")) {
      // Extract new start line from hunk header
      const match = line.match(/\+(\d+)/);
      newLineNum = match ? parseInt(match[1], 10) - 1 : 0;
      result.push({ type: "hunk", content: line, lineNumber: null });
    } else if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("diff ") || line.startsWith("index ")) {
      result.push({ type: "meta", content: line, lineNumber: null });
    } else if (line.startsWith("+")) {
      newLineNum++;
      result.push({ type: "add", content: line.slice(1), lineNumber: newLineNum });
    } else if (line.startsWith("-")) {
      result.push({ type: "del", content: line.slice(1), lineNumber: null });
    } else if (line.startsWith(" ")) {
      newLineNum++;
      result.push({ type: "ctx", content: line.slice(1), lineNumber: newLineNum });
    } else if (line.trim()) {
      result.push({ type: "ctx", content: line, lineNumber: null });
    }
  }

  return result;
}

function severityRank(s: string): number {
  return { critical: 5, high: 4, medium: 3, low: 2, info: 1 }[s] ?? 0;
}
