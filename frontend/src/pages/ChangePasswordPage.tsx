import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote } from "../components/Feedback";
import { useAuth } from "../auth/AuthContext";

export default function ChangePasswordPage() {
  const { t } = useTranslation(); const navigate = useNavigate(); const { refreshIdentity } = useAuth();
  const [current, setCurrent] = useState(""); const [next, setNext] = useState(""); const [confirm, setConfirm] = useState(""); const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); if (next !== confirm) { setError(t("passwordMismatch")); return; } setBusy(true); setError(null); try { await api.changePassword({ current_password: current, new_password: next }); await refreshIdentity(); navigate("/", { replace: true }); } catch (err) { setError((err as Error).message); } finally { setBusy(false); } };
  return <main className="shell loginShell"><div className="loginCard"><h1>{t("changePassword")}</h1><form className="form" onSubmit={submit}><div className="formRow"><label>{t("currentPassword")}</label><input type="password" className="technical" value={current} onChange={(e) => setCurrent(e.target.value)} /></div><div className="formRow"><label>{t("newPassword")}</label><input type="password" className="technical" value={next} onChange={(e) => setNext(e.target.value)} /></div><div className="formRow"><label>{t("confirmPassword")}</label><input type="password" className="technical" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></div>{error && <ErrorNote message={error} />}<button className="primary" disabled={busy}>{t("save")}</button></form></div></main>;
}
