"""Supported field types and per-type value validation.

The engine is metadata-driven: a record payload is only meaningful relative to
the ``FieldDefinition`` rows of its table. This module owns the value-level
rules; :mod:`backend.app.services.record_service` owns the payload-level rules.
"""
from datetime import date

from backend.app.services.errors import ValidationIssue

TEXT = "text"
LONG_TEXT = "long_text"
NUMBER = "number"
BOOLEAN = "boolean"
DATE = "date"
SINGLE_SELECT = "single_select"
RELATION = "relation"

#: Types the metadata engine accepts today.
SUPPORTED_FIELD_TYPES: tuple[str, ...] = (
    TEXT,
    LONG_TEXT,
    NUMBER,
    BOOLEAN,
    DATE,
    SINGLE_SELECT,
    RELATION,
)

#: Types reserved by the domain model but not implemented yet. Listed so the
#: UI can show them as unavailable instead of pretending they do not exist.
PLANNED_FIELD_TYPES: tuple[str, ...] = (
    "datetime",
    "multi_select",
    "email",
    "phone",
    "user",
    "formula",
)


def select_options(config: dict | None) -> list[str]:
    """Normalize ``config.options`` into a list of stored values.

    Accepts ``["a", "b"]`` or ``[{"value": "a", "label": "A"}, ...]`` so the UI
    can carry localized labels without changing what is stored in the record.
    """
    raw = (config or {}).get("options") or []
    if not isinstance(raw, list):
        return []
    options: list[str] = []
    for item in raw:
        if isinstance(item, str):
            options.append(item)
        elif isinstance(item, dict) and isinstance(item.get("value"), str):
            options.append(item["value"])
    return options


def is_empty(value: object) -> bool:
    """Whether a value counts as "not provided" for a required check."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def coerce_value(key: str, label: str, field_type: str, config: dict | None, value: object):
    """Validate and normalize one value.

    ``key`` identifies the field for the client; ``label`` is what the message
    shows, so a Hebrew-labelled field reports a Hebrew-readable error.

    Returns ``(normalized_value, issue)``; exactly one of the two is meaningful.
    Types are strict on purpose — silent coercion in a schemaless JSONB column
    is how a database quietly becomes untrustworthy.
    """
    if field_type in (TEXT, LONG_TEXT):
        if not isinstance(value, str):
            return None, _type_issue(key, label, field_type, "a string")
        return value, None

    if field_type == NUMBER:
        # bool is a subclass of int in Python; it is not a number here.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, _type_issue(key, label, field_type, "a number")
        return value, None

    if field_type == BOOLEAN:
        if not isinstance(value, bool):
            return None, _type_issue(key, label, field_type, "a boolean")
        return value, None

    if field_type == DATE:
        if not isinstance(value, str):
            return None, _type_issue(key, label, field_type, "an ISO date string (YYYY-MM-DD)")
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return None, _type_issue(key, label, field_type, "an ISO date string (YYYY-MM-DD)")
        return parsed.isoformat(), None

    if field_type == SINGLE_SELECT:
        if not isinstance(value, str):
            return None, _type_issue(key, label, field_type, "one of the configured options")
        options = select_options(config)
        if value not in options:
            allowed = ", ".join(options) or "(no options configured)"
            return None, ValidationIssue(
                field=key,
                code="invalid_option",
                message=f"Field '{label}' must be one of: {allowed}.",
            )
        return value, None

    if field_type == RELATION:
        if not isinstance(value, str):
            return None, _type_issue(key, label, field_type, "a record UUID")
        try:
            import uuid
            return str(uuid.UUID(value)), None
        except ValueError:
            return None, _type_issue(key, label, field_type, "a record UUID")

    return None, ValidationIssue(
        field=key,
        code="unsupported_type",
        message=f"Field '{label}' uses type '{field_type}', which is not supported yet.",
    )


def _type_issue(key: str, label: str, field_type: str, expectation: str) -> ValidationIssue:
    return ValidationIssue(
        field=key,
        code="invalid_type",
        message=f"Field '{label}' of type '{field_type}' expects {expectation}.",
    )
