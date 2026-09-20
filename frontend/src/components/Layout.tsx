import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import i18n from "../i18n";
import type { SupportedLocale } from "../api/types";
import Technical from "./Technical";

interface LayoutProps {
  title: string;
  subtitle?: string;
  /** Present on workspace-scoped screens to enable the persistent switcher. */
  workspaceId?: string;
  /** Route to the parent screen. The chevron flips with the document direction. */
  backTo?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export default function Layout({ title, subtitle, workspaceId, backTo, actions, children }: LayoutProps) {
  const { t } = useTranslation();
  const { session, logout, setLocale, refreshIdentity } = useAuth();
  const navigate = useNavigate();
  const [localeStatus, setLocaleStatus] = useState<"saved" | "error" | null>(null);
  const [workspaceMenuOpen, setWorkspaceMenuOpen] = useState(false);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceLocale, setWorkspaceLocale] = useState<SupportedLocale | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [workspaceBusy, setWorkspaceBusy] = useState(false);
  const activeWorkspace = session?.memberships.find((membership) => membership.workspace_id === workspaceId);
  const creationLocale = workspaceLocale ?? session?.user.preferred_locale ?? session?.effective_locale ?? "en";

  const signOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const changeLocale = async (locale: SupportedLocale) => {
    setLocaleStatus(null);
    try {
      await setLocale(locale);
      setLocaleStatus("saved");
    } catch {
      setLocaleStatus("error");
    }
  };

  const switchWorkspace = (id: string) => {
    setWorkspaceMenuOpen(false);
    setCreatingWorkspace(false);
    navigate(`/workspaces/${id}`);
  };

  const createWorkspace = async () => {
    if (workspaceName.trim() === "") return;
    setWorkspaceBusy(true);
    setWorkspaceError(null);
    try {
      const created = await api.createWorkspace({
        name: workspaceName.trim(),
        default_locale: creationLocale,
      });
      await refreshIdentity();
      setWorkspaceName("");
      setWorkspaceLocale(null);
      setCreatingWorkspace(false);
      setWorkspaceMenuOpen(false);
      navigate(`/workspaces/${created.id}`);
    } catch {
      setWorkspaceError(t("workspaceCreationFailed"));
    } finally {
      setWorkspaceBusy(false);
    }
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div className="topbarMain">
          {backTo && (
            <Link className="backLink" to={backTo}>
              <span className="chevronBack" aria-hidden="true" />
              {t("back")}
            </Link>
          )}
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
          {workspaceId && (
            <div className="workspaceSwitcher">
              <span className="workspaceSwitcherLabel">{t("workspace")}</span>
              <button
                type="button"
                className="workspaceSwitcherButton"
                aria-expanded={workspaceMenuOpen}
                aria-haspopup="menu"
                onClick={() => {
                  setWorkspaceMenuOpen((open) => !open);
                  setWorkspaceError(null);
                }}
              >
                <span>{activeWorkspace?.workspace_name ?? t("workspace")}</span>
                <span className="workspaceSwitcherCaret" aria-hidden="true">▾</span>
              </button>
              {workspaceMenuOpen && (
                <div className="workspaceMenu" role="menu">
                  <div className="workspaceMenuList">
                    {session?.memberships.map((membership) => (
                      <button
                        key={membership.workspace_id}
                        type="button"
                        className={membership.workspace_id === workspaceId ? "workspaceMenuItem active" : "workspaceMenuItem"}
                        role="menuitem"
                        onClick={() => switchWorkspace(membership.workspace_id)}
                      >
                        <span>{membership.workspace_name}</span>
                        {membership.workspace_id === workspaceId && <span aria-label={t("activeWorkspace")}>✓</span>}
                      </button>
                    ))}
                  </div>
                  <div className="workspaceMenuActions">
                    <button
                      type="button"
                      className="workspaceMenuItem"
                      role="menuitem"
                      onClick={() => {
                        setCreatingWorkspace((open) => !open);
                        setWorkspaceError(null);
                      }}
                    >
                      + {t("createNewWorkspace")}
                    </button>
                    <button
                      type="button"
                      className="workspaceMenuItem"
                      role="menuitem"
                      onClick={() => {
                        setWorkspaceMenuOpen(false);
                        navigate("/?view=all");
                      }}
                    >
                      {t("viewAllWorkspaces")}
                    </button>
                  </div>
                  {creatingWorkspace && (
                    <form
                      className="workspaceCreateForm"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void createWorkspace();
                      }}
                    >
                      <label htmlFor="workspace-switcher-name">{t("workspaceName")}</label>
                      <input
                        id="workspace-switcher-name"
                        value={workspaceName}
                        autoFocus
                        onChange={(event) => setWorkspaceName(event.target.value)}
                      />
                      <label htmlFor="workspace-switcher-locale">{t("defaultLanguage")}</label>
                      <select
                        id="workspace-switcher-locale"
                        value={creationLocale}
                        onChange={(event) => setWorkspaceLocale(event.target.value as SupportedLocale)}
                      >
                        <option value="en">{t("locales.en")}</option>
                        <option value="he">{t("locales.he")}</option>
                        <option value="pt-BR">{t("locales.pt-BR")}</option>
                      </select>
                      {workspaceError && <small className="workspaceCreateError" role="alert">{workspaceError}</small>}
                      <button className="primary" type="submit" disabled={workspaceBusy}>
                        {t("create")}
                      </button>
                    </form>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="topbarAside">
          <span className="languageLabel">{t("personalLanguage")}</span>
          <select
            aria-label={t("personalLanguage")}
            value={i18n.language}
            onChange={(event) => void changeLocale(event.target.value as SupportedLocale)}
          >
            <option value="en">English</option>
            <option value="he">עברית</option>
            <option value="pt-BR">Português</option>
          </select>
          {localeStatus && (
            <small className={`localeStatus ${localeStatus}`} role="status">
              {t(localeStatus === "saved" ? "languageSaved" : "languageSaveFailed")}
            </small>
          )}

          {session && (
            <div className="account">
              {/* The address is LTR even inside a Hebrew layout. */}
              <Technical className="accountEmail">{session.user.email}</Technical>
              <button type="button" className="linkButton" onClick={() => void signOut()}>
                {t("signOut")}
              </button>
            </div>
          )}
        </div>
      </header>

      {actions && <div className="actionRow">{actions}</div>}
      {children}
    </main>
  );
}
