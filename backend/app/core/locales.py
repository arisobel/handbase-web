"""Supported UI locales and locale resolution.

This module is the backend source of truth for values persisted on users and
workspaces.  Keeping validation here prevents each service from accepting a
slightly different set of locale strings.
"""
from enum import StrEnum

from backend.app.core.config import get_settings
from backend.app.services.errors import ValidationError, ValidationIssue


class SupportedLocale(StrEnum):
    ENGLISH = "en"
    HEBREW = "he"
    PORTUGUESE_BRAZIL = "pt-BR"


SUPPORTED_LOCALES = tuple(locale.value for locale in SupportedLocale)


def validate_locale(locale: str, *, field: str) -> str:
    if locale not in SUPPORTED_LOCALES:
        raise ValidationError(
            f"Unsupported locale '{locale}'.",
            [
                ValidationIssue(
                    field=field,
                    code="unsupported_locale",
                    message="Supported locales: " + ", ".join(SUPPORTED_LOCALES) + ".",
                )
            ],
        )
    return locale


def application_default_locale() -> str:
    configured = get_settings().default_locale
    return configured if configured in SUPPORTED_LOCALES else SupportedLocale.ENGLISH.value


def resolve_locale(
    preferred_locale: str | None,
    workspace_default_locale: str | None = None,
) -> str:
    """Resolve personal preference -> workspace default -> application default."""
    if preferred_locale in SUPPORTED_LOCALES:
        return preferred_locale
    if workspace_default_locale in SUPPORTED_LOCALES:
        return workspace_default_locale
    return application_default_locale()
