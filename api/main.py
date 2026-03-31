"""FastAPI application entry point."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import leads, stats, pipeline, kanban, map as map_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="New Business Locator API",
    description="API for managing POS sales leads",
    version="1.0.0",
)

# CORS — configurable via ALLOWED_ORIGINS env var (comma-separated)
_default_origins = "http://localhost:3000,http://localhost:3001,http://localhost:3002"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)
app.include_router(stats.router)
app.include_router(pipeline.router)
app.include_router(kanban.router)
app.include_router(map_router.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
