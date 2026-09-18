import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import i18n from "../i18n";
import Technical from "./Technical";

interface LayoutProps {
  title: string;
  subtitle?: string;
  /** Route to the parent screen. The chevron flips with the document direction. */
  backTo?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export default function Layout({ title, subtitle, backTo, actions, children }: LayoutProps) {
  const { t } = useTranslation();
  const { session, logout, setLocale } = useAuth();
  const navigate = useNavigate();

  const signOut = async () => {
    await logout();
    navigate("/login", { replace: true });
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
        </div>

        <div className="topbarAside">
          <select
            aria-label={t("language")}
            value={i18n.language}
            onChange={(event) => void setLocale(event.target.value)}
          >
            <option value="en">English</option>
            <option value="he">עברית</option>
            <option value="pt-BR">Português</option>
          </select>

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
