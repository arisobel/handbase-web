import { useTranslation } from "react-i18next";

export function Loading() {
  const { t } = useTranslation();
  return <p className="muted">{t("loading")}</p>;
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="errorNote" role="alert">
      {message}
    </p>
  );
}

export function Empty({ message }: { message: string }) {
  return <p className="empty">{message}</p>;
}
