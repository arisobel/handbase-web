import { useTranslation } from "react-i18next";
import i18n, { applyDocumentDirection } from "./i18n";

const cards = [
  { key: "students", count: 432, icon: "ת" },
  { key: "families", count: 219, icon: "מ" },
  { key: "followup", count: 17, icon: "✓" },
  { key: "tasks", count: 6, icon: "!" },
];

export default function App() {
  const { t } = useTranslation();

  const changeLanguage = async (locale: string) => {
    await i18n.changeLanguage(locale);
    localStorage.setItem("locale", locale);
    applyDocumentDirection(locale);
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">METADATA DATABASE</div>
          <h1>{t("appName")}</h1>
          <p>{t("subtitle")}</p>
        </div>
        <select aria-label={t("language")} value={i18n.language}
          onChange={(e) => changeLanguage(e.target.value)}>
          <option value="en">English</option>
          <option value="he">עברית</option>
          <option value="pt-BR">Português</option>
        </select>
      </header>

      <section className="searchRow">
        <input placeholder={t("search")} />
        <button>+</button>
      </section>

      <section>
        <div className="sectionTitle">
          <h2>{t("tables")}</h2>
          <button className="linkButton">+ {t("newTable")}</button>
        </div>
        <div className="grid">
          {cards.map((card) => (
            <article className="card" key={card.key}>
              <span className="cardIcon">{card.icon}</span>
              <div><strong>{t(card.key)}</strong><small>{card.count} {t("records")}</small></div>
              <span className="chevron">›</span>
            </article>
          ))}
        </div>
      </section>

      <section className="listPanel">
        <h2>{t("recent")}</h2>
        <div className="listItem">
          <div><strong>{t("activeStudents")}</strong><small>187 {t("records")}</small></div><span>›</span>
        </div>
        <div className="listItem">
          <div><strong>{t("needsFollowup")}</strong><small>14 {t("records")}</small></div><span>›</span>
        </div>
      </section>

      <nav className="bottomNav">
        <button>⌂</button><button>▦</button><button>＋</button><button>✓</button><button>☰</button>
      </nav>
    </main>
  );
}
