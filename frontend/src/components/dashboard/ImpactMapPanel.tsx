"use client";

import dynamic from "next/dynamic";
import { Card } from "@/components/ui/Card";
import type { ImpactMap } from "@/types/impact-map";

const ImpactMapFlow = dynamic(() => import("@/app/impact-map/ImpactMapFlow"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[600px] items-center justify-center">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
    </div>
  ),
});

export function ImpactMapPanel({ data }: { data: ImpactMap }) {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Impact Map</h1>
        <p className="mt-1 text-sm text-slate-500">
          Visual graph of changed files, dependencies, tests, and functional areas.
          Click a node for details. 1-hop blast radius.
        </p>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-3 text-xs">
        <StatBadge label="Nodes" value={data.stats.total_nodes ?? 0} />
        <StatBadge label="Edges" value={data.stats.total_edges ?? 0} />
        <StatBadge label="Changed" value={data.stats.changed_files ?? 0} color="text-amber-600" />
        <StatBadge label="High Risk" value={data.stats.red_nodes ?? 0} color="text-red-600" />
        <StatBadge label="Medium" value={data.stats.orange_nodes ?? 0} color="text-orange-600" />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
        {(Object.keys(data.legend) as Array<keyof typeof data.legend>).map((color) => (
          <div key={color} className="flex items-center gap-2">
            <span className={`inline-block h-3 w-3 rounded-full ${legendColorClass(color)}`} />
            <span>{data.legend[color]}</span>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-6 bg-slate-400" />
          <span>import</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-6 border-t-2 border-dashed border-blue-400" />
          <span>test</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-6 border-t-2 border-dotted border-purple-400" />
          <span>area</span>
        </div>
      </div>

      {/* React Flow canvas */}
      <Card padding="none" className="overflow-hidden">
        <ImpactMapFlow data={data} />
      </Card>

      <p className="text-xs text-slate-400">
        Immediate impact / dependency connections only (1-hop). This does not represent the complete system-wide blast radius.
      </p>
    </div>
  );
}

function StatBadge({ label, value, color = "text-slate-700" }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5">
      <span className="text-slate-400">{label}</span>
      <span className={`font-bold ${color}`}>{value}</span>
    </div>
  );
}

function legendColorClass(color: string): string {
  switch (color) {
    case "red": return "bg-red-500";
    case "orange": return "bg-orange-500";
    case "yellow": return "bg-yellow-500";
    case "green": return "bg-green-500";
    default: return "bg-slate-500";
  }
}
