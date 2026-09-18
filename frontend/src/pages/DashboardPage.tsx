import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client";
import type { Workspace } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";

/**
 * Workspace selection.
 *
 * A user with exactly one workspace is sent straight into it — but the list is
 * always what drives the decision, so nothing here assumes a single workspace
 * is permanent.
 */
export default function DashboardPage() {
  const { t } = useTranslation();
  const { session, membershipFor } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api
      .listWorkspaces()
      .then(setWorkspaces)
      .catch((err: Error) => setError(err.message));
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() === "") return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createWorkspace({ name: name.trim() });
      setWorkspaces((current) => [...(current ?? []), created]);
      setName("");
      setCreating(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // Skip the picker when there is nothing to pick — but only before the user
  // has started creating a second one.
  if (!creating && workspaces?.length === 1) {
    return <Navigate to={`/workspaces/${workspaces[0].id}`} replace />;
  }

  return (
    <Layout title={t("appName")} subtitle={t("chooseWorkspace")}>
      <section>
        <div className="sectionTitle">
          <h2>{t("workspaces")}</h2>
          {!creating && (
            <button type="button" className="linkButton" onClick={() => setCreating(true)}>
              + {t("newWorkspace")}
            </button>
          )}
        </div>

        {creating && (
          <form className="inlineForm" onSubmit={submit}>
            <input
              aria-label={t("workspaceName")}
              placeholder={t("workspaceNamePlaceholder")}
              value={name}
              autoFocus
              onChange={(event) => setName(event.target.value)}
            />
            <button className="primary" type="submit" disabled={busy}>
              {t("create")}
            </button>
          </form>
        )}

        {error && <ErrorNote message={error} />}
        {workspaces === null && !error && <Loading />}
        {workspaces?.length === 0 && !creating && <Empty message={t("noWorkspacesYet")} />}

        <div className="cardList">
          {workspaces?.map((workspace) => (
            <Link className="card" key={workspace.id} to={`/workspaces/${workspace.id}`}>
              <span className="cardIcon" aria-hidden="true">
                {workspace.name.slice(0, 1)}
              </span>
              <div>
                <strong>{workspace.name}</strong>
                <small>{t(`roles.${membershipFor(workspace.id)?.role ?? "VIEWER"}`)}</small>
              </div>
              <span className="chevron" aria-hidden="true" />
            </Link>
          ))}
        </div>

        {session && session.memberships.length === 0 && workspaces?.length === 0 && (
          <p className="muted">{t("noMembershipHint")}</p>
        )}
      </section>
    </Layout>
  );
}
