"""
Processing jobs API endpoints.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from backend.core.database import get_db
from backend.api.dependencies import get_pagination, Pagination
from backend.schemas.models import ProcessingJob, ProcessingJobStatus, Document
from backend.schemas.jobs import (
    ProcessingJobResponse, ProcessingJobListResponse, ProcessingJobStats,
    JobRetryRequest, JobCancelRequest, JobFilter, JobBulkOperation,
    JobQueueInfo, JobPerformanceMetrics, JobLogsResponse, JobLogEntry
)


router = APIRouter()


@router.get("", response_model=ProcessingJobListResponse)
async def list_processing_jobs(
    status: Optional[ProcessingJobStatus] = None,
    document_id: Optional[int] = None,
    task_name: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    pagination: Pagination = Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """
    List processing jobs with filtering and pagination.

    - **status**: Filter by job status
    - **document_id**: Filter by document ID
    - **task_name**: Filter by task name
    - **created_after/created_before**: Filter by creation date range
    - **page/page_size**: Pagination parameters
    """
    try:
        # Build query
        query = db.query(ProcessingJob)
        
        # Apply filters
        if status is not None:
            query = query.filter(ProcessingJob.status == status)
        
        if document_id is not None:
            query = query.filter(ProcessingJob.document_id == document_id)
        
        if task_name is not None:
            query = query.filter(ProcessingJob.task_name.ilike(f"%{task_name}%"))
        
        if created_after is not None:
            query = query.filter(ProcessingJob.created_at >= created_after)
        
        if created_before is not None:
            query = query.filter(ProcessingJob.created_at <= created_before)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        jobs = query.order_by(desc(ProcessingJob.created_at))\
            .offset(pagination.offset)\
            .limit(pagination.limit)\
            .all()
        
        # Convert to response format
        job_responses = []
        for job in jobs:
            # Get document info
            document = db.query(Document).filter(Document.id == job.document_id).first()
            
            processing_time = None
            if job.started_at and job.completed_at:
                processing_time = (job.completed_at - job.started_at).total_seconds()
            
            job_responses.append(ProcessingJobResponse(
                id=job.id,
                status=job.status,
                document_id=job.document_id,
                document_filename=document.filename if document else "Unknown",
                task_name=job.task_name,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                processing_time=processing_time,
                progress=job.progress,
                error_message=job.error_message,
                result=job.result,
                retry_count=job.retry_count,
                max_retries=job.max_retries
            ))
        
        return ProcessingJobListResponse(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            jobs=job_responses
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list processing jobs: {str(e)}"
        )


@router.get("/stats", response_model=ProcessingJobStats)
async def get_processing_job_stats(
    db: Session = Depends(get_db)
):
    """
    Get processing job statistics.

    Returns aggregated statistics about processing jobs.
    """
    try:
        # Total jobs
        total_jobs = db.query(func.count(ProcessingJob.id)).scalar()
        
        # Jobs by status
        pending_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.PENDING).scalar()
        
        active_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.PROGRESS).scalar()
        
        completed_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.SUCCESS).scalar()
        
        failed_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.FAILURE).scalar()
        
        # Average processing time
        avg_time = db.query(func.avg(
            func.extract('epoch', ProcessingJob.completed_at - ProcessingJob.started_at)
        )).filter(
            ProcessingJob.status == ProcessingJobStatus.SUCCESS,
            ProcessingJob.started_at.isnot(None),
            ProcessingJob.completed_at.isnot(None)
        ).scalar()
        
        # Success rate
        success_rate = 0.0
        if total_jobs > 0:
            success_rate = (completed_jobs / total_jobs) * 100
        
        # Jobs today
        today = datetime.utcnow().date()
        jobs_today = db.query(func.count(ProcessingJob.id))\
            .filter(func.date(ProcessingJob.created_at) == today).scalar()
        
        # Jobs this hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        jobs_this_hour = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.created_at >= hour_ago).scalar()
        
        return ProcessingJobStats(
            total_jobs=total_jobs,
            pending_jobs=pending_jobs,
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            avg_processing_time=float(avg_time) if avg_time else None,
            success_rate=success_rate,
            jobs_today=jobs_today,
            jobs_this_hour=jobs_this_hour
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job statistics: {str(e)}"
        )


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific processing job by ID.

    Returns detailed information about a processing job.
    """
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job with id {job_id} not found"
            )
        
        # Get document info
        document = db.query(Document).filter(Document.id == job.document_id).first()
        
        processing_time = None
        if job.started_at and job.completed_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
        
        return ProcessingJobResponse(
            id=job.id,
            status=job.status,
            document_id=job.document_id,
            document_filename=document.filename if document else "Unknown",
            task_name=job.task_name,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            processing_time=processing_time,
            progress=job.progress,
            error_message=job.error_message,
            result=job.result,
            retry_count=job.retry_count,
            max_retries=job.max_retries
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing job: {str(e)}"
        )


@router.post("/{job_id}/retry")
async def retry_processing_job(
    job_id: str,
    retry_request: JobRetryRequest,
    db: Session = Depends(get_db)
):
    """
    Retry a failed processing job.

    Retries a failed or cancelled processing job.
    """
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job with id {job_id} not found"
            )
        
        # Check if job can be retried
        if job.status not in [ProcessingJobStatus.FAILURE, ProcessingJobStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job with status {job.status} cannot be retried"
            )
        
        # Check retry limit
        if job.retry_count >= job.max_retries and not retry_request.force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job has exceeded maximum retry count ({job.max_retries})"
            )
        
        # Reset job status
        job.status = ProcessingJobStatus.PENDING
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        
        if retry_request.reset_progress:
            job.progress = None
        
        if not retry_request.force:
            job.retry_count += 1
        
        db.commit()
        
        # In a real implementation, you would queue the job for retry
        # For now, just return success
        
        return {"message": f"Job {job_id} queued for retry"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry processing job: {str(e)}"
        )


