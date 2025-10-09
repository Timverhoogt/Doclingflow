"""
SQLAlchemy database models for Doclingflow.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    JSON, ForeignKey, Enum
)
from sqlalchemy.orm import relationship

from backend.core.database import Base


class ProcessingStatus(str, PyEnum):
    """Processing job status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentCategory(str, PyEnum):
    """Document classification categories."""
    SAFETY_DATA_SHEETS = "Safety Data Sheets"
    TECHNICAL_SPECIFICATIONS = "Technical Specifications"
    EQUIPMENT_MANUALS = "Equipment Manuals"
    BUSINESS_DOCUMENTS = "Business Documents"
    REGULATORY_COMPLIANCE = "Regulatory Compliance"
    OPERATIONAL_PROCEDURES = "Operational Procedures"
    UNCATEGORIZED = "Uncategorized"


class Document(Base):
    """Document metadata model."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # File information
    filename = Column(String(255), nullable=False, index=True)
    original_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA256 hash

    # Processing metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    processing_time = Column(Float, nullable=True)  # Processing time in seconds

    # Classification
    category = Column(Enum(DocumentCategory), default=DocumentCategory.UNCATEGORIZED, index=True)
    classification_confidence = Column(Float, nullable=True)

    # Content metadata
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)

    # Extracted entities (stored as JSON)
    entities = Column(JSON, nullable=True)
    # Structure: {
    #     "equipment_ids": ["T-101", "P-202"],
    #     "chemical_names": ["Benzene", "Toluene"],
    #     "dates": ["2024-01-15"],
    #     "locations": ["Tank Farm A"],
    #     "personnel": ["John Doe"],
    #     "measurements": ["500 psi", "150°C"]
    # }

    # Additional metadata
    metadata = Column(JSON, nullable=True)
    # Structure: {
    #     "author": "...",
    #     "title": "...",
    #     "subject": "...",
    #     "keywords": ["..."],
    #     "created_date": "...",
    #     "modified_date": "..."
    # }

    # Storage paths
    storage_path = Column(String(512), nullable=True)  # Path in processed folder

    # Status flags
    is_active = Column(Boolean, default=True, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    archived_at = Column(DateTime, nullable=True)

    # Relationships
    processing_jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', category='{self.category}')>"


class ProcessingJob(Base):
    """Processing job tracking model."""
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification
    celery_task_id = Column(String(255), nullable=True, unique=True, index=True)

    # Status
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Progress tracking
    current_step = Column(String(100), nullable=True)
    progress_percentage = Column(Integer, default=0)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Results
    result_data = Column(JSON, nullable=True)
    # Structure: {
    #     "chunks_created": 15,
    #     "entities_extracted": 42,
    #     "classification": "Safety Data Sheets",
    #     "confidence": 0.95
    # }

    # Relationships
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document = relationship("Document", back_populates="processing_jobs")

    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, status='{self.status}', document_id={self.document_id})>"


class DocumentChunk(Base):
    """Document chunk model for vector storage."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)

    # Chunk identification
    chunk_index = Column(Integer, nullable=False)  # Position in document

    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # Hash of content

    # Metadata
    word_count = Column(Integer, nullable=True)
    char_count = Column(Integer, nullable=True)

    # Page information (for PDFs)
    page_number = Column(Integer, nullable=True)

    # Vector storage reference
    vector_id = Column(String(255), nullable=True, unique=True, index=True)  # Qdrant point ID

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"


class WatchFolder(Base):
    """Watch folder configuration model."""
    __tablename__ = "watch_folders"

    id = Column(Integer, primary_key=True, index=True)

    # Path information
    path = Column(String(512), nullable=False, unique=True)

    # Settings
    is_active = Column(Boolean, default=True, index=True)
    auto_process = Column(Boolean, default=True)

    # Statistics
    documents_processed = Column(Integer, default=0)
    last_scan_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<WatchFolder(id={self.id}, path='{self.path}', is_active={self.is_active})>"


class SystemSettings(Base):
    """System settings model for storing runtime configuration."""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Setting key-value
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=False)

    # Metadata
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemSettings(key='{self.key}')>"
