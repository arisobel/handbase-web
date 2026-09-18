from fastapi import APIRouter

from backend.app.services.field_types import PLANNED_FIELD_TYPES, SUPPORTED_FIELD_TYPES

router = APIRouter()


@router.get("/meta/field-types", deprecated=True)
def field_types():
    """Legacy catalog endpoint. Use ``/api/v1/field-types`` instead.

    ``items`` used to advertise types the engine could not actually store; it
    now lists only the supported ones.
    """
    return {
        "items": list(SUPPORTED_FIELD_TYPES),
        "supported": list(SUPPORTED_FIELD_TYPES),
        "planned": list(PLANNED_FIELD_TYPES),
    }
