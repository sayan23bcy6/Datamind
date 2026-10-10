export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  postgres: string;
  redis: string;
}

export interface DatasetItem {
  id: string;
  name: string;
  created_at: string;
}

export interface DatasetVersionItem {
  id: string;
  version_number: number;
  parent_version_id: string | null;
  source_name: string;
  row_count: number;
  column_count: number;
  file_size_bytes: number | null;
  sha256: string;
  is_original: boolean;
  created_at: string;
}

export interface UploadResponse {
  dataset_id: string;
  version_id: string;
  dataset_name: string;
  file_name: string;
  row_count: number;
  column_count: number;
  sha256: string;
}

export interface DemoDatasetResponse {
  dataset_id: string;
  version_id: string;
  message: string;
  created: boolean;
}

export interface ColumnProfileItem {
  name: string;
  dtype: string;
  missing_count: number;
  missing_rate: number;
  unique_count: number;
  sample_values: Array<string | number | null>;
}

export interface DimensionScores {
  completeness: number;
  uniqueness: number;
  consistency: number;
  validity: number;
  accuracy: number;
  overall: number;
}

export interface ProfileResponse {
  row_count: number;
  column_count: number;
  columns: ColumnProfileItem[];
  dimensions: DimensionScores;
}

export interface InvestigationSummary {
  investigation_id: string;
  status: "pending" | "running" | "awaiting_human" | "completed" | "partial" | "failed";
  state: string;
  iteration: number;
  max_iterations: number;
  cost_used: number;
  cost_budget: number;
  dataset_version_id: string;
  output_version_id: string | null;
  error: string | null;
}

export interface ProposalItem {
  type: "proposal";
  iteration: number;
  proposal_id: string;
  operation: string;
  target_columns: string[];
  parameters: Record<string, unknown>;
  rationale: string;
  confidence: number;
  confidence_basis: string;
}

export interface VerdictItem {
  type: "verdict";
  proposal_id: string;
  verdict: "APPROVE" | "REJECT" | "ESCALATE_TO_HUMAN";
  reasons: string[];
  unsupported_assumptions: string[];
  created_at: string;
}

export type ProposalOrVerdict = ProposalItem | VerdictItem;

export interface DiffItem {
  column: string;
  row_index: number | null;
  original_row_index: number | null;
  change_type: "modified" | "removed" | "added";
  original_value: string | null;
  new_value: string | null;
  rule: string;
  confidence: number;
  confidence_basis: string;
}

export interface DistributionItem {
  column: string;
  before_bins: number[];
  after_bins: number[];
  ks_statistic: number | null;
  p_value: number | null;
  passed: boolean;
}

export interface EvidenceItem {
  evidence_id: string;
  claim: string;
  test_name: string;
  statistic: string | null;
  p_value: string | null;
  details: Record<string, unknown> | null;
}

export interface AuditLog {
  investigation_id: string;
  audit_trail: Array<{
    type: string;
    state?: string;
    role?: string;
    tool?: string;
    operation?: string;
    delta?: number;
    reason?: string;
    timestamp?: string;
    [key: string]: unknown;
  }>;
}

export interface ReviewItem {
  review_id: string;
  investigation_id: string;
  proposal_id: string;
  status: "pending" | "approved" | "edited" | "rejected";
  proposal_summary: string | null;
  parameters: Record<string, unknown> | null;
}

export interface WatchItem {
  id: string;
  dataset_id: string;
  schedule: string;
  drift_threshold: string;
  enabled: boolean;
  last_checked_at: string | null;
  created_at: string;
}

