"""Health check API endpoints."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", message="School of Life API is running")


@router.get("/health/db", response_model=HealthResponse)
async def health_check_db() -> HealthResponse:
    """Database health check endpoint."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return HealthResponse(status="ok", message="Database connection is working")
            else:
                return HealthResponse(status="error", message="Database query failed")
    except Exception as e:
        return HealthResponse(status="error", message=f"Database connection failed: {str(e)}")


@router.get("/diag/echo")
async def diagnostic_echo(request: Request):
    """Diagnostic endpoint to check headers and origin."""
    return {
        "method": request.method,
        "url": str(request.url),
        "origin": request.headers.get("origin"),
        "host": request.headers.get("host"),
        "user_agent": request.headers.get("user-agent", "")[:50],
        "auth_header_present": "authorization" in request.headers,
        "content_type": request.headers.get("content-type"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
    }
