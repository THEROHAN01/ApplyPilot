"""
Module: main.py
Purpose: FastAPI application factory; mounts routers and CORS.
Author: ApplyPilot
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from middleware.rate_limiter import RateLimitMiddleware
from routers import applications, auth, dashboard, health, jobs, resumes


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(title="ApplyPilot API", version="0.1.0")
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(resumes.router)
    app.include_router(jobs.router)
    app.include_router(applications.router)
    app.include_router(dashboard.router)
    return app


app = create_app()
