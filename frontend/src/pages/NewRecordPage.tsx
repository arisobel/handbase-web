import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError, type FieldValue, type TableDetail } from "../api/types";
import { ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";
import RecordForm from "../components/RecordForm";

export default function NewRecordPage() {
  const { t } = useTranslation();
  const { tableId = "" } = useParams();
  const navigate = useNavigate();
  const [table, setTable] = useState<TableDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [issues, setIssues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .getTable(tableId)
      .then(setTable)
      .catch((err: Error) => setError(err.message));
  }, [tableId]);

  const submit = async (data: Record<string, FieldValue>) => {
    setBusy(true);
    setError(null);
    setIssues({});
    try {
      await api.createRecord({ table_id: tableId, data });
      navigate(`/tables/${tableId}`);
    } catch (err) {
      const apiError = err as ApiError;
      setIssues(apiError.issuesByField?.() ?? {});
      setError(apiError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title={table?.name ?? t("newRecord")} subtitle={t("newRecord")} backTo={`/tables/${tableId}`}>
      {error && <ErrorNote message={error} />}
      {table === null && !error && <Loading />}
      {table && (
        <RecordForm
          fields={table.fields}
          issues={issues}
          busy={busy}
          submitLabel={t("save")}
          onSubmit={submit}
          onCancel={() => navigate(`/tables/${tableId}`)}
        />
      )}
    </Layout>
  );
}
