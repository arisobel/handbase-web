"""Password hashing and token primitives.

Nothing cryptographic is invented here: password hashing is argon2id via
``argon2-cffi`` and access tokens are HS256 JWTs via ``PyJWT``. This module only
wires those libraries to the application's settings.
"""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.app.core.config import get_settings

#: argon2id with the library defaults, which track the OWASP recommendation.
_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(Exception):
    """Raised when an access token is absent, malformed, expired or wrong-typed."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Whether a stored hash predates the current argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def create_access_token(user_id: uuid.UUID, *, now: datetime | None = None) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for a short-lived access token."""
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    ttl = settings.access_token_ttl_seconds
    payload = {
        "sub": str(user_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=ttl)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256"), ttl


def decode_access_token(token: str) -> uuid.UUID:
    """Return the subject of a valid access token, or raise ``InvalidTokenError``."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    # A refresh token must never be usable as an access token.
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Unexpected token type.")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Malformed subject.") from exc


def generate_refresh_token() -> str:
    """An opaque, high-entropy refresh token. Never stored as-is."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 digest used as the stored lookup key.

    A fast digest is correct here (unlike for passwords): the token already has
    ~288 bits of entropy, so there is nothing to brute-force.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_invitation_token() -> str:
    """Opaque high-entropy, one-time token; only its SHA-256 digest is stored."""
    return secrets.token_urlsafe(48)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
