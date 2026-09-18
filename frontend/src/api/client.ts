import {
  ApiError,
  type ApiIssue,
  type FieldDefinition,
  type FieldType,
  type FieldValue,
  type RecordPage,
  type RecordRow,
  type TableDetail,
  type TableSummary,
  type Workspace,
} from "./types";

const BASE = "/api/v1";

interface DetailEnvelope {
  detail?: string | { code?: string; message?: string; errors?: ApiIssue[] };
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: DetailEnvelope = {};
  try {
    body = (await response.json()) as DetailEnvelope;
  } catch {
    // Non-JSON error body (proxy, gateway). Fall through to the status text.
  }
  const detail = body.detail;
  if (detail && typeof detail === "object") {
    return new ApiError(
      response.status,
      detail.code ?? "error",
      detail.message ?? response.statusText,
      detail.errors ?? [],
    );
  }
  return new ApiError(response.status, "error", detail ?? response.statusText);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (method: string, payload: unknown): RequestInit => ({
  method,
  body: JSON.stringify(payload),
});

export const api = {
  listWorkspaces: () => request<Workspace[]>("/workspaces"),
  getWorkspace: (id: string) => request<Workspace>(`/workspaces/${id}`),
  createWorkspace: (payload: { name: string; default_locale?: string }) =>
    request<Workspace>("/workspaces", json("POST", payload)),
  deleteWorkspace: (id: string) => request<void>(`/workspaces/${id}`, { method: "DELETE" }),

  listTables: (workspaceId: string) =>
    request<TableSummary[]>(`/tables?workspace_id=${encodeURIComponent(workspaceId)}`),
  getTable: (id: string) => request<TableDetail>(`/tables/${id}`),
  createTable: (payload: { workspace_id: string; name: string; description?: string | null }) =>
    request<TableSummary>("/tables", json("POST", payload)),
  deleteTable: (id: string) => request<void>(`/tables/${id}`, { method: "DELETE" }),

  createField: (payload: {
    table_id: string;
    label: string;
    field_type: FieldType;
    required: boolean;
    config?: Record<string, unknown>;
  }) => request<FieldDefinition>("/fields", json("POST", payload)),
  deleteField: (id: string) => request<void>(`/fields/${id}`, { method: "DELETE" }),

  listRecords: (tableId: string, limit = 50, offset = 0) =>
    request<RecordPage>(
      `/records?table_id=${encodeURIComponent(tableId)}&limit=${limit}&offset=${offset}`,
    ),
  getRecord: (id: string) => request<RecordRow>(`/records/${id}`),
  createRecord: (payload: { table_id: string; data: Record<string, FieldValue> }) =>
    request<RecordRow>("/records", json("POST", payload)),
  replaceRecord: (id: string, data: Record<string, FieldValue>) =>
    request<RecordRow>(`/records/${id}`, json("PUT", { data })),
  deleteRecord: (id: string) => request<void>(`/records/${id}`, { method: "DELETE" }),
};
