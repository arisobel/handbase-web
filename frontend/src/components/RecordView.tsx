import { useTranslation } from "react-i18next";
import type { FieldDefinition, FieldValue } from "../api/types";
import { formatValue } from "./RecordList";

/** Read-only rendering of a record, for members who hold only READ. */
export default function RecordView({
  fields,
  data,
}: {
  fields: FieldDefinition[];
  data: Record<string, FieldValue>;
}) {
  const { t } = useTranslation();
  const yes = t("yes");
  const no = t("no");

  return (
    <dl className="readOnlyRecord">
      {fields.map((field) => (
        <div className="formRow" key={field.id}>
          <dt>{field.label}</dt>
          <dd>{formatValue(field, data[field.key], yes, no)}</dd>
        </div>
      ))}
    </dl>
  );
}
