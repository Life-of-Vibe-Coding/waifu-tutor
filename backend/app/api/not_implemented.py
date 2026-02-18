"""Placeholder routes that return 501 until migrated."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def not_implemented(_request: Request, path: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "message": "This endpoint is not yet implemented in the Python backend.",
            "path": path,
        },
    )
