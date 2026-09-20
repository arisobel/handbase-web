import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import {
  ApiError,
  type SupportedLocale,
  Workspace,
  WorkspaceMember,
  WorkspaceRole,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorNote, Loading } from "../components/Feedback";
import Layout from "../components/Layout";
import Technical from "../components/Technical";

const ROLES: WorkspaceRole[] = ["OWNER", "ADMIN", "EDITOR", "VIEWER"];
const LOCALES: SupportedLocale[] = ["en", "he", "pt-BR"];

export default function WorkspaceSettingsPage() {
  const { t } = useTranslation();
  const { workspaceId = "" } = useParams();
  const { session, can, membershipFor, applyWorkspaceLocale, refreshIdentity } = useAuth();
  const canManageMembers = can(workspaceId, "manage_members");
  const canManageWorkspace = can(workspaceId, "manage_workspace");
  const actorRole = membershipFor(workspaceId)?.role;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[] | null>(null);
  const [name, setName] = useState("");
  const [defaultLocale, setDefaultLocale] = useState<SupportedLocale>("en");
  const [email, setEmail] = useState("");
  const [newRole, setNewRole] = useState<WorkspaceRole>("VIEWER");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ownerCount = members?.filter((member) => member.role === "OWNER").length ?? 0;

  const presentError = (err: unknown, action: "add" | "role" | "remove" | "general") => {
    if (!(err instanceof ApiError)) return t("operationFailed");
    if (action === "add" && err.status === 404) return t("accountNotFound");
    if (err.status === 409) {
      if (err.message.includes("already a member")) return t("duplicateMember");
      if (err.message.includes("last OWNER")) return t("lastOwnerProtected");
    }
    if (err.status === 403) return t("ownerProtected");
    return t("operationFailed");
  };

  useEffect(() => {
    setError(null);
    const requests: [Promise<Workspace>, Promise<WorkspaceMember[]>] = [
      api.getWorkspace(workspaceId),
      canManageMembers ? api.listMembers(workspaceId) : Promise.resolve([]),
    ];
    Promise.all(requests)
      .then(([loadedWorkspace, loadedMembers]) => {
        setWorkspace(loadedWorkspace);
        setName(loadedWorkspace.name);
        setDefaultLocale(loadedWorkspace.default_locale);
        setMembers(loadedMembers);
        applyWorkspaceLocale(loadedWorkspace.default_locale);
      })
    .catch(() => setError(t("operationFailed")));
  }, [workspaceId, canManageMembers, applyWorkspaceLocale]);

  const saveGeneral = async (event: FormEvent) => {
    event.preventDefault();
    if (!canManageWorkspace || name.trim() === "") return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.updateWorkspace(workspaceId, {
        name: name.trim(),
        default_locale: defaultLocale,
      });
      setWorkspace(updated);
      applyWorkspaceLocale(updated.default_locale);
      setNotice(t("settingsSaved"));
    } catch (err) {
      setError(presentError(err, "general"));
    } finally {
      setBusy(false);
    }
  };

  const addMember = async (event: FormEvent) => {
    event.preventDefault();
    if (email.trim() === "") return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await api.addMember(workspaceId, {
        email: email.trim(),
        role: newRole,
      });
      setMembers((current) => [...(current ?? []), created]);
      setEmail("");
      setNewRole("VIEWER");
      setNotice(t("memberAdded"));
    } catch (err) {
      setError(presentError(err, "add"));
    } finally {
      setBusy(false);
    }
  };

  const changeRole = async (member: WorkspaceMember, role: WorkspaceRole) => {
    if (member.role === role) return;
    if (!window.confirm(t("confirmRoleChange"))) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.updateMember(workspaceId, member.id, role);
      setMembers((current) => current?.map((item) => (item.id === member.id ? updated : item)) ?? []);
      if (session?.user.id === member.user_id) await refreshIdentity();
      setNotice(t("roleUpdated"));
    } catch (err) {
      setError(presentError(err, "role"));
    } finally {
      setBusy(false);
    }
  };

  const removeMember = async (member: WorkspaceMember) => {
    if (!window.confirm(t("confirmRemoveMember", { name: member.display_name }))) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.removeMember(workspaceId, member.id);
      setMembers((current) => current?.filter((item) => item.id !== member.id) ?? []);
      if (session?.user.id === member.user_id) await refreshIdentity();
      setNotice(t("memberRemoved"));
    } catch (err) {
      setError(presentError(err, "remove"));
    } finally {
      setBusy(false);
    }
  };

  const canEditMember = (member: WorkspaceMember) =>
    canManageMembers
    && (actorRole === "OWNER" || member.role !== "OWNER")
    && !(member.role === "OWNER" && ownerCount <= 1);

  if (!canManageMembers && !canManageWorkspace) {
    return (
      <Layout title={t("workspaceSettings")} workspaceId={workspaceId} backTo={`/workspaces/${workspaceId}`}>
        <ErrorNote message={t("settingsForbidden")} />
      </Layout>
    );
  }

  return (
    <Layout
      title={workspace ? t("workspaceSettingsFor", { name: workspace.name }) : t("workspaceSettings")}
      subtitle={actorRole ? `${t("currentRole")}: ${t(`roles.${actorRole}`)}` : undefined}
      workspaceId={workspaceId}
      backTo={`/workspaces/${workspaceId}`}
    >
      {error && <ErrorNote message={error} />}
      {notice && <p className="successNote" role="status">{notice}</p>}
      {!workspace && !error && <Loading />}

      {workspace && (
        <nav className="settingsTabs" aria-label={t("workspaceSettings")}>
          <a href="#general">{t("generalTab")}</a>
          {canManageMembers && <a href="#members">{t("membersTab")}</a>}
        </nav>
      )}

      {workspace && (
        <section id="general" className="settingsSection">
          <div className="sectionTitle"><h2>{t("general")}</h2></div>
          <form className="form settingsPanel" onSubmit={saveGeneral}>
            <div className="formRow">
              <label htmlFor="workspace-settings-name">{t("workspaceName")}</label>
              <input
                id="workspace-settings-name"
                value={name}
                disabled={!canManageWorkspace}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div className="formRow">
              <label htmlFor="workspace-default-locale">{t("defaultLanguage")}</label>
              <select
                id="workspace-default-locale"
                value={defaultLocale}
                disabled={!canManageWorkspace}
                onChange={(event) => setDefaultLocale(event.target.value as SupportedLocale)}
              >
                {LOCALES.map((locale) => (
                  <option key={locale} value={locale}>{t(`locales.${locale}`)}</option>
                ))}
              </select>
              <small>{t("workspaceLanguageHint")}</small>
            </div>
            {canManageWorkspace && (
              <div className="formActions">
                <button className="primary" type="submit" disabled={busy}>{t("save")}</button>
              </div>
            )}
            {!canManageWorkspace && <p className="muted compact">{t("ownerOnlyGeneral")}</p>}
          </form>
        </section>
      )}

      {canManageMembers && (
        <section id="members" className="settingsSection">
          <div className="sectionTitle"><h2>{t("members")}</h2></div>
          <form className="memberAddForm settingsPanel" onSubmit={addMember}>
            <div className="formRow">
              <label htmlFor="member-email">{t("email")}</label>
              <input
                id="member-email"
                className="technical"
                type="email"
                value={email}
                placeholder="teacher@example.com"
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className="formRow">
              <label htmlFor="member-role">{t("role")}</label>
              <select
                id="member-role"
                value={newRole}
                onChange={(event) => setNewRole(event.target.value as WorkspaceRole)}
              >
                {ROLES.filter((role) => actorRole === "OWNER" || role !== "OWNER").map((role) => (
                  <option key={role} value={role}>{t(`roles.${role}`)}</option>
                ))}
              </select>
            </div>
            <button className="primary memberAddButton" type="submit" disabled={busy}>
              {t("addMember")}
            </button>
            <small className="memberAddHint">{t("existingUsersOnly")}</small>
          </form>

          {members === null && !error && <Loading />}
          {members && (
            <>
              {members.length === 1 && <p className="muted compact">{t("onlyMember")}</p>}
              <div className="tableScroll">
              <table className="recordTable memberTable">
                <thead>
                  <tr>
                    <th>{t("nameAndEmail")}</th>
                    <th>{t("role")}</th>
                    <th>{t("language")}</th>
                    <th>{t("status")}</th>
                    <th className="actionsHeader">{t("actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.id}>
                      <td className="primaryCell" data-label={t("nameAndEmail")}>
                        <strong>{member.display_name}</strong>
                        <small><Technical>{member.email}</Technical></small>
                      </td>
                      <td data-label={t("role")}>
                        {canEditMember(member) ? (
                          <select
                            aria-label={t("roleFor", { name: member.display_name })}
                            value={member.role}
                            disabled={busy}
                            onChange={(event) => void changeRole(member, event.target.value as WorkspaceRole)}
                          >
                            {ROLES.filter((role) => actorRole === "OWNER" || role !== "OWNER").map((role) => (
                              <option key={role} value={role}>{t(`roles.${role}`)}</option>
                            ))}
                          </select>
                        ) : (
                          <>
                            <span>{t(`roles.${member.role}`)}</span>
                            {member.role === "OWNER" && (
                              <small className="memberRoleHint">
                                {t(ownerCount <= 1 ? "lastOwnerProtected" : "ownerProtected")}
                              </small>
                            )}
                          </>
                        )}
                      </td>
                      <td data-label={t("language")}>
                        {member.preferred_locale
                          ? t(`locales.${member.preferred_locale}`)
                          : t("workspaceDefault")}
                      </td>
                      <td data-label={t("status")}>
                        <span className={member.is_active ? "statusBadge" : "statusBadge inactive"}>
                          {t(member.is_active ? "active" : "inactive")}
                        </span>
                      </td>
                      <td className="actionsCell" data-label={t("actions")}>
                        {canEditMember(member) && (
                          <button
                            type="button"
                            className="danger"
                            disabled={busy}
                            onClick={() => void removeMember(member)}
                          >
                            {t("remove")}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </>
          )}
        </section>
      )}
    </Layout>
  );
}
