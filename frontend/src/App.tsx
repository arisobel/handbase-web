import { Navigate, Route, Routes } from "react-router-dom";
import RequireAuth from "./auth/RequireAuth";
import DashboardPage from "./pages/DashboardPage";
import EditRecordPage from "./pages/EditRecordPage";
import LoginPage from "./pages/LoginPage";
import InvitePage from "./pages/InvitePage";
import NewRecordPage from "./pages/NewRecordPage";
import TableRecordsPage from "./pages/TableRecordsPage";
import TableSettingsPage from "./pages/TableSettingsPage";
import WorkspacePage from "./pages/WorkspacePage";
import WorkspaceSettingsPage from "./pages/WorkspaceSettingsPage";

/** Everything except `/login` sits behind a session; the API enforces it too. */
const guarded = (element: React.ReactElement) => <RequireAuth>{element}</RequireAuth>;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/invite/:token" element={<InvitePage />} />
      <Route path="/" element={guarded(<DashboardPage />)} />
      <Route path="/workspaces/:workspaceId" element={guarded(<WorkspacePage />)} />
      <Route
        path="/workspaces/:workspaceId/settings"
        element={guarded(<WorkspaceSettingsPage />)}
      />
      <Route path="/tables/:tableId" element={guarded(<TableRecordsPage />)} />
      <Route path="/tables/:tableId/settings" element={guarded(<TableSettingsPage />)} />
      <Route path="/tables/:tableId/new" element={guarded(<NewRecordPage />)} />
      <Route path="/records/:recordId" element={guarded(<EditRecordPage />)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
