export interface Lead {
  id: number;
  fingerprint: string;
  business_name: string;
  business_type: string | null;
  raw_type: string | null;
  address: string | null;
  city: string | null;
  state: string;
  zip_code: string | null;
  county: string | null;
  license_date: string | null;
  pos_score: number;
  stage: Stage;
  source_url: string | null;
  source_type: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  contacted_at: string | null;
  closed_at: string | null;
}

export type Stage =
  | "New"
  | "Qualified"
  | "Contacted"
  | "Follow-up"
  | "Closed-Won"
  | "Closed-Lost";

export const STAGES: Stage[] = [
  "New",
  "Qualified",
  "Contacted",
  "Follow-up",
  "Closed-Won",
  "Closed-Lost",
];

export interface LeadsResponse {
  leads: Lead[];
  count: number;
}

export interface Stats {
  by_stage: Record<string, number>;
  by_county: Record<string, number>;
  by_type: Record<string, number>;
  avg_score: number;
  total_leads: number;
  last_run: PipelineRun | null;
}

export interface PipelineRun {
  id: number;
  run_started_at: string;
  run_finished_at: string | null;
  status: string;
  leads_found: number;
  leads_new: number;
  leads_dupes: number;
  error_message: string | null;
  sources_queried: string | null;
}

export interface PipelineStatus {
  running: boolean;
  last_result: {
    run_id?: number;
    status: string;
    leads_found?: number;
    leads_new?: number;
    leads_dupes?: number;
    error?: string | null;
  } | null;
}

export interface KanbanData {
  stages: Stage[];
  columns: Record<Stage, Lead[]>;
}

export interface LeadFilters {
  stage?: string;
  county?: string;
  minScore?: number;
  sort?: string;
  limit?: number;
}
