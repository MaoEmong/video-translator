from fastapi import APIRouter

from app.api.routes.artifacts import router as artifacts_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.videos import router as videos_router

api_router = APIRouter()
api_router.include_router(artifacts_router)
api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(videos_router)
