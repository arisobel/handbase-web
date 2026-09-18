import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { FieldDefinition, FieldValue, RecordRow, SelectOption } from "../api/types";

/** Columns beyond this are hidden from the list; the editor shows everything. */
const MAX_COLUMNS = 4;

function optionLabel(field: FieldDefinition, value: string): string {
  const match = (field.config.options ?? []).find((option: string | SelectOption) =>
    typeof option === "string" ? option === value : option.value === value,
  );
  if (typeof match === "string") return match;
  return match?.label ?? value;
}

export function formatValue(
  field: FieldDefinition,
  value: FieldValue | undefined,
  yes: string,
  no: string,
): string {
  if (value === undefined || value === null) return "—";
  if (field.field_type === "boolean") return value ? yes : no;
  if (field.field_type === "single_select") return optionLabel(field, String(value));
  return String(value);
}

interface RecordListProps {
  fields: FieldDefinition[];
  records: RecordRow[];
}

/**
 * One markup tree for both breakpoints: a table on wide screens, stacked rows
 * on narrow ones (see `.recordTable` in styles.css). Values are read from the
 * field definitions, so the list never hard-codes a domain column.
 */
export default function RecordList({ fields, records }: RecordListProps) {
  const { t } = useTranslation();
  const columns = fields.slice(0, MAX_COLUMNS);
  const yes = t("yes");
  const no = t("no");

  return (
    <div className="tableScroll">
      <table className="recordTable">
        <thead>
          <tr>
            {columns.map((field) => (
              <th key={field.id}>{field.label}</th>
            ))}
            <th className="actionsHeader">{t("actions")}</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id}>
              {columns.map((field, index) => (
                <td key={field.id} data-label={field.label} className={index === 0 ? "primaryCell" : ""}>
                  {formatValue(field, record.data[field.key], yes, no)}
                </td>
              ))}
              <td className="actionsCell">
                <Link to={`/records/${record.id}`}>{t("edit")}</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
