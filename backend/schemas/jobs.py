"""
Pydantic schemas for processing jobs API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from backend.schemas.models import ProcessingJobStatus


class ProcessingJobResponse(BaseModel):
    """Processing job response schema."""
    id: str
    status: ProcessingJobStatus
    document_id: int
    document_filename: str
    task_name: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


class ProcessingJobListResponse(BaseModel):
    """Processing job list response schema."""
    total: int
    page: int
    page_size: int
    jobs: List[ProcessingJobResponse]


class ProcessingJobStats(BaseModel):
    """Processing job statistics schema."""
    total_jobs: int
    pending_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    avg_processing_time: Optional[float] = None
    success_rate: float
    jobs_today: int
    jobs_this_hour: int


class JobRetryRequest(BaseModel):
    """Job retry request schema."""
    force: bool = False
    reset_progress: bool = True


class JobCancelRequest(BaseModel):
    """Job cancel request schema."""
    reason: Optional[str] = None


class JobProgressUpdate(BaseModel):
    """Job progress update schema."""
    progress: float = Field(ge=0.0, le=100.0)
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class JobResult(BaseModel):
    """Job result schema."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    warnings: List[str] = []


class JobFilter(BaseModel):
    """Job filter schema."""
    status: Optional[ProcessingJobStatus] = None
    document_id: Optional[int] = None
    task_name: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    completed_after: Optional[datetime] = None
    completed_before: Optional[datetime] = None


class JobBulkOperation(BaseModel):
    """Job bulk operation schema."""
    job_ids: List[str]
    operation: str = Field(regex="^(retry|cancel|delete)$")
    reason: Optional[str] = None


class JobQueueInfo(BaseModel):
    """Job queue information schema."""
    queue_name: str
    active_jobs: int
    pending_jobs: int
    failed_jobs: int
    avg_wait_time: Optional[float] = None
    estimated_completion: Optional[datetime] = None


class JobPerformanceMetrics(BaseModel):
    """Job performance metrics schema."""
    period: str
    total_jobs: int
    avg_processing_time: float
    median_processing_time: float
    p95_processing_time: float
    success_rate: float
    throughput_per_hour: float
    error_rate: float
    retry_rate: float


class JobLogEntry(BaseModel):
    """Job log entry schema."""
    timestamp: datetime
    level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class JobLogsResponse(BaseModel):
    """Job logs response schema."""
    job_id: str
    logs: List[JobLogEntry]
    total_logs: int
    page: int
    page_size: int
