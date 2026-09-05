"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  type Node,
  type NodeMouseHandler,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";

import type { ImpactMap, ImpactNode, RiskColor } from "@/types/impact-map";

// Light theme risk colors — subtle tinted backgrounds with colored borders
const RISK_COLORS: Record<RiskColor, { bg: string; border: string; text: string }> = {
  red: { bg: "#fef2f2", border: "#dc2626", text: "#991b1b" },
  orange: { bg: "#fff7ed", border: "#f97316", text: "#9a3412" },
  yellow: { bg: "#fefce8", border: "#eab308", text: "#854d0e" },
  green: { bg: "#f0fdf4", border: "#22c55e", text: "#166534" },
};

const NODE_TYPE_LABELS: Record<string, string> = {
  source: "Source",
  test: "Test",
  config: "Config",
  area: "Area",
};

export default function ImpactMapFlow({ data }: { data: ImpactMap }) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: Node[] = data.nodes.map((n) => ({
      id: n.id,
      type: "default",
      position: { x: 0, y: 0 },
      data: { label: n.label, impact: n },
      style: nodeStyle(n),
    }));

    const edges: Edge[] = data.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: e.kind === "import",
      style: edgeStyle(e.kind),
    }));

    // Simple layout: group by functional area, place area nodes at top
    const areaNodes = nodes.filter(
      (n) => (n.data.impact as ImpactNode).type === "area"
    );
    const fileNodes = nodes.filter(
      (n) => (n.data.impact as ImpactNode).type !== "area"
    );

    // Place area nodes in a row at the top
    areaNodes.forEach((n, i) => {
      n.position = {
        x: 200 + i * 250,
        y: 50,
      };
    });

    // Place file nodes in a grid below
    const cols = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(fileNodes.length))));
    fileNodes.forEach((n, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      n.position = {
        x: 100 + col * 250,
        y: 200 + row * 150,
      };
    });

    return { initialNodes: [...areaNodes, ...fileNodes], initialEdges: edges };
  }, [data]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const selectedNode = useMemo(
    () => data.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [data, selectedNodeId]
  );

  const connectedNodeIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const ids = new Set<string>();
    for (const e of data.edges) {
      if (e.source === selectedNodeId) ids.add(e.target);
      if (e.target === selectedNodeId) ids.add(e.source);
    }
    return ids;
  }, [data.edges, selectedNodeId]);

  const handleNodeClick: NodeMouseHandler = (_event, node) => {
    setSelectedNodeId(node.id);
  };

  const handlePaneClick = () => {
    setSelectedNodeId(null);
  };

  // Apply highlighting when selection changes
  const highlightedNodes = useMemo(() => {
    if (!selectedNodeId) return nodes;
    return nodes.map((n) => {
      const isSelected = n.id === selectedNodeId;
      const isConnected = connectedNodeIds.has(n.id);
      const impact = n.data.impact as ImpactNode;
      const baseStyle = nodeStyle(impact);
      const colors = RISK_COLORS[impact.risk_color] ?? RISK_COLORS.green;
      return {
        ...n,
        style: {
          ...baseStyle,
          opacity: isSelected || isConnected ? 1 : 0.2,
          border: isSelected ? `3px solid ${colors.border}` : baseStyle.border,
          boxShadow: isSelected ? "0 0 0 3px rgba(99, 102, 241, 0.3)" : "none",
        },
      };
    });
  }, [nodes, selectedNodeId, connectedNodeIds]);

  const highlightedEdges = useMemo(() => {
    if (!selectedNodeId) return edges;
    return edges.map((e) => {
      const involves = e.source === selectedNodeId || e.target === selectedNodeId;
      return {
        ...e,
        style: {
          ...e.style,
          opacity: involves ? 1 : 0.08,
          strokeWidth: involves ? 2.5 : 1,
        },
      };
    });
  }, [edges, selectedNodeId]);

  return (
    <div className="flex h-[600px] w-full bg-white">
      <div className="relative flex-1">
        <ReactFlowProvider>
          <ReactFlow
            nodes={highlightedNodes}
            edges={highlightedEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            onPaneClick={handlePaneClick}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e2e8f0" />
            <Controls />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      {/* Detail panel */}
      {selectedNode && (
        <div className="w-72 shrink-0 overflow-y-auto border-l border-slate-200 bg-slate-50 p-4">
          <NodeDetail node={selectedNode} connectedIds={connectedNodeIds} allNodes={data.nodes} />
        </div>
      )}
    </div>
  );
}

