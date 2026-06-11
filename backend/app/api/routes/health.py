from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "repo-intelligence",
    }


@router.get("/health/ready")
async def readiness_check():
    return {"status": "ready"}
