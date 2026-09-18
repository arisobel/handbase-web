"""Neutral internal identifiers derived from user-supplied labels.

User labels may be entirely Hebrew (``שם פרטי``). Internal keys and slugs stay
ASCII-neutral so they are safe in URLs, JSON keys and future export formats.
"""
import re
import unicodedata
from collections.abc import Iterable

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def _ascii_fold(value: str) -> str:
    """Strip diacritics so ``João`` becomes ``joao`` rather than ``jo o``."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def slugify(value: str, separator: str = "-") -> str:
    """Best-effort ASCII slug. Returns an empty string for non-Latin input."""
    folded = _ascii_fold(value or "").lower()
    return _NON_SLUG.sub(separator, folded).strip(separator)


def unique_identifier(
    label: str,
    taken: Iterable[str],
    *,
    separator: str = "-",
    fallback_prefix: str = "item",
    max_length: int = 120,
) -> str:
    """Build a slug that is unique within ``taken``.

    Labels with no Latin characters fall back to ``<prefix><sep><n>`` so a
    Hebrew-only table or field still gets a usable identifier.
    """
    existing = set(taken)
    base = slugify(label, separator)[:max_length]
    if not base:
        index = 1
        while f"{fallback_prefix}{separator}{index}" in existing:
            index += 1
        return f"{fallback_prefix}{separator}{index}"

    if base not in existing:
        return base

    index = 2
    while True:
        suffix = f"{separator}{index}"
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
        if candidate not in existing:
            return candidate
        index += 1
