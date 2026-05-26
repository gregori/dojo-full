"""FastAPI application entry point with CORS, rate limiting, and routers."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config import settings
from app.core.middleware import limiter, rate_limit_exceeded_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting Dojo Manager API")
    logger.info(f"Environment: {settings.APP_ENV}")
    yield
    logger.info("Shutting down Dojo Manager API")


app = FastAPI(
    title="Dojo Manager API",
    description="Aikido Dojo Management System",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS middleware — allow_credentials=True requires explicit origins (no wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health")
async def health():
    """Health check endpoint (root level)."""
    return {"status": "ok"}


@app.get("/api/v1/health")
async def health_v1():
    """Health check endpoint (API v1 level)."""
    return {"status": "ok"}