const API_BASE = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP error ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {
      // fallback
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    return handleResponse<HealthResponse>(res);
  },

  async getDatasets(): Promise<DatasetItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/datasets`);
    return handleResponse<DatasetItem[]>(res);
  },

  async uploadDataset(file: File, datasetName?: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (datasetName) formData.append("dataset_name", datasetName);
    const res = await fetch(`${API_BASE}/api/v1/datasets/upload`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<UploadResponse>(res);
  },

  async createDemoDataset(): Promise<DemoDatasetResponse> {
    const res = await fetch(`${API_BASE}/api/v1/datasets/demo`, {
      method: "POST",
    });
    return handleResponse<DemoDatasetResponse>(res);
  },

  async getDatasetVersions(datasetId: string): Promise<DatasetVersionItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/versions`);
    return handleResponse<DatasetVersionItem[]>(res);
  },

  async getVersionProfile(versionId: string): Promise<ProfileResponse> {
    const res = await fetch(`${API_BASE}/api/v1/versions/${versionId}/profile`);
    return handleResponse<ProfileResponse>(res);
  },

  getDownloadUrl(versionId: string): string {
    return `${API_BASE}/api/v1/versions/${versionId}/download`;
  },

  async createInvestigation(datasetId: string): Promise<{ investigation_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/investigations`, {
      method: "POST",
    });
    return handleResponse<{ investigation_id: string; status: string }>(res);
  },

  async getInvestigation(id: string): Promise<InvestigationSummary> {
    const res = await fetch(`${API_BASE}/api/v1/investigations/${id}`);
    return handleResponse<InvestigationSummary>(res);
  },

  async getInvestigationProposals(id: string): Promise<ProposalOrVerdict[]> {
    const res = await fetch(`${API_BASE}/api/v1/investigations/${id}/proposals`);
    return handleResponse<ProposalOrVerdict[]>(res);
  },

  async getInvestigationDiff(id: string): Promise<DiffItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/investigations/${id}/diff`);
    return handleResponse<DiffItem[]>(res);
  },

  async getInvestigationDistributions(id: string): Promise<DistributionItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/investigations/${id}/distributions`);
    return handleResponse<DistributionItem[]>(res);
  },

  async getInvestigationEvidence(id: string): Promise<EvidenceItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/investigations/${id}/evidence`);
    return handleResponse<EvidenceItem[]>(res);
  },

  async getInvestigationAudit(id: string): Promise<AuditLog> {
    const res = await fetch(`${API_BASE}/api/v1/investigations/${id}/audit`);
    return handleResponse<AuditLog>(res);
  },

  getReportDownloadUrl(id: string, format: "json" | "markdown" | "html" | "pdf"): string {
    return `${API_BASE}/api/v1/investigations/${id}/report?format=${format}`;
  },

  async getReviews(status = "pending"): Promise<ReviewItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/reviews?status=${status}`);
    return handleResponse<ReviewItem[]>(res);
  },

  async submitReviewDecision(
    reviewId: string,
    decision: "approve" | "edit" | "reject",
    parameters?: Record<string, unknown>
  ): Promise<{ status: string; review_id: string; decision: string }> {
    const body: Record<string, unknown> = { decision };
    if (decision === "edit") {
      body.parameters = parameters || {};
    } else if (parameters) {
      body.parameters = parameters;
    }
    const res = await fetch(`${API_BASE}/api/v1/reviews/${reviewId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return handleResponse<{ status: string; review_id: string; decision: string }>(res);
  },

  async getWatches(): Promise<WatchItem[]> {
    const res = await fetch(`${API_BASE}/api/v1/watches`);
    return handleResponse<WatchItem[]>(res);
  },

  async createWatch(data: { dataset_id: string; schedule: string; drift_threshold: string; enabled: boolean }): Promise<WatchItem> {
    const res = await fetch(`${API_BASE}/api/v1/watches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return handleResponse<WatchItem>(res);
  },

  async deleteWatch(id: string): Promise<{ status: string; id: string }> {
    const res = await fetch(`${API_BASE}/api/v1/watches/${id}`, {
      method: "DELETE",
    });
    return handleResponse<{ status: string; id: string }>(res);
  },

  getEventsUrl(id: string): string {
    return `${API_BASE}/api/v1/investigations/${id}/events`;
  },
};
