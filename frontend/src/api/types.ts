/** Field types the backend can store today. Mirrors `SUPPORTED_FIELD_TYPES`. */
export const FIELD_TYPES = [
  "text",
  "long_text",
  "number",
  "boolean",
  "date",
  "single_select",
] as const;

export type FieldType = (typeof FIELD_TYPES)[number];

/** A stored record value. `null` is never persisted; empty values are dropped. */
export type FieldValue = string | number | boolean;

export interface SelectOption {
  value: string;
  label?: string;
}

export interface FieldConfig {
  options?: (string | SelectOption)[];
}

/** Capability names returned by the API; mirrors `services/authz.Capability`. */
export type Capability = "read" | "write_records" | "change_structure" | "manage_workspace";

export type WorkspaceRole = "OWNER" | "ADMIN" | "EDITOR" | "VIEWER";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  preferred_locale: string;
  is_active: boolean;
}

export interface Membership {
  workspace_id: string;
  workspace_name: string;
  role: WorkspaceRole;
  capabilities: Capability[];
}

/** What `/auth/me` returns: who you are and where you belong. */
export interface Identity {
  user: AuthUser;
  memberships: Membership[];
}

/** What `/auth/login` and `/auth/refresh` return: an identity plus a token. */
export interface Session extends Identity {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Workspace {
  id: string;
  name: string;
  default_locale: string;
  created_at?: string | null;
}

export interface TableSummary {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  created_at?: string | null;
}

export interface FieldDefinition {
  id: string;
  table_id: string;
  key: string;
  label: string;
  field_type: FieldType;
  position: number;
  required: boolean;
  config: FieldConfig;
}

export interface TableDetail extends TableSummary {
  fields: FieldDefinition[];
}

export interface RecordRow {
  id: string;
  table_id: string;
  data: Record<string, FieldValue>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RecordPage {
  items: RecordRow[];
  total: number;
  limit: number;
  offset: number;
}

/** One field-level problem reported by the record validator. */
export interface ApiIssue {
  field: string | null;
  code: string;
  message: string;
}

/** Normalizes the backend's `{detail: {...}}` envelope into something throwable. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly issues: ApiIssue[];

  constructor(status: number, code: string, message: string, issues: ApiIssue[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.issues = issues;
  }

  /** Field-key → message, for rendering errors next to their input. */
  issuesByField(): Record<string, string> {
    const map: Record<string, string> = {};
    for (const issue of this.issues) {
      if (issue.field) map[issue.field] = issue.message;
    }
    return map;
  }
}
