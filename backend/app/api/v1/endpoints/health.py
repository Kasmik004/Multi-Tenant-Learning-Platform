from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DBSession

router = APIRouter()


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: DBSession) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
