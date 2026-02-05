import type {
  Lead,
  LeadsResponse,
  Stats,
  PipelineRun,
  PipelineStatus,
  KanbanData,
  LeadFilters,
  LeadFieldUpdate,
  DuplicatesResponse,
  MergeRequest,
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
  if (filters.q) params.set("q", filters.q);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore !== undefined) params.set("minScore", filters.minScore.toString());
  if (filters.maxScore !== undefined) params.set("maxScore", filters.maxScore.toString());
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.limit) params.set("limit", filters.limit.toString());
  if (filters.page !== undefined) params.set("page", filters.page.toString());
  if (filters.pageSize !== undefined) params.set("pageSize", filters.pageSize.toString());

  const query = params.toString();
  return fetchJson<LeadsResponse>(`${API_BASE}/leads${query ? `?${query}` : ""}`);
}

export async function getLeadsByBatch(batchId: string): Promise<LeadsResponse & { batch_id: string }> {
  return fetchJson(`${API_BASE}/leads/batch/${encodeURIComponent(batchId)}`);
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

export async function updateLeadFields(
  id: number,
  fields: LeadFieldUpdate
): Promise<Lead> {
  return fetchJson<Lead>(`${API_BASE}/leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export async function updateLeadStage(id: number, stage: string): Promise<{ id: number; stage: string }> {
  return fetchJson(`${API_BASE}/leads/${id}/stage?stage=${encodeURIComponent(stage)}`, {
    method: "PATCH",
  });
}

export async function bulkUpdateLeads(
  ids: number[],
  options: { stage?: string; county?: string }
): Promise<{ updated: number[]; errors: Array<{ id?: number; error: string }> }> {
  const params = new URLSearchParams();
  if (options.stage) params.set("stage", options.stage);
  if (options.county) params.set("county", options.county);
  ids.forEach((id) => params.append("ids", id.toString()));

  return fetchJson(`${API_BASE}/leads/bulk?${params.toString()}`, {
    method: "POST",
  });
}

export async function bulkDeleteLeads(
  ids: number[]
): Promise<{ deleted: number[]; errors: Array<{ id: number; error: string }> }> {
  const params = new URLSearchParams();
  ids.forEach((id) => params.append("ids", id.toString()));

  return fetchJson(`${API_BASE}/leads/bulk?${params.toString()}`, {
    method: "DELETE",
  });
}

export function getExportUrl(filters: LeadFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore !== undefined) params.set("minScore", filters.minScore.toString());
  if (filters.maxScore !== undefined) params.set("maxScore", filters.maxScore.toString());

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

// Duplicates
export async function getDuplicatesCount(): Promise<{ count: number; status: string }> {
  return fetchJson(`${API_BASE}/leads/duplicates/count`);
}

export async function getDuplicates(limit = 20): Promise<DuplicatesResponse> {
  return fetchJson(`${API_BASE}/leads/duplicates?limit=${limit}`);
}

export async function scanForDuplicates(threshold = 0.7): Promise<{ new_suggestions: number }> {
  return fetchJson(`${API_BASE}/leads/duplicates/scan?threshold=${threshold}`, { method: "POST" });
}

export async function updateDuplicateSuggestion(
  suggestionId: number,
  status: "merged" | "dismissed"
): Promise<{ id: number; status: string }> {
  return fetchJson(`${API_BASE}/leads/duplicates/${suggestionId}?status=${status}`, {
    method: "PATCH",
  });
}

export async function mergeLeads(request: MergeRequest): Promise<Lead> {
  return fetchJson(`${API_BASE}/leads/merge`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}
