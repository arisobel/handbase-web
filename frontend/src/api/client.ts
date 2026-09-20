import {
  ApiError,
  type ApiIssue,
  type FieldDefinition,
  type FieldType,
  type FieldValue,
  type RecordPage,
  type Identity,
  type RecordRow,
  type Session,
  type TableDetail,
  type TableSummary,
  type Workspace,
  type WorkspaceMember,
  type WorkspaceRole,
  type SupportedLocale,
} from "./types";

const BASE = "/api/v1";

/**
 * The access token lives in a module variable, never in localStorage or a
 * readable cookie: a script injected into the page cannot exfiltrate it, and it
 * disappears when the tab closes. The refresh token is an HttpOnly cookie the
 * page can never read, so a reload restores the session through `/auth/refresh`
 * rather than by persisting anything here.
 */
let accessToken: string | null = null;
let sessionListener: ((session: Session | null) => void) | null = null;

/** Registered by the auth provider so a silent refresh updates React state. */
export function setSessionListener(listener: ((session: Session | null) => void) | null): void {
  sessionListener = listener;
}

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

async function send(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${BASE}${path}`, {
    ...init,
    headers,
    // Required for the refresh cookie on /auth/* calls.
    credentials: "include",
  });
}

/** Ask for a new access token using the refresh cookie. Returns false if there is no session. */
async function tryRefresh(): Promise<boolean> {
  const response = await send("/auth/refresh", { method: "POST" });
  if (!response.ok) return false;
  const session = (await response.json()) as Session;
  accessToken = session.access_token;
  sessionListener?.(session);
  return true;
}

async function request<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  let response = await send(path, init);

  // An expired access token is the normal case, not an error: refresh once and
  // replay. `/auth/*` is excluded so a failed login cannot trigger a refresh loop.
  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await tryRefresh()) {
      response = await send(path, init);
    } else {
      accessToken = null;
      sessionListener?.(null);
    }
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (method: string, payload: unknown): RequestInit => ({
  method,
  body: JSON.stringify(payload),
});

export const api = {
  login: async (email: string, password: string) => {
    const session = await request<Session>("/auth/login", json("POST", { email, password }));
    accessToken = session.access_token;
    return session;
  },
  /** Restore a session on page load. Resolves to null when there is none. */
  restoreSession: async (): Promise<Session | null> => {
    try {
      const session = await request<Session>("/auth/refresh", { method: "POST" }, false);
      accessToken = session.access_token;
      return session;
    } catch {
      accessToken = null;
      return null;
    }
  },
  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" }, false);
    } finally {
      accessToken = null;
    }
  },
  me: () => request<Identity>("/auth/me"),
  updateProfile: (payload: { display_name?: string; preferred_locale?: SupportedLocale }) =>
    request<Identity>("/auth/me", json("PATCH", payload)),

  listWorkspaces: () => request<Workspace[]>("/workspaces"),
  getWorkspace: (id: string) => request<Workspace>(`/workspaces/${id}`),
  createWorkspace: (payload: { name: string; default_locale?: SupportedLocale }) =>
    request<Workspace>("/workspaces", json("POST", payload)),
  updateWorkspace: (
    id: string,
    payload: { name?: string; default_locale?: SupportedLocale },
  ) => request<Workspace>(`/workspaces/${id}`, json("PATCH", payload)),
  deleteWorkspace: (id: string) => request<void>(`/workspaces/${id}`, { method: "DELETE" }),
  listMembers: (workspaceId: string) =>
    request<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`),
  addMember: (workspaceId: string, payload: { email: string; role: WorkspaceRole }) =>
    request<WorkspaceMember>(`/workspaces/${workspaceId}/members`, json("POST", payload)),
  updateMember: (workspaceId: string, membershipId: string, role: WorkspaceRole) =>
    request<WorkspaceMember>(
      `/workspaces/${workspaceId}/members/${membershipId}`,
      json("PATCH", { role }),
    ),
  removeMember: (workspaceId: string, membershipId: string) =>
    request<void>(`/workspaces/${workspaceId}/members/${membershipId}`, {
      method: "DELETE",
    }),

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
