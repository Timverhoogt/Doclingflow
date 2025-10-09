"""
Pydantic schemas for document API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from backend.schemas.models import DocumentCategory


# Base schemas
class DocumentBase(BaseModel):
    """Base document schema."""
    filename: str
    file_type: str
    category: Optional[DocumentCategory] = DocumentCategory.UNCATEGORIZED


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    original_path: str
    file_size: int
    file_hash: str


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""
    category: Optional[DocumentCategory] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None


class DocumentChunkBase(BaseModel):
    """Base document chunk schema."""
    chunk_index: int
    content: str
    page_number: Optional[int] = None


class DocumentChunkResponse(DocumentChunkBase):
    """Document chunk response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    content_hash: str
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    vector_id: Optional[str] = None
    created_at: datetime


class DocumentResponse(DocumentBase):
    """Document response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_path: str
    file_size: int
    file_hash: str

    # Processing metadata
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    processing_time: Optional[float] = None

    # Classification
    classification_confidence: Optional[float] = None

    # Content metadata
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    chunk_count: int = 0

    # Extracted entities
    entities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    # Storage
    storage_path: Optional[str] = None

    # Status
    is_active: bool = True
    is_archived: bool = False
    archived_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """Document list response with pagination."""
    total: int
    page: int
    page_size: int
    documents: List[DocumentResponse]


class DocumentStatsResponse(BaseModel):
    """Document statistics response."""
    total_documents: int
    by_category: Dict[str, int]
    by_file_type: Dict[str, int]
    total_size_bytes: int
    avg_processing_time: Optional[float] = None
    documents_processed_today: int
    documents_pending: int


class DocumentSearchRequest(BaseModel):
    """Document search request schema."""
    query: Optional[str] = None
    category: Optional[DocumentCategory] = None
    file_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    is_archived: Optional[bool] = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class DocumentUploadResponse(BaseModel):
    """Document upload response."""
    document_id: int
    filename: str
    file_size: int
    processing_job_id: Optional[int] = None
    message: str
