// Types mirroring the backend Phase 4 analysis schemas.

export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type Confidence = "low" | "medium" | "high";

export interface PRMeta {
  owner: string;
  repo: string;
  number: number;
  title: string;
  state: string;
  author: string | null;
  body: string | null;
  html_url: string;
  base_branch: string | null;
  head_branch: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface Finding {
  id: string;
  category: string;
  severity: Severity;
  title: string;
  file: string | null;
  line_range: [number, number] | null;
  what_changed: string;
  why_it_matters: string;
  evidence: string[];
  confidence: Confidence;
}

export interface FunctionalArea {
  name: string;
  files: string[];
  detected_by: string;
}

export interface ScopeDriftSignal {
  has_drift: boolean;
  stated_areas: string[];
  actual_areas: string[];
  unexpected_areas: string[];
  reason: string;
}

export interface ChangeSignal {
  files_changed: number;
  lines_added: number;
  lines_removed: number;
  total_changes: number;
  size_class: string;
  category_counts: Record<string, number>;
  functional_areas: FunctionalArea[];
  scope_drift: ScopeDriftSignal;
  findings: Finding[];
}

export interface CriticalArea {
  name: string;
  kind: string;
  files: string[];
  evidence: string[];
  severity: Severity;
}

export interface CriticalAreaSignal {
  areas: CriticalArea[];
  findings: Finding[];
}

export interface SecurityCheckResult {
  check_type: string;
  status: "pass" | "warn" | "fail";
  summary: string;
  findings: Finding[];
}

export interface SecuritySignal {
  findings: Finding[];
  checks: SecurityCheckResult[];
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
}

export interface QualitySignal {
  findings: Finding[];
}

export interface TestCoverageIndication {
  changed_source_files: number;
  changed_test_files: number;
  source_files_with_tests: number;
  source_files_without_tests: number;
  missing_test_files: string[];
  has_reliable_coverage_report: boolean;
  coverage_note: string;
}

export interface TestSignal {
  coverage: TestCoverageIndication;
  findings: Finding[];
}

export interface AnalysisResult {
  phase: string;
  meta: PRMeta;
  change: ChangeSignal;
  critical: CriticalAreaSignal;
  security: SecuritySignal;
  quality: QualitySignal;
  tests: TestSignal;
  all_findings: Finding[];
  stats: Record<string, number>;
  project_context?: ProjectContext;
}

export interface ProjectContext {
  name: string;
  description: string;
  language: string;
  tech_stack: string[];
  key_directories: string[];
  readme_excerpt: string;
  package_info: Record<string, string>;
}

export interface FindingExplanation {
  finding_id: string;
  explanation: string;
  is_inference: boolean;
}

export interface ScopeDriftReasoning {
  assessment: string;
  is_inference: boolean;
}

export interface AIInsights {
  pr_intent: string;
  functional_area_interpretation: string;
  scope_drift_reasoning: ScopeDriftReasoning | null;
  finding_explanations: FindingExplanation[];
  risk_reasoning: string;
  is_ai_generated: boolean;
  provider: string;
  disclaimer: string;
}

export interface RiskWeights {
  change: number;
  scope: number;
  critical: number;
  security: number;
  quality: number;
  tests: number;
}

export interface RiskDimensionScore {
  dimension: string;
  raw_score: number;
  weight: number;
  weighted_score: number;
  contributing_factors: string[];
}

export interface RiskResult {
  total_score: number;
  level: string;
  dimension_scores: RiskDimensionScore[];
  top_contributors: string[];
  weights: RiskWeights;
  disclaimer: string;
}

export interface PriorityItem {
  rank: number;
  file: string;
  score: number;
  severity: Severity;
  reason: string;
  supporting_finding_ids: string[];
}

export interface ReviewPriority {
  items: PriorityItem[];
  top_concerns: string[];
}

export interface Phase4Result {
  phase: string;
  meta: PRMeta;
  analysis: AnalysisResult;
  ai_insights: AIInsights;
  risk: RiskResult;
  priority: ReviewPriority;
  stats: Record<string, number | string>;
}

// Phase 1 types (for diff)
export interface ChangedFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch: string | null;
  previous_filename: string | null;
}

export interface DiffSummary {
  total_additions: number;
  total_deletions: number;
  total_changes: number;
  files_changed: number;
}

export interface AnalyzeResponse {
  phase: string;
  meta: PRMeta;
  diff_summary: DiffSummary;
  files: ChangedFile[];
  raw_diff: string | null;
}
