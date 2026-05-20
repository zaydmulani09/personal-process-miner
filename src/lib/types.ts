export interface Workflow {
  id: number;
  name: string;
  fingerprint: string;
  steps: string; // JSON-encoded array (strings or step objects)
  frequency: number;
  avg_duration_seconds: number | null;
  first_seen: string | null;
  last_seen: string | null;
  is_labeled: number; // 0 or 1
  created_at: string;
  // added by ranker
  score?: number;
  time_wasted_seconds?: number;
  time_wasted_human?: string;
}

export interface Session {
  id: number;
  started_at: string;
  ended_at: string | null;
  event_count: number;
  dominant_app: string | null;
}

export interface SummaryStats {
  total_workflows: number;
  total_time_wasted_seconds: number;
  total_time_wasted_human: string;
  top_workflow: Workflow | null;
  weekly_wasted_seconds: number;
  weekly_wasted_human: string;
}

export interface Automation {
  id: number;
  workflow_id: number | null;
  name: string;
  script_type: string;
  script_body: string;
  last_run_at: string | null;
  run_count: number;
  last_run_status: string | null;
  created_at: string;
  scheduled?: boolean;
  schedule_info?: string; // human-readable, e.g. "Daily at 09:00"
}
