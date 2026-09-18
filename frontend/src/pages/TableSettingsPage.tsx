import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError, FIELD_TYPES, type FieldType, type TableDetail } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";

/** The table builder: define the structure that every form and list derives from. */
export default function TableSettingsPage() {
  const { t } = useTranslation();
  const { tableId = "" } = useParams();
  const { can } = useAuth();
  const [table, setTable] = useState<TableDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [fieldType, setFieldType] = useState<FieldType>("text");
  const [required, setRequired] = useState(false);
  const [options, setOptions] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setError(null);
    api
      .getTable(tableId)
      .then(setTable)
      .catch((err: Error) => setError(err.message));
  }, [tableId]);

  const addField = async (event: FormEvent) => {
    event.preventDefault();
    if (label.trim() === "") return;
    setBusy(true);
    setError(null);
    try {
      const config =
        fieldType === "single_select"
          ? {
              options: options
                .split(",")
                .map((option) => option.trim())
                .filter(Boolean),
            }
          : {};
      const created = await api.createField({
        table_id: tableId,
        label: label.trim(),
        field_type: fieldType,
        required,
        config,
      });
      setTable((current) =>
        current ? { ...current, fields: [...current.fields, created] } : current,
      );
      setLabel("");
      setRequired(false);
      setOptions("");
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.issues?.[0]?.message ?? apiError.message);
    } finally {
      setBusy(false);
    }
  };

  const removeField = async (fieldId: string) => {
    setError(null);
    try {
      await api.deleteField(fieldId);
      setTable((current) =>
        current ? { ...current, fields: current.fields.filter((f) => f.id !== fieldId) } : current,
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (error && table === null) {
    return (
      <Layout title={t("tableStructure")} backTo="/">
        <ErrorNote message={error} />
      </Layout>
    );
  }

  if (table === null) {
    return (
      <Layout title={t("tableStructure")} backTo="/">
        <Loading />
      </Layout>
    );
  }

  // Reaching this route directly without the capability shows the structure
  // read-only; the API would reject every write anyway.
  const canBuild = can(table.workspace_id, "change_structure");

  return (
    <Layout title={table.name} subtitle={t("tableStructure")} backTo={`/tables/${table.id}`}>
      {canBuild && (
      <section>
        <div className="sectionTitle">
          <h2>{t("addField")}</h2>
        </div>

        <form className="form" onSubmit={addField}>
          <div className="formRow">
            <label htmlFor="field-label">{t("fieldLabel")}</label>
            <input
              id="field-label"
              placeholder={t("fieldLabelPlaceholder")}
              value={label}
              onChange={(event) => setLabel(event.target.value)}
            />
          </div>

          <div className="formRow">
            <label htmlFor="field-type">{t("fieldType")}</label>
            <select
              id="field-type"
              value={fieldType}
              onChange={(event) => setFieldType(event.target.value as FieldType)}
            >
              {FIELD_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`fieldTypes.${type}`)}
                </option>
              ))}
            </select>
          </div>

          {fieldType === "single_select" && (
            <div className="formRow">
              <label htmlFor="field-options">{t("fieldOptions")}</label>
              <input
                id="field-options"
                placeholder={t("fieldOptionsPlaceholder")}
                value={options}
                onChange={(event) => setOptions(event.target.value)}
              />
            </div>
          )}

          <div className="formRow inlineCheck">
            <label htmlFor="field-required">{t("required")}</label>
            <input
              id="field-required"
              type="checkbox"
              className="checkbox"
              checked={required}
              onChange={(event) => setRequired(event.target.checked)}
            />
          </div>

          <div className="formActions">
            <button className="primary" type="submit" disabled={busy}>
              {t("addField")}
            </button>
          </div>
        </form>

        {error && <ErrorNote message={error} />}
      </section>
      )}

      <section className="listPanel">
        <h2>{t("fields")}</h2>
        {table.fields.length === 0 && <Empty message={t("noFieldsYet")} />}
        {table.fields.map((field) => (
          <div className="listItem" key={field.id}>
            <div>
              <strong>{field.label}</strong>
              <small>
                {t(`fieldTypes.${field.field_type}`)}
                {field.required ? ` · ${t("required")}` : ""} · <code>{field.key}</code>
              </small>
            </div>
            {canBuild && (
              <button className="danger" type="button" onClick={() => void removeField(field.id)}>
                {t("delete")}
              </button>
            )}
          </div>
        ))}
      </section>
    </Layout>
  );
}
