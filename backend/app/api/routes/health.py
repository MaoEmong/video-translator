from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["system"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "api",
        "checked_at": datetime.now(UTC).isoformat(),
    }
