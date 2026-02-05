import type {
  Lead,
  LeadsResponse,
  Stats,
  PipelineRun,
  PipelineStatus,
  KanbanData,
  LeadFilters,
} from "./types";

const API_BASE = "/api";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Leads
export async function getLeads(filters: LeadFilters = {}): Promise<LeadsResponse> {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore) params.set("minScore", filters.minScore.toString());
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.limit) params.set("limit", filters.limit.toString());

  const query = params.toString();
  return fetchJson<LeadsResponse>(`${API_BASE}/leads${query ? `?${query}` : ""}`);
}

export async function getLead(id: number): Promise<Lead> {
  return fetchJson<Lead>(`${API_BASE}/leads/${id}`);
}

export async function updateLead(
  id: number,
  data: { stage?: string; note?: string }
): Promise<Lead> {
  const params = new URLSearchParams();
  if (data.stage) params.set("stage", data.stage);
  if (data.note) params.set("note", data.note);

  return fetchJson<Lead>(`${API_BASE}/leads/${id}?${params.toString()}`, {
    method: "PATCH",
  });
}

export async function updateLeadStage(id: number, stage: string): Promise<{ id: number; stage: string }> {
  return fetchJson(`${API_BASE}/leads/${id}/stage?stage=${encodeURIComponent(stage)}`, {
    method: "PATCH",
  });
}

export async function bulkUpdateLeads(
  ids: number[],
  stage: string
): Promise<{ updated: number[]; errors: Array<{ id: number; error: string }> }> {
  const params = new URLSearchParams();
  params.set("stage", stage);
  ids.forEach((id) => params.append("ids", id.toString()));

  return fetchJson(`${API_BASE}/leads/bulk?${params.toString()}`, {
    method: "POST",
  });
}

export function getExportUrl(filters: LeadFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore) params.set("minScore", filters.minScore.toString());

  const query = params.toString();
  return `${API_BASE}/leads/export${query ? `?${query}` : ""}`;
}

// Stats
export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${API_BASE}/stats`);
}

// Pipeline
export async function getPipelineRuns(limit = 10): Promise<{ runs: PipelineRun[] }> {
  return fetchJson(`${API_BASE}/pipeline/runs?limit=${limit}`);
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  return fetchJson<PipelineStatus>(`${API_BASE}/pipeline/status`);
}

export async function triggerPipelineRun(): Promise<{ message: string; running: boolean }> {
  return fetchJson(`${API_BASE}/pipeline/run`, { method: "POST" });
}

// Kanban
export async function getKanbanData(filters: LeadFilters = {}): Promise<KanbanData> {
  const params = new URLSearchParams();
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore) params.set("min_score", filters.minScore.toString());

  const query = params.toString();
  return fetchJson<KanbanData>(`${API_BASE}/kanban${query ? `?${query}` : ""}`);
}
