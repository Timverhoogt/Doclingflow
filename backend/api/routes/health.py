"""
Health check and system status endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.database import get_db
from backend.core.qdrant_client import get_qdrant_manager
from backend.core.config import get_settings


router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    Returns OK if the API is running.
    """
    return {
        "status": "ok",
        "service": "doclingflow-api"
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check including database and Qdrant status.
    """
    health_status = {
        "status": "ok",
        "services": {}
    }

    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = {
            "status": "ok",
            "type": "postgresql"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = {
            "status": "error",
            "error": str(e)
        }

    # Check Qdrant connection
    try:
        qdrant = get_qdrant_manager()
        collection_info = qdrant.get_collection_info()
        health_status["services"]["qdrant"] = {
            "status": "ok",
            "collection": collection_info.get("name"),
            "vectors_count": collection_info.get("vectors_count", 0)
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["qdrant"] = {
            "status": "error",
            "error": str(e)
        }

    return health_status


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness check for Kubernetes/container orchestration.
    Returns 200 if ready to accept traffic, 503 otherwise.
    """
    try:
        # Check database
        db.execute(text("SELECT 1"))

        # Check Qdrant
        qdrant = get_qdrant_manager()
        if not qdrant.collection_exists():
            raise HTTPException(
                status_code=503,
                detail="Qdrant collection not initialized"
            )

        return {"status": "ready"}

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes/container orchestration.
    Returns 200 if the application is alive.
    """
    return {"status": "alive"}


@router.get("/system/info")
async def system_info() -> Dict[str, Any]:
    """
    Get system information and configuration.
    """
    settings = get_settings()

    return {
        "app": {
            "name": settings.app.name,
            "version": settings.app.version,
            "debug": settings.debug
        },
        "processing": {
            "supported_formats": settings.processing.supported_formats,
            "chunk_size": settings.processing.chunk_size,
            "chunk_overlap": settings.processing.chunk_overlap,
            "max_concurrent_jobs": settings.processing.max_concurrent_jobs
        },
        "llm": {
            "provider": settings.llm.provider,
            "model": settings.llm.model
        },
        "embeddings": {
            "provider": settings.embeddings.provider,
            "model": settings.embeddings.model,
            "dimensions": settings.embeddings.dimensions
        },
        "classification": {
            "categories": [
                cat.name for cat in settings.classification.get_categories()
            ]
        }
    }
