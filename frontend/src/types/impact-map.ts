// Types mirroring the backend Impact Map schemas (Phase 5).

export type NodeType = "source" | "test" | "config" | "area";

export type RiskColor = "red" | "orange" | "yellow" | "green";

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export interface ImpactNode {
  id: string;
  type: NodeType;
  label: string;
  file_path: string | null;
  functional_area: string | null;
  changed: boolean;
  risk_color: RiskColor;
  severity: Severity | null;
  finding_count: number;
  finding_ids: string[];
  priority_score: number | null;
  is_critical_area: boolean;
  additions: number;
  deletions: number;
}

export interface ImpactEdge {
  id: string;
  source: string;
  target: string;
  kind: "import" | "test" | "area";
}

export interface ImpactMap {
  phase: string;
  nodes: ImpactNode[];
  edges: ImpactEdge[];
  stats: Record<string, number>;
  legend: Record<string, string>;
}