@router.post("/{job_id}/cancel")
async def cancel_processing_job(
    job_id: str,
    cancel_request: JobCancelRequest,
    db: Session = Depends(get_db)
):
    """
    Cancel a processing job.

    Cancels a pending or active processing job.
    """
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job with id {job_id} not found"
            )
        
        # Check if job can be cancelled
        if job.status not in [ProcessingJobStatus.PENDING, ProcessingJobStatus.PROGRESS]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job with status {job.status} cannot be cancelled"
            )
        
        # Update job status
        job.status = ProcessingJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.error_message = cancel_request.reason or "Job cancelled by user"
        
        db.commit()
        
        # In a real implementation, you would cancel the actual Celery task
        # For now, just return success
        
        return {"message": f"Job {job_id} cancelled"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel processing job: {str(e)}"
        )


@router.delete("/{job_id}")
async def delete_processing_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a processing job.

    Permanently deletes a processing job record.
    """
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job with id {job_id} not found"
            )
        
        # Only allow deletion of completed, failed, or cancelled jobs
        if job.status in [ProcessingJobStatus.PENDING, ProcessingJobStatus.PROGRESS]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete active or pending jobs"
            )
        
        db.delete(job)
        db.commit()
        
        return {"message": f"Job {job_id} deleted"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete processing job: {str(e)}"
        )


@router.post("/bulk")
async def bulk_job_operation(
    operation: JobBulkOperation,
    db: Session = Depends(get_db)
):
    """
    Perform bulk operations on processing jobs.

    Supports bulk retry, cancel, or delete operations.
    """
    try:
        if not operation.job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No job IDs provided"
            )
        
        # Get jobs
        jobs = db.query(ProcessingJob)\
            .filter(ProcessingJob.id.in_(operation.job_ids)).all()
        
        if len(jobs) != len(operation.job_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some job IDs not found"
            )
        
        updated_count = 0
        
        for job in jobs:
            if operation.operation == "retry":
                if job.status in [ProcessingJobStatus.FAILURE, ProcessingJobStatus.CANCELLED]:
                    job.status = ProcessingJobStatus.PENDING
                    job.started_at = None
                    job.completed_at = None
                    job.error_message = None
                    job.retry_count += 1
                    updated_count += 1
            
            elif operation.operation == "cancel":
                if job.status in [ProcessingJobStatus.PENDING, ProcessingJobStatus.PROGRESS]:
                    job.status = ProcessingJobStatus.CANCELLED
                    job.completed_at = datetime.utcnow()
                    job.error_message = operation.reason or "Bulk cancelled"
                    updated_count += 1
            
            elif operation.operation == "delete":
                if job.status in [ProcessingJobStatus.SUCCESS, ProcessingJobStatus.FAILURE, ProcessingJobStatus.CANCELLED]:
                    db.delete(job)
                    updated_count += 1
        
        db.commit()
        
        return {
            "message": f"Bulk {operation.operation} completed",
            "jobs_processed": len(jobs),
            "jobs_updated": updated_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk operation: {str(e)}"
        )


@router.get("/queue/info", response_model=List[JobQueueInfo])
async def get_queue_info(
    db: Session = Depends(get_db)
):
    """
    Get processing queue information.

    Returns information about processing queues and their status.
    """
    try:
        # In a real implementation, this would query Celery queues
        # For now, return basic queue info based on job status
        
        queue_info = []
        
        # Default queue
        pending_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.PENDING).scalar()
        
        active_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.PROGRESS).scalar()
        
        failed_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == ProcessingJobStatus.FAILURE).scalar()
        
        # Calculate average wait time
        avg_wait_time = db.query(func.avg(
            func.extract('epoch', ProcessingJob.started_at - ProcessingJob.created_at) / 60
        )).filter(
            ProcessingJob.started_at.isnot(None),
            ProcessingJob.status.in_([ProcessingJobStatus.SUCCESS, ProcessingJobStatus.PROGRESS])
        ).scalar()
        
        queue_info.append(JobQueueInfo(
            queue_name="default",
            active_jobs=active_jobs,
            pending_jobs=pending_jobs,
            failed_jobs=failed_jobs,
            avg_wait_time=float(avg_wait_time) if avg_wait_time else None,
            estimated_completion=None  # Would need more complex calculation
        ))
        
        return queue_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue info: {str(e)}"
        )


@router.get("/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(
    job_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get logs for a specific processing job.

    Returns paginated logs for a processing job.
    """
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job with id {job_id} not found"
            )
        
        # In a real implementation, this would query actual log storage
        # For now, return placeholder logs
        
        logs = []
        if job.error_message:
            logs.append(JobLogEntry(
                timestamp=job.completed_at or job.created_at,
                level="ERROR",
                message=job.error_message,
                metadata={"job_id": job_id}
            ))
        
        if job.result:
            logs.append(JobLogEntry(
                timestamp=job.completed_at or job.created_at,
                level="INFO",
                message="Job completed successfully",
                metadata={"job_id": job_id, "result": job.result}
            ))
        
        # Add creation log
        logs.append(JobLogEntry(
            timestamp=job.created_at,
            level="INFO",
            message=f"Job created: {job.task_name}",
            metadata={"job_id": job_id, "document_id": job.document_id}
        ))
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_logs = logs[offset:offset + page_size]
        
        return JobLogsResponse(
            job_id=job_id,
            logs=paginated_logs,
            total_logs=len(logs),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job logs: {str(e)}"
        )
