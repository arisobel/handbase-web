import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { TableSummary, Workspace } from "../api/types";
import { Empty, ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";

export default function WorkspacePage() {
  const { t } = useTranslation();
  const { workspaceId = "" } = useParams();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [tables, setTables] = useState<TableSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setError(null);
    Promise.all([api.getWorkspace(workspaceId), api.listTables(workspaceId)])
      .then(([loadedWorkspace, loadedTables]) => {
        setWorkspace(loadedWorkspace);
        setTables(loadedTables);
      })
      .catch((err: Error) => setError(err.message));
  }, [workspaceId]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() === "") return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createTable({
        workspace_id: workspaceId,
        name: name.trim(),
        description: description.trim() || null,
      });
      setTables((current) => [...(current ?? []), created]);
      setName("");
      setDescription("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title={workspace?.name ?? t("workspace")} subtitle={t("tables")} backTo="/">
      <section>
        <div className="sectionTitle">
          <h2>{t("newTable")}</h2>
        </div>

        <form className="form" onSubmit={submit}>
          <div className="formRow">
            <label htmlFor="table-name">{t("tableName")}</label>
            <input
              id="table-name"
              placeholder={t("tableNamePlaceholder")}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="formRow">
            <label htmlFor="table-description">{t("tableDescription")}</label>
            <input
              id="table-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <div className="formActions">
            <button className="primary" type="submit" disabled={busy}>
              {t("createTable")}
            </button>
          </div>
        </form>

        {error && <ErrorNote message={error} />}
        {tables === null && !error && <Loading />}
        {tables?.length === 0 && <Empty message={t("noTablesYet")} />}

        <div className="cardList">
          {tables?.map((table) => (
            <Link className="card" key={table.id} to={`/tables/${table.id}`}>
              <span className="cardIcon" aria-hidden="true">
                {table.name.slice(0, 1)}
              </span>
              <div>
                <strong>{table.name}</strong>
                <small>{table.description || table.slug}</small>
              </div>
              <span className="chevron" aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>
    </Layout>
  );
}
