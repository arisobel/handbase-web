import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { RecordRow, TableDetail } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";
import RecordList from "../components/RecordList";

export default function TableRecordsPage() {
  const { t } = useTranslation();
  const { tableId = "" } = useParams();
  const { can } = useAuth();
  const [table, setTable] = useState<TableDetail | null>(null);
  const [records, setRecords] = useState<RecordRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([api.getTable(tableId), api.listRecords(tableId)])
      .then(([loadedTable, page]) => {
        setTable(loadedTable);
        setRecords(page.items);
        setTotal(page.total);
      })
      .catch((err: Error) => setError(err.message));
  }, [tableId]);

  // The API rejects these anyway; hiding them keeps the UI honest about the role.
  const actions = table && (
    <>
      {can(table.workspace_id, "write_records") && (
        <Link className="primary buttonLink" to={`/tables/${table.id}/new`}>
          {t("newRecord")}
        </Link>
      )}
      {can(table.workspace_id, "change_structure") && (
        <Link className="secondary buttonLink" to={`/tables/${table.id}/settings`}>
          {t("tableStructure")}
        </Link>
      )}
    </>
  );

  return (
    <Layout
      title={table?.name ?? t("records")}
      subtitle={table ? t("recordCount", { count: total }) : undefined}
      backTo={table ? `/workspaces/${table.workspace_id}` : "/"}
      actions={actions}
    >
      {error && <ErrorNote message={error} />}
      {(table === null || records === null) && !error && <Loading />}

      {table && table.fields.length === 0 && <Empty message={t("noFieldsYetHint")} />}
      {table && table.fields.length > 0 && records?.length === 0 && (
        <Empty message={t("noRecordsYet")} />
      )}
      {table && records && records.length > 0 && (
        <RecordList
          fields={table.fields}
          records={records}
          canEdit={can(table.workspace_id, "write_records")}
        />
      )}
    </Layout>
  );
}