function nodeStyle(n: ImpactNode): React.CSSProperties {
  const colors = RISK_COLORS[n.risk_color] ?? RISK_COLORS.green;
  return {
    background: colors.bg,
    border: `2px solid ${colors.border}`,
    color: colors.text,
    borderRadius: "8px",
    padding: "8px 12px",
    fontSize: "12px",
    fontWeight: n.changed ? 600 : 400,
    width: 180,
    textAlign: "center",
    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
  };
}

function edgeStyle(kind: string): React.CSSProperties {
  switch (kind) {
    case "import":
      return { stroke: "#64748b", strokeWidth: 1.5 };
    case "test":
      return { stroke: "#3b82f6", strokeWidth: 1.5, strokeDasharray: "5 3" };
    case "area":
      return { stroke: "#a78bfa", strokeWidth: 1, strokeDasharray: "2 4" };
    default:
      return { stroke: "#64748b", strokeWidth: 1 };
  }
}

function NodeDetail({
  node,
  connectedIds,
  allNodes,
}: {
  node: ImpactNode;
  connectedIds: Set<string>;
  allNodes: ImpactNode[];
}) {
  const connectedNodes = allNodes.filter((n) => connectedIds.has(n.id));
  const colors = RISK_COLORS[node.risk_color] ?? RISK_COLORS.green;

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1 flex items-center gap-2">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ background: colors.border }}
          />
          <span className="text-xs uppercase tracking-wide text-slate-500">
            {NODE_TYPE_LABELS[node.type] ?? node.type}
          </span>
          {node.changed && (
            <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
              changed
            </span>
          )}
        </div>
        <h3 className="break-all font-mono text-sm font-semibold text-slate-900">
          {node.file_path ?? node.label}
        </h3>
      </div>

      <div className="space-y-2 text-xs">
        <DetailRow label="Risk" value={node.risk_color.toUpperCase()} color={colors.text} />
        <DetailRow label="Severity" value={node.severity ?? "—"} />
        <DetailRow label="Functional area" value={node.functional_area ?? "—"} />
        <DetailRow label="Findings" value={String(node.finding_count)} />
        <DetailRow label="Priority score" value={node.priority_score != null ? String(node.priority_score) : "—"} />
        <DetailRow label="Critical area" value={node.is_critical_area ? "Yes" : "No"} />
        {node.changed && (
          <>
            <DetailRow label="Additions" value={`+${node.additions}`} />
            <DetailRow label="Deletions" value={`-${node.deletions}`} />
          </>
        )}
      </div>

      {node.finding_ids.length > 0 && (
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Finding IDs
          </h4>
          <div className="flex flex-wrap gap-1">
            {node.finding_ids.slice(0, 8).map((fid) => (
              <span
                key={fid}
                className="rounded border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[10px] text-slate-500"
              >
                {fid}
              </span>
            ))}
          </div>
        </div>
      )}

      {connectedNodes.length > 0 && (
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Connected files ({connectedNodes.length})
          </h4>
          <p className="mb-2 text-[10px] text-slate-400">
            Immediate impact / dependency connections
          </p>
          <div className="space-y-1">
            {connectedNodes.map((cn) => {
              const cnColors = RISK_COLORS[cn.risk_color] ?? RISK_COLORS.green;
              return (
                <div key={cn.id} className="flex items-center gap-2 text-xs">
                  <span
                    className="inline-block h-2 w-2 shrink-0 rounded-full"
                    style={{ background: cnColors.border }}
                  />
                  <span className="break-all font-mono text-slate-600">
                    {cn.file_path ?? cn.label}
                  </span>
                  {cn.changed && <span className="text-amber-600">*</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-700" style={color ? { color } : undefined}>
        {value}
      </span>
    </div>
  );
}
