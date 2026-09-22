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
  WorkspaceInvitation,
  CreatedWorkspaceInvitation,
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
  const [invitations, setInvitations] = useState<WorkspaceInvitation[] | null>(null);
  const [createdInvitation, setCreatedInvitation] = useState<CreatedWorkspaceInvitation | null>(null);
  const [name, setName] = useState("");
  const [defaultLocale, setDefaultLocale] = useState<SupportedLocale>("en");
  const [email, setEmail] = useState("");
  const [newRole, setNewRole] = useState<WorkspaceRole>("VIEWER");
  const [onboardingMode, setOnboardingMode] = useState<"existing" | "invite" | "local">("local");
  const [verificationMode, setVerificationMode] = useState<"LINK_ONLY" | "LINK_AND_PIN">("LINK_ONLY");
  const [displayName, setDisplayName] = useState("");
  const [localLocale, setLocalLocale] = useState<SupportedLocale>("en");
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
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
    const requests: [Promise<Workspace>, Promise<WorkspaceMember[]>, Promise<WorkspaceInvitation[]>] = [
      api.getWorkspace(workspaceId),
      canManageMembers ? api.listMembers(workspaceId) : Promise.resolve([]),
      canManageMembers ? api.listInvitations(workspaceId) : Promise.resolve([]),
    ];
    Promise.all(requests)
      .then(([loadedWorkspace, loadedMembers, loadedInvitations]) => {
        setWorkspace(loadedWorkspace);
        setName(loadedWorkspace.name);
        setDefaultLocale(loadedWorkspace.default_locale);
        setMembers(loadedMembers);
        setInvitations(loadedInvitations);
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
    setCreatedInvitation(null);
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
      if (onboardingMode === "local") {
        const created = await api.createLocalUser(workspaceId, { email: email.trim(), display_name: displayName.trim(), role: newRole, preferred_locale: localLocale });
        setMembers((current) => [...(current ?? []), { id: "new", user_id: created.id, email: created.email, display_name: created.display_name, role: created.role, preferred_locale: localLocale, is_active: true, must_change_password: true }]);
        setTemporaryPassword(created.temporary_password); setEmail(""); setDisplayName(""); setNotice(t("localUserCreated")); return;
      }
      if (onboardingMode === "invite") {
        const invitation = await api.createInvitation(workspaceId, { email: email.trim(), role: newRole, verification_mode: verificationMode });
        setInvitations((current) => [invitation, ...(current ?? [])]); setCreatedInvitation(invitation); setEmail(""); setNotice(t("invitationCreated")); return;
      }
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

  const resetMemberPassword = async (member: WorkspaceMember) => {
    if (!window.confirm(t("confirmResetPassword", { name: member.display_name }))) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const reset = await api.resetMemberPassword(workspaceId, member.id);
      setTemporaryPassword(reset.temporary_password);
      setNotice(t("passwordReset"));
    } catch (err) {
      setError(presentError(err, "role"));
    } finally {
      setBusy(false);
    }
  };

  const copyInvitation = async () => {
    if (!createdInvitation) return;
    try {
      await navigator.clipboard.writeText(createdInvitation.invitation_url);
      setNotice(t("invitationLinkCopied"));
    } catch {
      setError(t("operationFailed"));
    }
  };

  const revokeInvitation = async (invitation: WorkspaceInvitation) => {
    setBusy(true);
    try {
      await api.revokeInvitation(workspaceId, invitation.id);
      setInvitations((current) => current?.map((item) => item.id === invitation.id ? { ...item, revoked_at: new Date().toISOString() } : item) ?? []);
    } catch (err) {
      setError(presentError(err, "remove"));
    } finally { setBusy(false); }
  };

  const canEditMember = (member: WorkspaceMember) =>
    canManageMembers
    && (actorRole === "OWNER" || member.role !== "OWNER")
    && !(member.role === "OWNER" && ownerCount <= 1);
  const canResetMemberPassword = (member: WorkspaceMember) =>
    canManageMembers && (actorRole === "OWNER" || member.role !== "OWNER");
  const canManageInvitation = (invitation: WorkspaceInvitation) =>
    canManageMembers && (actorRole === "OWNER" || invitation.role !== "OWNER");

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

          {createdInvitation && (
            <div className="settingsPanel invitationCreated">
              <strong>{createdInvitation.email}</strong>
              <small>{t(`roles.${createdInvitation.role}`)} · {new Date(createdInvitation.expires_at).toLocaleDateString()}</small>
              <button type="button" className="secondary" onClick={() => void copyInvitation()}>{t("copyInvitationLink")}</button>
              {createdInvitation.pin && <p>{t("verificationCode")}: <Technical>{createdInvitation.pin}</Technical></p>}
            </div>
          )}
        </section>
      )}

      {canManageMembers && (
        <section id="members" className="settingsSection">
          <div className="sectionTitle"><h2>{t("members")}</h2></div>
          <form className="memberAddForm settingsPanel" onSubmit={addMember}>
            <div className="formRow"><label htmlFor="onboarding-mode">{t("onboardingMode")}</label><select id="onboarding-mode" value={onboardingMode} onChange={(event) => setOnboardingMode(event.target.value as "existing" | "invite" | "local")}><option value="local">{t("createUser")}</option><option value="existing">{t("existingUser")}</option><option value="invite">{t("inviteUser")}</option></select></div>
            {onboardingMode === "local" && <><div className="formRow"><label htmlFor="local-name">{t("displayName")}</label><input id="local-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} required /></div><div className="formRow"><label htmlFor="local-locale">{t("personalLanguage")}</label><select id="local-locale" value={localLocale} onChange={(event) => setLocalLocale(event.target.value as SupportedLocale)}>{LOCALES.map((locale) => <option key={locale} value={locale}>{t(`locales.${locale}`)}</option>)}</select></div></>}
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
            {onboardingMode === "invite" && <div className="formRow"><label htmlFor="invite-mode">{t("inviteSecurity")}</label><select id="invite-mode" value={verificationMode} onChange={(event) => setVerificationMode(event.target.value as "LINK_ONLY" | "LINK_AND_PIN")}><option value="LINK_ONLY">{t("linkOnly")}</option><option value="LINK_AND_PIN">{t("linkAndPin")}</option></select></div>}
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
            <small className="memberAddHint">{t(`onboardingHint.${onboardingMode}`)}</small>
          </form>
          {temporaryPassword && <div className="settingsPanel"><strong>{t("temporaryPassword")}</strong><p><Technical>{temporaryPassword}</Technical></p></div>}

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
                        {canResetMemberPassword(member) && (
                          <>
                            <button type="button" className="secondary" disabled={busy} onClick={() => void resetMemberPassword(member)}>
                              {t("resetPassword")}
                            </button>
                          </>
                        )}
                        {canEditMember(member) && (
                          <>
                            <button
                              type="button"
                              className="danger"
                              disabled={busy}
                              onClick={() => void removeMember(member)}
                            >
                              {t("remove")}
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </>
          )}
          {invitations && (
            <div className="listPanel">
              <h3>{t("pendingInvitations")}</h3>
              {invitations.filter((item) => !item.accepted_at && !item.revoked_at && new Date(item.expires_at) > new Date()).map((invitation) => (
                <div className="listItem" key={invitation.id}>
                  <div><strong><Technical>{invitation.email}</Technical></strong><small>{t(`roles.${invitation.role}`)} · {new Date(invitation.expires_at).toLocaleDateString()}</small></div>
                  {canManageInvitation(invitation) && <button type="button" className="danger" disabled={busy} onClick={() => void revokeInvitation(invitation)}>{t("revokeInvitation")}</button>}
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </Layout>
  );
}
