"""
Pydantic schemas for settings API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from backend.schemas.models import DocumentCategory


class SettingsResponse(BaseModel):
    """Settings response schema."""
    app: Dict[str, Any]
    processing: Dict[str, Any]
    llm: Dict[str, Any]
    embeddings: Dict[str, Any]
    classification: Dict[str, Any]
    data: Dict[str, Any]
    qdrant: Dict[str, Any]
    celery: Dict[str, Any]


class SettingsUpdate(BaseModel):
    """Settings update schema."""
    processing: Optional[Dict[str, Any]] = None
    llm: Optional[Dict[str, Any]] = None
    embeddings: Optional[Dict[str, Any]] = None
    classification: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    qdrant: Optional[Dict[str, Any]] = None
    celery: Optional[Dict[str, Any]] = None


class WatchFolder(BaseModel):
    """Watch folder schema."""
    path: str
    enabled: bool = True
    recursive: bool = True
    file_patterns: List[str] = ["*.pdf", "*.docx", "*.xlsx", "*.pptx"]
    created_at: datetime
    last_scan: Optional[datetime] = None
    files_found: int = 0


class WatchFolderCreate(BaseModel):
    """Watch folder creation schema."""
    path: str
    enabled: bool = True
    recursive: bool = True
    file_patterns: List[str] = ["*.pdf", "*.docx", "*.xlsx", "*.pptx"]


class WatchFolderUpdate(BaseModel):
    """Watch folder update schema."""
    enabled: Optional[bool] = None
    recursive: Optional[bool] = None
    file_patterns: Optional[List[str]] = None


class ClassificationRule(BaseModel):
    """Classification rule schema."""
    id: int
    name: str
    category: DocumentCategory
    keywords: List[str]
    patterns: List[str]
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ClassificationRuleCreate(BaseModel):
    """Classification rule creation schema."""
    name: str
    category: DocumentCategory
    keywords: List[str] = []
    patterns: List[str] = []
    priority: int = 100
    enabled: bool = True


class ClassificationRuleUpdate(BaseModel):
    """Classification rule update schema."""
    name: Optional[str] = None
    category: Optional[DocumentCategory] = None
    keywords: Optional[List[str]] = None
    patterns: Optional[List[str]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class ProcessingSettings(BaseModel):
    """Processing settings schema."""
    chunk_size: int = Field(ge=100, le=2000)
    chunk_overlap: int = Field(ge=0, le=500)
    max_file_size: int = Field(ge=1024, le=100*1024*1024)  # 1KB to 100MB
    supported_formats: List[str]
    max_concurrent_jobs: int = Field(ge=1, le=10)
    embedding_batch_size: int = Field(ge=1, le=100)


class LLMSettings(BaseModel):
    """LLM settings schema."""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = Field(ge=100, le=4000)
    temperature: float = Field(ge=0.0, le=2.0)
    timeout: int = Field(ge=5, le=300)


class EmbeddingSettings(BaseModel):
    """Embedding settings schema."""
    provider: str
    model: str
    dimensions: int = Field(ge=100, le=4000)
    batch_size: int = Field(ge=1, le=100)
    use_local_fallback: bool = True


class DataSettings(BaseModel):
    """Data settings schema."""
    inbox_path: str
    processed_path: str
    archive_path: str
    failed_path: str
    temp_path: str
    max_storage_gb: int = Field(ge=1, le=1000)
    cleanup_after_days: int = Field(ge=1, le=365)


class QdrantSettings(BaseModel):
    """Qdrant settings schema."""
    host: str
    port: int = Field(ge=1, le=65535)
    collection_name: str
    vector_size: int = Field(ge=100, le=4000)
    distance: str = "Cosine"
    timeout: int = Field(ge=5, le=300)


class CelerySettings(BaseModel):
    """Celery settings schema."""
    broker_url: str
    result_backend: str
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = ["json"]
    timezone: str = "UTC"
    enable_utc: bool = True
    task_track_started: bool = True
    task_time_limit: int = Field(ge=60, le=3600)
    task_soft_time_limit: int = Field(ge=30, le=1800)


class SettingsValidation(BaseModel):
    """Settings validation response schema."""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class SettingsBackup(BaseModel):
    """Settings backup schema."""
    timestamp: datetime
    settings: Dict[str, Any]
    version: str


class SettingsRestore(BaseModel):
    """Settings restore schema."""
    backup_data: Dict[str, Any]
    confirm: bool = False
