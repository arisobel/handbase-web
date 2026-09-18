import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: { translation: {
    appName: "Pocket Tables", subtitle: "Your structured information, anywhere.",
    search: "Search...", tables: "Tables", students: "Students", families: "Families",
    followup: "Follow-up", tasks: "My tasks", records: "records", newTable: "New table",
    recent: "Recent lists", activeStudents: "Active students", needsFollowup: "Needs follow-up",
    language: "Language"
  }},
  he: { translation: {
    appName: "Pocket Tables", subtitle: "המידע המסודר שלך, בכל מקום.",
    search: "חיפוש...", tables: "טבלאות", students: "תלמידים", families: "משפחות",
    followup: "מעקב", tasks: "המשימות שלי", records: "רשומות", newTable: "טבלה חדשה",
    recent: "רשימות אחרונות", activeStudents: "תלמידים פעילים", needsFollowup: "דורשים מעקב",
    language: "שפה"
  }},
  "pt-BR": { translation: {
    appName: "Pocket Tables", subtitle: "Suas informações estruturadas, em qualquer lugar.",
    search: "Pesquisar...", tables: "Tabelas", students: "Alunos", families: "Famílias",
    followup: "Acompanhamento", tasks: "Minhas tarefas", records: "registros", newTable: "Nova tabela",
    recent: "Listas recentes", activeStudents: "Alunos ativos", needsFollowup: "Precisam de acompanhamento",
    language: "Idioma"
  }}
};

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem("locale") || "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export function applyDocumentDirection(locale: string) {
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "he" ? "rtl" : "ltr";
}

applyDocumentDirection(i18n.language);
export default i18n;
