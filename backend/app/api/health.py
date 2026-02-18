"""Health check for frontend/load balancer."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "waifu-tutor-api"}
