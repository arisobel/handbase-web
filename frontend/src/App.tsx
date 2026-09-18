import { Navigate, Route, Routes } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import EditRecordPage from "./pages/EditRecordPage";
import NewRecordPage from "./pages/NewRecordPage";
import TableRecordsPage from "./pages/TableRecordsPage";
import TableSettingsPage from "./pages/TableSettingsPage";
import WorkspacePage from "./pages/WorkspacePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/workspaces/:workspaceId" element={<WorkspacePage />} />
      <Route path="/tables/:tableId" element={<TableRecordsPage />} />
      <Route path="/tables/:tableId/settings" element={<TableSettingsPage />} />
      <Route path="/tables/:tableId/new" element={<NewRecordPage />} />
      <Route path="/records/:recordId" element={<EditRecordPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
