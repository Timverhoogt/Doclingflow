"""
Pydantic schemas for analytics API endpoints.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from backend.schemas.models import DocumentCategory


class AnalyticsOverview(BaseModel):
    """Analytics overview response schema."""
    total_documents: int
    total_size_bytes: int
    documents_processed_today: int
    documents_pending: int
    avg_processing_time: Optional[float] = None
    by_category: Dict[str, int]
    by_file_type: Dict[str, int]
    processing_success_rate: float
    last_updated: datetime


class TimelineDataPoint(BaseModel):
    """Timeline data point schema."""
    date: date
    documents_processed: int
    documents_uploaded: int
    total_size_bytes: int
    avg_processing_time: Optional[float] = None


class TimelineResponse(BaseModel):
    """Timeline analytics response schema."""
    period: str  # "day", "week", "month"
    start_date: date
    end_date: date
    data_points: List[TimelineDataPoint]
    total_documents: int
    total_size_bytes: int


class CategoryDistribution(BaseModel):
    """Category distribution schema."""
    category: DocumentCategory
    count: int
    percentage: float
    total_size_bytes: int
    avg_processing_time: Optional[float] = None


class CategoryAnalyticsResponse(BaseModel):
    """Category analytics response schema."""
    distributions: List[CategoryDistribution]
    uncategorized_count: int
    uncategorized_percentage: float
    total_documents: int


class ProcessingJobStats(BaseModel):
    """Processing job statistics schema."""
    job_id: str
    status: str
    document_id: int
    document_filename: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None


class QueueStatus(BaseModel):
    """Processing queue status schema."""
    active_jobs: int
    pending_jobs: int
    failed_jobs: int
    completed_today: int
    avg_wait_time_minutes: Optional[float] = None
    estimated_completion_time: Optional[datetime] = None
    recent_jobs: List[ProcessingJobStats]


class PerformanceMetrics(BaseModel):
    """Performance metrics schema."""
    avg_processing_time_seconds: float
    median_processing_time_seconds: float
    p95_processing_time_seconds: float
    throughput_documents_per_hour: float
    error_rate_percentage: float
    queue_efficiency_score: float


class AnalyticsFilters(BaseModel):
    """Analytics filters schema."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category: Optional[DocumentCategory] = None
    file_type: Optional[str] = None
    include_archived: bool = False


class DocumentTrends(BaseModel):
    """Document trends analysis schema."""
    upload_trend: str  # "increasing", "decreasing", "stable"
    processing_trend: str
    size_trend: str
    category_trends: Dict[str, str]
    peak_upload_hours: List[int]
    peak_upload_days: List[str]


class SystemHealthMetrics(BaseModel):
    """System health metrics schema."""
    database_status: str
    qdrant_status: str
    celery_status: str
    disk_usage_percentage: float
    memory_usage_percentage: float
    cpu_usage_percentage: float
    active_connections: int
    last_backup: Optional[datetime] = None
