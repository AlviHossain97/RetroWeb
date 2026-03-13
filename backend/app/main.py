"""
PiStation Stats API — Application entry point.

Creates the FastAPI application with Jinja2 templating, static file serving,
connection pooling, and all route registrations.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.config import get_settings
from app.db import close_pool
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    session_routes, stats_routes, dashboard_routes, health_routes,
    game_routes, system_routes, device_routes, achievement_routes,
    ai_routes,
)

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # Startup — nothing extra needed; pool is lazy-initialized
    yield
    # Shutdown — close the DB connection pool
    close_pool()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Jinja2 template engine
    templates = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    application.state.templates = templates

    # Static files
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Register routers
    application.include_router(health_routes.router)
    application.include_router(session_routes.router)
    application.include_router(stats_routes.router)
    application.include_router(dashboard_routes.router)
    application.include_router(game_routes.router)
    application.include_router(system_routes.router)
    application.include_router(device_routes.router)
    application.include_router(achievement_routes.router)
    application.include_router(ai_routes.router)

    return application


app = create_app()
