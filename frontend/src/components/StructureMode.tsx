import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export function useStructureMode(workspaceId: string | undefined, allowed: boolean) {
  const key = `handbase:structure-mode:${workspaceId ?? ""}`;
  const [enabled, setEnabled] = useState(() => allowed && localStorage.getItem(key) === "true");
  useEffect(() => { setEnabled(allowed && localStorage.getItem(key) === "true"); }, [key, allowed]);
  const set = (next: boolean) => { setEnabled(next); localStorage.setItem(key, String(next)); };
  return [enabled, set] as const;
}

export function StructureModeToggle({ enabled, onChange }: { enabled: boolean; onChange: (value: boolean) => void }) {
  const { t } = useTranslation();
  return <button type="button" className="actionStructure structureToggle" aria-pressed={enabled} onClick={() => onChange(!enabled)}>
    <span aria-hidden="true">⚙</span> {enabled ? t("structureModeOn") : t("structureModeOff")}
  </button>;
}
