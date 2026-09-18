from fastapi import APIRouter

from backend.app.api.v1 import auth, fields, records, tables, workspaces

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(tables.router)
api_router.include_router(fields.router)
api_router.include_router(records.router)

__all__ = ["api_router"]
