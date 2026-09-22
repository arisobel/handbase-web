import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

/** Gate for every authenticated route. The server enforces this too. */
export default function RequireAuth({ children }: { children: React.ReactElement }) {
  const { session } = useAuth();
  const { t } = useTranslation();
  const location = useLocation();

  if (session === undefined) {
    return (
      <main className="shell">
        <p className="muted">{t("loading")}</p>
      </main>
    );
  }

  if (session === null) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (session.user.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  return children;
}
