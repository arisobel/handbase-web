import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import i18n, { applyDocumentDirection } from "../i18n";

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

  const changeLanguage = async (locale: string) => {
    await i18n.changeLanguage(locale);
    localStorage.setItem("locale", locale);
    applyDocumentDirection(locale);
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
        <select
          aria-label={t("language")}
          value={i18n.language}
          onChange={(event) => void changeLanguage(event.target.value)}
        >
          <option value="en">English</option>
          <option value="he">עברית</option>
          <option value="pt-BR">Português</option>
        </select>
      </header>

      {actions && <div className="actionRow">{actions}</div>}
      {children}
    </main>
  );
}
