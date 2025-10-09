"""
Document management API endpoints.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.core.database import get_db
from backend.api.dependencies import (
    get_pagination, Pagination,
    get_document_or_404, get_active_document_or_404
)
from backend.schemas.models import Document, DocumentCategory, DocumentChunk
from backend.schemas.document import (
    DocumentResponse, DocumentListResponse,
    DocumentUpdate, DocumentStatsResponse,
    DocumentChunkResponse
)


router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    category: Optional[DocumentCategory] = None,
    file_type: Optional[str] = None,
    is_archived: Optional[bool] = False,
    search: Optional[str] = None,
    pagination: Pagination = Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """
    List documents with filtering and pagination.

    - **category**: Filter by document category
    - **file_type**: Filter by file type (pdf, docx, etc.)
    - **is_archived**: Show archived documents
    - **search**: Search in filename
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    query = db.query(Document)

    # Apply filters
    if category is not None:
        query = query.filter(Document.category == category)

    if file_type is not None:
        query = query.filter(Document.file_type == file_type.lower())

    if is_archived is not None:
        query = query.filter(Document.is_archived == is_archived)

    if search:
        query = query.filter(Document.filename.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    documents = query.order_by(desc(Document.uploaded_at))\
        .offset(pagination.offset)\
        .limit(pagination.limit)\
        .all()

    return DocumentListResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        documents=documents
    )


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_document_stats(db: Session = Depends(get_db)):
    """
    Get document statistics.

    Returns aggregated statistics about documents in the system.
    """
    # Total documents
    total_documents = db.query(func.count(Document.id))\
        .filter(Document.is_active == True)\
        .scalar()

    # Documents by category
    category_stats = db.query(
        Document.category,
        func.count(Document.id)
    ).filter(Document.is_active == True)\
        .group_by(Document.category)\
        .all()

    by_category = {str(cat): count for cat, count in category_stats}

    # Documents by file type
    file_type_stats = db.query(
        Document.file_type,
        func.count(Document.id)
    ).filter(Document.is_active == True)\
        .group_by(Document.file_type)\
        .all()

    by_file_type = {ftype: count for ftype, count in file_type_stats}

    # Total size
    total_size = db.query(func.sum(Document.file_size))\
        .filter(Document.is_active == True)\
        .scalar() or 0

    # Average processing time
    avg_time = db.query(func.avg(Document.processing_time))\
        .filter(
            Document.is_active == True,
            Document.processing_time.isnot(None)
        ).scalar()

    # Documents processed today
    today = datetime.utcnow().date()
    docs_today = db.query(func.count(Document.id))\
        .filter(
            Document.is_active == True,
            func.date(Document.processed_at) == today
        ).scalar()

    # Pending documents (uploaded but not processed)
    docs_pending = db.query(func.count(Document.id))\
        .filter(
            Document.is_active == True,
            Document.processed_at.is_(None)
        ).scalar()

    return DocumentStatsResponse(
        total_documents=total_documents,
        by_category=by_category,
        by_file_type=by_file_type,
        total_size_bytes=int(total_size),
        avg_processing_time=float(avg_time) if avg_time else None,
        documents_processed_today=docs_today,
        documents_pending=docs_pending
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document: Document = Depends(get_document_or_404)
):
    """
    Get a specific document by ID.

    Returns detailed information about a document.
    """
    return document


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    update_data: DocumentUpdate,
    document: Document = Depends(get_active_document_or_404),
    db: Session = Depends(get_db)
):
    """
    Update document metadata.

    - **category**: Update document category
    - **metadata**: Update custom metadata
    - **is_active**: Activate/deactivate document
    - **is_archived**: Archive/unarchive document
    """
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(document, field, value)

    # Set archived timestamp if archiving
    if update_data.is_archived and not document.is_archived:
        document.archived_at = datetime.utcnow()
    elif update_data.is_archived is False:
        document.archived_at = None

    db.commit()
    db.refresh(document)

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: Document = Depends(get_document_or_404),
    db: Session = Depends(get_db)
):
    """
    Delete a document.

    This will permanently delete the document and all associated data
    including chunks and processing jobs.
    """
    db.delete(document)
    db.commit()
    return None


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
async def get_document_chunks(
    document: Document = Depends(get_document_or_404),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get chunks for a specific document.

    Returns paginated list of document chunks in order.
    """
    offset = (page - 1) * page_size

    chunks = db.query(DocumentChunk)\
        .filter(DocumentChunk.document_id == document.id)\
        .order_by(DocumentChunk.chunk_index)\
        .offset(offset)\
        .limit(page_size)\
        .all()

    return chunks
