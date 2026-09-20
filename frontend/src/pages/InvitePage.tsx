import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError, type PublicInvitation, type SupportedLocale } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorNote, Loading } from "../components/Feedback";
import Technical from "../components/Technical";

export default function InvitePage() {
  const { t } = useTranslation();
  const { token = "" } = useParams();
  const { session, refreshIdentity } = useAuth();
  const navigate = useNavigate();
  const [invite, setInvite] = useState<PublicInvitation | null>(null);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [locale, setLocale] = useState<SupportedLocale>("en");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getInvitation(token).then((loaded) => {
      setInvite(loaded);
      setLocale(localStorage.getItem("locale") as SupportedLocale || loaded.workspace_default_locale || "en");
    }).catch(() => setError(t("invitationUnavailable")));
  }, [token, t]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!session && password !== confirm) {
      setError(t("passwordMismatch"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const accepted = await api.acceptInvitation(token, session ? {} : {
        display_name: name.trim(), password, preferred_locale: locale,
      });
      if (session) await refreshIdentity();
      navigate(`/workspaces/${accepted.workspace_id}`, { replace: true });
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.status === 409 ? t("invitationSignInRequired") : t("invitationUnavailable"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="shell loginShell">
      <div className="loginCard inviteCard">
        {!invite && !error && <Loading />}
        {error && <ErrorNote message={error} />}
        {invite && (
          <>
            <header className="loginHeader">
              <h1>{t("invitedTo", { workspace: invite.workspace_name })}</h1>
              <p><Technical>{invite.email}</Technical> · {t(`roles.${invite.role}`)}</p>
            </header>
            {invite.account_exists && !session ? (
              <>
                <p>{t("invitationExistingAccount")}</p>
                <Link className="primary buttonLink" to={`/login?invite=${token}`}>{t("signIn")}</Link>
              </>
            ) : (
              <form className="form" onSubmit={submit}>
                {!session && <>
                  <div className="formRow"><label htmlFor="invite-name">{t("displayName")}</label><input id="invite-name" value={name} onChange={(event) => setName(event.target.value)} /></div>
                  <div className="formRow"><label htmlFor="invite-password">{t("password")}</label><input id="invite-password" type="password" className="technical" dir="ltr" value={password} onChange={(event) => setPassword(event.target.value)} /></div>
                  <div className="formRow"><label htmlFor="invite-confirm">{t("confirmPassword")}</label><input id="invite-confirm" type="password" className="technical" dir="ltr" value={confirm} onChange={(event) => setConfirm(event.target.value)} /></div>
                  <div className="formRow"><label htmlFor="invite-locale">{t("personalLanguage")}</label><select id="invite-locale" value={locale} onChange={(event) => setLocale(event.target.value as SupportedLocale)}><option value="en">{t("locales.en")}</option><option value="he">{t("locales.he")}</option><option value="pt-BR">{t("locales.pt-BR")}</option></select></div>
                </>}
                <button className="primary" type="submit" disabled={busy}>{t("createAccountAndJoin")}</button>
              </form>
            )}
          </>
        )}
      </div>
    </main>
  );
}
