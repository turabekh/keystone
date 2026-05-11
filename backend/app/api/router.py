from fastapi import APIRouter

from app.api.v1 import counties, properties

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(counties.router)
api_router.include_router(properties.router)