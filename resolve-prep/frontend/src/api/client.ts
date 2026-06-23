export interface TreeNode {
  name: string;
  children: TreeNode[];
}

export interface PrepTemplate {
  id: string;
  name: string;
  version: number;
  description: string;
  resolve_bins: TreeNode[];
  filesystem: TreeNode[];
  timeline: {
    frame_rate: string;
    resolution: string;
    pixel_aspect: string;
    color_timeline_space?: string | null;
    color_timeline_gamma?: string | null;
  };
  color_management: Record<string, unknown>;
  export: Record<string, unknown>;
}

export interface WorkflowRequest {
  project_name: string;
  production_root: string;
  rushes_root: string;
  template_id: string;
  card_grouping: "folder" | "flat";
  create_timelines: boolean;
  queue_exports: boolean;
  dry_run?: boolean;
}

export interface StepResult {
  step: string;
  success: boolean;
  message: string;
  details: Record<string, unknown>;
}

export interface WorkflowResult {
  project_name: string;
  template: PrepTemplate;
  scan?: {
    root: string;
    cards: Record<string, unknown[]>;
    total_files: number;
    errors: string[];
  };
  steps: StepResult[];
  dry_run: boolean;
}

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchTemplates(): Promise<PrepTemplate[]> {
  return request<PrepTemplate[]>("/templates");
}

export function runWorkflow(payload: WorkflowRequest): Promise<WorkflowResult> {
  return request<WorkflowResult>("/workflow/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchHealth(): Promise<{ status: string; dry_run_default: boolean }> {
  return request("/health");
}
