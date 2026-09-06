"""CodeLens backend — FastAPI entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import get_settings

app = FastAPI(
    title="CodeLens API",
    description="GitHub-based PR intelligence tool. Phase 1: GitHub Foundation.",
    version="0.1.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": "CodeLens API", "phase": "phase-1-github-foundation", "docs": "/docs"}
