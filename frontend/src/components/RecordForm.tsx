import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { FieldDefinition, FieldValue, SelectOption } from "../api/types";

/** Form state keeps everything as strings/booleans; conversion happens on submit. */
type FormState = Record<string, string | boolean>;

interface RecordFormProps {
  fields: FieldDefinition[];
  initialData?: Record<string, FieldValue>;
  /** Field key → message, as returned by the backend validator. */
  issues?: Record<string, string>;
  submitLabel: string;
  busy?: boolean;
  onSubmit: (data: Record<string, FieldValue>) => void;
  onCancel?: () => void;
}

function normalizeOptions(field: FieldDefinition): SelectOption[] {
  return (field.config.options ?? []).map((option) =>
    typeof option === "string" ? { value: option } : option,
  );
}

export function buildInitialState(
  fields: FieldDefinition[],
  data: Record<string, FieldValue> = {},
): FormState {
  const state: FormState = {};
  for (const field of fields) {
    const value = data[field.key];
    if (field.field_type === "boolean") {
      state[field.key] = value === true;
    } else {
      state[field.key] = value === undefined || value === null ? "" : String(value);
    }
  }
  return state;
}

/**
 * Converts form state into an API payload.
 *
 * Empty optional values are omitted rather than sent as empty strings, and a
 * malformed number is passed through untouched so the server — the single
 * source of validation truth — reports it.
 */
function toPayload(fields: FieldDefinition[], state: FormState): Record<string, FieldValue> {
  const payload: Record<string, FieldValue> = {};
  for (const field of fields) {
    const raw = state[field.key];
    if (field.field_type === "boolean") {
      payload[field.key] = raw === true;
      continue;
    }
    const text = typeof raw === "string" ? raw : "";
    if (text.trim() === "") continue;

    if (field.field_type === "number") {
      const parsed = Number(text);
      payload[field.key] = Number.isNaN(parsed) ? text : parsed;
    } else {
      payload[field.key] = text;
    }
  }
  return payload;
}

/**
 * Renders a form entirely from field definitions. Nothing here knows about
 * students, families or any other domain concept.
 */
export default function RecordForm({
  fields,
  initialData,
  issues = {},
  submitLabel,
  busy = false,
  onSubmit,
  onCancel,
}: RecordFormProps) {
  const { t } = useTranslation();
  const [state, setState] = useState<FormState>(() => buildInitialState(fields, initialData));

  const setValue = (key: string, value: string | boolean) =>
    setState((current) => ({ ...current, [key]: value }));

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(toPayload(fields, state));
  };

  if (fields.length === 0) {
    return <p className="empty">{t("noFieldsYet")}</p>;
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      {fields.map((field) => {
        const issue = issues[field.key];
        const inputId = `field-${field.id}`;
        const describedBy = issue ? `${inputId}-error` : undefined;

        return (
          <div className="formRow" key={field.id}>
            <label htmlFor={inputId}>
              {field.label}
              {field.required && (
                <span className="required" aria-hidden="true">
                  *
                </span>
              )}
            </label>

            {field.field_type === "long_text" && (
              <textarea
                id={inputId}
                rows={4}
                aria-describedby={describedBy}
                value={String(state[field.key] ?? "")}
                onChange={(event) => setValue(field.key, event.target.value)}
              />
            )}

            {field.field_type === "boolean" && (
              <input
                id={inputId}
                type="checkbox"
                className="checkbox"
                aria-describedby={describedBy}
                checked={state[field.key] === true}
                onChange={(event) => setValue(field.key, event.target.checked)}
              />
            )}

            {field.field_type === "single_select" && (
              <select
                id={inputId}
                aria-describedby={describedBy}
                value={String(state[field.key] ?? "")}
                onChange={(event) => setValue(field.key, event.target.value)}
              >
                <option value="">{t("selectPlaceholder")}</option>
                {normalizeOptions(field).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label ?? option.value}
                  </option>
                ))}
              </select>
            )}

            {(field.field_type === "text" ||
              field.field_type === "number" ||
              field.field_type === "date") && (
              <input
                id={inputId}
                type={field.field_type === "date" ? "date" : "text"}
                inputMode={field.field_type === "number" ? "decimal" : undefined}
                aria-describedby={describedBy}
                value={String(state[field.key] ?? "")}
                onChange={(event) => setValue(field.key, event.target.value)}
              />
            )}

            {issue && (
              <p className="fieldError" id={`${inputId}-error`}>
                {issue}
              </p>
            )}
          </div>
        );
      })}

      <div className="formActions">
        <button className="primary" type="submit" disabled={busy}>
          {busy ? t("saving") : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            {t("cancel")}
          </button>
        )}
      </div>
    </form>
  );
}
