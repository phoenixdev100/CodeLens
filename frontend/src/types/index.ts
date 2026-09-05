// Types mirroring the backend Pydantic schemas (Phase 1).

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

export interface ErrorResponse {
  error: string;
  detail?: string;
}

export interface HealthResponse {
  status: string;
  auth_mode: "github-app" | "pat" | "none";
}
