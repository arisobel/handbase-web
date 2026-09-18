import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Workspace } from "../api/types";
import { Empty, ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";

export default function DashboardPage() {
  const { t } = useTranslation();
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    api
      .listWorkspaces()
      .then(setWorkspaces)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(load, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() === "") return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createWorkspace({ name: name.trim() });
      setWorkspaces((current) => [...(current ?? []), created]);
      setName("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title={t("appName")} subtitle={t("subtitle")}>
      <section>
        <div className="sectionTitle">
          <h2>{t("workspaces")}</h2>
        </div>

        <form className="inlineForm" onSubmit={submit}>
          <input
            aria-label={t("workspaceName")}
            placeholder={t("workspaceNamePlaceholder")}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <button className="primary" type="submit" disabled={busy}>
            {t("create")}
          </button>
        </form>

        {error && <ErrorNote message={error} />}
        {workspaces === null && !error && <Loading />}
        {workspaces?.length === 0 && <Empty message={t("noWorkspacesYet")} />}

        <div className="cardList">
          {workspaces?.map((workspace) => (
            <Link className="card" key={workspace.id} to={`/workspaces/${workspace.id}`}>
              <span className="cardIcon" aria-hidden="true">
                {workspace.name.slice(0, 1)}
              </span>
              <div>
                <strong>{workspace.name}</strong>
                <small>{workspace.default_locale}</small>
              </div>
              <span className="chevron" aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>
    </Layout>
  );
}
