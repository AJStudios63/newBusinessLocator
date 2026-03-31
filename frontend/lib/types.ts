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
  latitude: number | null;
  longitude: number | null;
  county: string | null;
  license_date: string | null;
  pos_score: number;
  stage: Stage;
  source_url: string | null;
  source_type: string | null;
  source_batch_id: string | null;
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

export type BusinessType =
  | "restaurant"
  | "bar"
  | "retail"
  | "salon"
  | "cafe"
  | "bakery"
  | "gym"
  | "spa"
  | "other";

export const BUSINESS_TYPES: BusinessType[] = [
  "restaurant",
  "bar",
  "retail",
  "salon",
  "cafe",
  "bakery",
  "gym",
  "spa",
  "other",
];

export interface LeadsResponse {
  leads: Lead[];
  count: number;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface LeadsBatchResponse {
  leads: Lead[];
  count: number;
  batch_id: string;
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
  credits_used: number;
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
  counts?: Record<Stage, number>;
}

export interface LeadFilters {
  q?: string;
  stage?: string;
  county?: string;
  minScore?: number;
  maxScore?: number;
  sort?: string;
  limit?: number;
  page?: number;
  pageSize?: number;
}

export interface LeadFieldUpdate {
  business_name?: string;
  address?: string;
  city?: string;
  county?: string;
  zip_code?: string;
  business_type?: string;
  stage?: string;
  note?: string;
}

export interface DuplicateSuggestion {
  id: number;
  lead_a: Lead;
  lead_b: Lead;
  similarity_score: number;
  status: "pending" | "merged" | "dismissed";
  created_at: string;
}

export interface DuplicatesResponse {
  suggestions: DuplicateSuggestion[];
  count: number;
}

export interface MergeRequest {
  keep_id: number;
  merge_id: number;
  field_choices?: Record<string, string>;
  suggestion_id?: number;
}

export interface MapLead {
  id: number;
  business_name: string;
  business_type: string | null;
  city: string | null;
  county: string | null;
  pos_score: number;
  stage: Stage;
  latitude: number;
  longitude: number;
}

export interface MapLeadsResponse {
  leads: MapLead[];
  total_geocoded: number;
  total_without_coords: number;
}

export interface MapFilters {
  stage?: string;
  county?: string;
  minScore?: number;
  maxScore?: number;
  businessType?: string;
}
