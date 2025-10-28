"""
FastAPI application initialization for Doclingflow.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.database import init_database, close_database
from backend.core.qdrant_client import get_qdrant_manager, close_qdrant
from backend.api.routes import health, documents, search, analytics, settings, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app.name} v{settings.app.version}")

    # Initialize database
    print("Initializing database...")
    init_database()

    # Initialize Qdrant collection
    print("Initializing Qdrant...")
    qdrant = get_qdrant_manager()
    if not qdrant.collection_exists():
        qdrant.create_collection()

    print("Application startup complete!")

    yield

    # Shutdown
    print("Shutting down application...")
    close_database()
    close_qdrant()
    print("Application shutdown complete!")


# Create FastAPI application
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="Document processing and RAG pipeline for petrochemical documents",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
    app.include_router(search.router, prefix="/api/search", tags=["Search"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
    app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])

    return app


# Create application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint."""
    settings = get_settings()
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "status": "running",
        "docs": "/docs"
    }
