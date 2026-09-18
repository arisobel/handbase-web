import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorNote } from "../components/Feedback";
import i18n, { applyDocumentDirection } from "../i18n";

export default function LoginPage() {
  const { t } = useTranslation();
  const { session, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Before signing in there is no account preference, so the picker is local.
  const changeLanguage = async (locale: string) => {
    await i18n.changeLanguage(locale);
    localStorage.setItem("locale", locale);
    applyDocumentDirection(locale);
  };

  if (session) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from && from !== "/login" ? from : "/"} replace />;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : "/", { replace: true });
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.status === 401 ? t("invalidCredentials") : apiError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="shell loginShell">
      <div className="loginCard">
        <header className="loginHeader">
          <h1>{t("appName")}</h1>
          <p>{t("signInSubtitle")}</p>
        </header>

        <form className="form" onSubmit={submit}>
          <div className="formRow">
            <label htmlFor="login-email">{t("email")}</label>
            {/* An email is always LTR, even on a Hebrew page. */}
            <input
              id="login-email"
              type="email"
              className="technical"
              dir="ltr"
              autoComplete="username"
              inputMode="email"
              placeholder="name@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="formRow">
            <label htmlFor="login-password">{t("password")}</label>
            <input
              id="login-password"
              type="password"
              className="technical"
              dir="ltr"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {error && <ErrorNote message={error} />}

          <div className="formActions">
            <button className="primary" type="submit" disabled={busy}>
              {busy ? t("signingIn") : t("signIn")}
            </button>
          </div>
        </form>

        <footer className="loginFooter">
          <label htmlFor="login-language">{t("language")}</label>
          <select
            id="login-language"
            value={i18n.language}
            onChange={(event) => void changeLanguage(event.target.value)}
          >
            <option value="en">English</option>
            <option value="he">עברית</option>
            <option value="pt-BR">Português</option>
          </select>
        </footer>
      </div>
    </main>
  );
}
