"""
Pydantic schemas for processing jobs.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from backend.schemas.models import ProcessingStatus


class ProcessingJobBase(BaseModel):
    """Base processing job schema."""
    document_id: int


class ProcessingJobCreate(ProcessingJobBase):
    """Schema for creating a processing job."""
    celery_task_id: Optional[str] = None


class ProcessingJobUpdate(BaseModel):
    """Schema for updating a processing job."""
    status: Optional[ProcessingStatus] = None
    current_step: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


class ProcessingJobResponse(ProcessingJobBase):
    """Processing job response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    celery_task_id: Optional[str] = None
    status: ProcessingStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    progress_percentage: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    result_data: Optional[Dict[str, Any]] = None


class ProcessingJobListResponse(BaseModel):
    """Processing job list response with pagination."""
    total: int
    page: int
    page_size: int
    jobs: List[ProcessingJobResponse]


class ProcessingJobStatsResponse(BaseModel):
    """Processing job statistics."""
    total_jobs: int
    pending: int
    processing: int
    completed: int
    failed: int
    cancelled: int
    avg_processing_time: Optional[float] = None  # In seconds
    success_rate: float  # Percentage


class ProcessingQueueStatus(BaseModel):
    """Current processing queue status."""
    active_jobs: int
    pending_jobs: int
    failed_jobs_last_24h: int
    avg_wait_time: Optional[float] = None  # In seconds
    worker_status: Dict[str, Any] = Field(
        default_factory=dict,
        description="Status of Celery workers"
    )


class RetryJobRequest(BaseModel):
    """Request schema for retrying a failed job."""
    reset_retry_count: bool = Field(
        default=False,
        description="Reset retry counter to 0"
    )


class BatchProcessingRequest(BaseModel):
    """Request schema for batch processing."""
    document_ids: List[int] = Field(..., min_length=1)
    force_reprocess: bool = Field(
        default=False,
        description="Reprocess even if already processed"
    )


class BatchProcessingResponse(BaseModel):
    """Response schema for batch processing."""
    total_documents: int
    jobs_created: int
    jobs_failed: int
    job_ids: List[int]
    message: str
