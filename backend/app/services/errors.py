"""Domain errors raised by the service layer.

Routers stay thin: they let these bubble up and an application-level handler
turns them into HTTP responses.
"""
from dataclasses import dataclass


class DomainError(Exception):
    """Base class for errors that map to a deterministic HTTP status."""

    status_code = 400
    code = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_payload(self) -> dict:
        return {"code": self.code, "message": self.message}


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


@dataclass
class ValidationIssue:
    field: str | None
    code: str
    message: str

    def to_payload(self) -> dict:
        return {"field": self.field, "code": self.code, "message": self.message}


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"

    def __init__(self, message: str, issues: list[ValidationIssue] | None = None):
        super().__init__(message)
        self.issues = issues or []

    def to_payload(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "errors": [issue.to_payload() for issue in self.issues],
        }
