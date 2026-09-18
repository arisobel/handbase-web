import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError, type FieldValue, type RecordRow, type TableDetail } from "../api/types";
import { ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";
import RecordForm from "../components/RecordForm";

export default function EditRecordPage() {
  const { t } = useTranslation();
  const { recordId = "" } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState<RecordRow | null>(null);
  const [table, setTable] = useState<TableDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [issues, setIssues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setError(null);
    // The record carries its table id; the table carries the form definition.
    api
      .getRecord(recordId)
      .then(async (loadedRecord) => {
        setRecord(loadedRecord);
        setTable(await api.getTable(loadedRecord.table_id));
      })
      .catch((err: Error) => setError(err.message));
  }, [recordId]);

  const submit = async (data: Record<string, FieldValue>) => {
    setBusy(true);
    setError(null);
    setIssues({});
    try {
      const saved = await api.replaceRecord(recordId, data);
      navigate(`/tables/${saved.table_id}`);
    } catch (err) {
      const apiError = err as ApiError;
      setIssues(apiError.issuesByField?.() ?? {});
      setError(apiError.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(t("confirmDeleteRecord"))) return;
    setError(null);
    try {
      await api.deleteRecord(recordId);
      navigate(`/tables/${record?.table_id ?? ""}`);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Layout
      title={table?.name ?? t("editRecord")}
      subtitle={t("editRecord")}
      backTo={record ? `/tables/${record.table_id}` : "/"}
      actions={
        record && (
          <button className="danger" type="button" onClick={() => void remove()}>
            {t("delete")}
          </button>
        )
      }
    >
      {error && <ErrorNote message={error} />}
      {(record === null || table === null) && !error && <Loading />}
      {record && table && (
        <RecordForm
          key={record.id}
          fields={table.fields}
          initialData={record.data}
          issues={issues}
          busy={busy}
          submitLabel={t("save")}
          onSubmit={submit}
          onCancel={() => navigate(`/tables/${record.table_id}`)}
        />
      )}
    </Layout>
  );
}
