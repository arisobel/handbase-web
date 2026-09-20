import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError, type FieldValue, type RecordRow, type TableDetail } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorNote, Loading } from "../components/Feedback";
import RecordView from "../components/RecordView";
import Layout from "../components/Layout";
import RecordForm from "../components/RecordForm";

export default function EditRecordPage() {
  const { t } = useTranslation();
  const { recordId = "" } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
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

  const canWrite = table ? can(table.workspace_id, "write_records") : false;

  return (
    <Layout
      title={table?.name ?? t("editRecord")}
      subtitle={canWrite ? t("editRecord") : t("viewRecord")}
      workspaceId={table?.workspace_id}
      backTo={record ? `/tables/${record.table_id}` : "/"}
      actions={
        record &&
        canWrite && (
          <button className="danger" type="button" onClick={() => void remove()}>
            {t("delete")}
          </button>
        )
      }
    >
      {error && <ErrorNote message={error} />}
      {(record === null || table === null) && !error && <Loading />}
      {record && table && canWrite && (
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
      {record && table && !canWrite && (
        <RecordView fields={table.fields} data={record.data} />
      )}
    </Layout>
  );
}
