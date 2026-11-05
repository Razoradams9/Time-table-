"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    accounts,
    auth,
    compensations,
    courses,
    dashboard,
    leaves,
    notifications,
    reference,
    substitutions,
    timetable,
)

logging.basicConfig(level=logging.INFO)

_DEFAULT_SECRET = "change-me-in-production-please-use-a-long-random-string"

app = FastAPI(title=settings.app_name, version="1.0.0")

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if "*" not in _origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app" if "*" not in _origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Create tables if they don't exist. (For real deployments use migrations.)
    Base.metadata.create_all(bind=engine)
    if settings.secret_key == _DEFAULT_SECRET:
        logging.getLogger(__name__).warning(
            "SECRET_KEY is still the insecure default; set SECRET_KEY in backend/.env before deploying"
        )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/branding")
def branding() -> dict:
    return {
        "institution_name": settings.institution_name,
        "institution_subtitle": settings.institution_subtitle,
        "department_name": settings.department_name,
        "product_name": settings.product_name,
        "semester_label": settings.semester_label,
    }


app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(reference.router)
app.include_router(timetable.router)
app.include_router(leaves.router)
app.include_router(substitutions.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(courses.router)
app.include_router(compensations.router)
