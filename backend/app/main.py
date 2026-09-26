"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    auth,
    dashboard,
    leaves,
    notifications,
    reference,
    substitutions,
    timetable,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Create tables if they don't exist. (For real deployments use migrations.)
    Base.metadata.create_all(bind=engine)


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
app.include_router(reference.router)
app.include_router(timetable.router)
app.include_router(leaves.router)
app.include_router(substitutions.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
