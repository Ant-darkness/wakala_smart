from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine, get_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown resources."""

    yield

    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description=("Backend API for WAKALA SMART agent and management applications."),
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    openapi_url=("/openapi.json" if settings.APP_ENV != "production" else None),
    lifespan=lifespan,
)


# Register all version 1 API endpoints.
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Return basic API information."""

    return {
        "message": "Welcome to WAKALA SMART API",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/health/live", tags=["Health"])
def liveness_check() -> dict[str, str]:
    """Check whether the application process is alive."""

    return {
        "status": "ok",
        "service": "wakala-smart-api",
    }


@app.get("/health/ready", tags=["Health"])
def readiness_check() -> dict[str, str]:
    """Check whether the application can access its database."""

    db: Session = next(get_db())

    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "service": "wakala-smart-api",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        ) from None

    finally:
        db.close()
