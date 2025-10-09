"""
FastAPI dependency injection functions.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import get_settings, Settings
from backend.core.qdrant_client import get_qdrant_manager, QdrantManager
from backend.schemas.models import Document


def get_current_settings() -> Settings:
    """
    Dependency to get current application settings.

    Usage:
        @app.get("/endpoint")
        def endpoint(settings: Settings = Depends(get_current_settings)):
            ...
    """
    return get_settings()


def get_qdrant() -> QdrantManager:
    """
    Dependency to get Qdrant manager instance.

    Usage:
        @app.get("/endpoint")
        def endpoint(qdrant: QdrantManager = Depends(get_qdrant)):
            ...
    """
    return get_qdrant_manager()


def get_document_or_404(
    document_id: int,
    db: Session = Depends(get_db)
) -> Document:
    """
    Dependency to get a document by ID or raise 404.

    Usage:
        @app.get("/documents/{document_id}")
        def get_document(doc: Document = Depends(get_document_or_404)):
            ...
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    return document


def get_active_document_or_404(
    document_id: int,
    db: Session = Depends(get_db)
) -> Document:
    """
    Dependency to get an active (non-archived) document by ID or raise 404.

    Usage:
        @app.get("/documents/{document_id}")
        def get_document(doc: Document = Depends(get_active_document_or_404)):
            ...
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.is_active == True,
        Document.is_archived == False
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active document with id {document_id} not found"
        )
    return document


class Pagination:
    """Pagination parameters dependency."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20
    ):
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be >= 1"
            )
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100"
            )

        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """Calculate SQL offset from page number."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get SQL limit (same as page_size)."""
        return self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 20
) -> Pagination:
    """
    Dependency for pagination parameters.

    Usage:
        @app.get("/items")
        def get_items(
            pagination: Pagination = Depends(get_pagination),
            db: Session = Depends(get_db)
        ):
            items = db.query(Item).offset(pagination.offset).limit(pagination.limit).all()
            ...
    """
    return Pagination(page=page, page_size=page_size)
