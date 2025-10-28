"""
Analytics and statistics API endpoints.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
import psutil
import os

from backend.core.database import get_db
from backend.core.qdrant_client import get_qdrant_manager, QdrantManager
from backend.core.config import get_settings
from backend.schemas.models import Document, DocumentCategory, ProcessingJob
from backend.schemas.analytics import (
    AnalyticsOverview, TimelineResponse, TimelineDataPoint,
    CategoryAnalyticsResponse, CategoryDistribution,
    QueueStatus, ProcessingJobStats, PerformanceMetrics,
    AnalyticsFilters, DocumentTrends, SystemHealthMetrics
)


router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    """
    Get analytics overview with key metrics.

    Returns aggregated statistics about documents, processing, and system performance.
    """
    try:
        # Build base query
        query = db.query(Document)
        
        # Apply filters
        if filters.start_date:
            query = query.filter(Document.uploaded_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(Document.uploaded_at <= filters.end_date)
        if filters.category:
            query = query.filter(Document.category == filters.category)
        if filters.file_type:
            query = query.filter(Document.file_type == filters.file_type)
        if not filters.include_archived:
            query = query.filter(Document.is_archived == False)
        
        # Total documents
        total_documents = query.filter(Document.is_active == True).count()
        
        # Total size
        total_size = query.filter(Document.is_active == True)\
            .with_entities(func.sum(Document.file_size)).scalar() or 0
        
        # Documents processed today
        today = datetime.utcnow().date()
        docs_today = query.filter(
            Document.is_active == True,
            func.date(Document.processed_at) == today
        ).count()
        
        # Pending documents
        docs_pending = query.filter(
            Document.is_active == True,
            Document.processed_at.is_(None)
        ).count()
        
        # Average processing time
        avg_time = query.filter(
            Document.is_active == True,
            Document.processing_time.isnot(None)
        ).with_entities(func.avg(Document.processing_time)).scalar()
        
        # Documents by category
        category_stats = query.filter(Document.is_active == True)\
            .with_entities(Document.category, func.count(Document.id))\
            .group_by(Document.category).all()
        
        by_category = {str(cat): count for cat, count in category_stats}
        
        # Documents by file type
        file_type_stats = query.filter(Document.is_active == True)\
            .with_entities(Document.file_type, func.count(Document.id))\
            .group_by(Document.file_type).all()
        
        by_file_type = {ftype: count for ftype, count in file_type_stats}
        
        # Processing success rate
        total_processed = query.filter(
            Document.is_active == True,
            Document.processed_at.isnot(None)
        ).count()
        
        failed_processed = query.filter(
            Document.is_active == True,
            Document.processing_time.isnot(None),
            Document.processing_time < 0  # Negative time indicates failure
        ).count()
        
        success_rate = 0.0
        if total_processed > 0:
            success_rate = ((total_processed - failed_processed) / total_processed) * 100
        
        return AnalyticsOverview(
            total_documents=total_documents,
            total_size_bytes=int(total_size),
            documents_processed_today=docs_today,
            documents_pending=docs_pending,
            avg_processing_time=float(avg_time) if avg_time else None,
            by_category=by_category,
            by_file_type=by_file_type,
            processing_success_rate=success_rate,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics overview: {str(e)}"
        )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline_analytics(
    period: str = Query(default="week", regex="^(day|week|month)$"),
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get timeline analytics for document processing.

    - **period**: Aggregation period (day, week, month)
    - **days**: Number of days to analyze (1-365)
    """
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Build date range
        date_range = []
        current_date = start_date
        
        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # Get data for each date
        data_points = []
        total_documents = 0
        total_size = 0
        
        for date_val in date_range:
            # Documents processed on this date
            processed_count = db.query(func.count(Document.id))\
                .filter(
                    Document.is_active == True,
                    func.date(Document.processed_at) == date_val
                ).scalar()
            
            # Documents uploaded on this date
            uploaded_count = db.query(func.count(Document.id))\
                .filter(
                    Document.is_active == True,
                    func.date(Document.uploaded_at) == date_val
                ).scalar()
            
            # Total size uploaded on this date
            size_bytes = db.query(func.sum(Document.file_size))\
                .filter(
                    Document.is_active == True,
                    func.date(Document.uploaded_at) == date_val
                ).scalar() or 0
            
            # Average processing time for this date
            avg_time = db.query(func.avg(Document.processing_time))\
                .filter(
                    Document.is_active == True,
                    func.date(Document.processed_at) == date_val,
                    Document.processing_time.isnot(None),
                    Document.processing_time > 0
                ).scalar()
            
            data_points.append(TimelineDataPoint(
                date=date_val,
                documents_processed=processed_count,
                documents_uploaded=uploaded_count,
                total_size_bytes=int(size_bytes),
                avg_processing_time=float(avg_time) if avg_time else None
            ))
            
            total_documents += uploaded_count
            total_size += int(size_bytes)
        
        return TimelineResponse(
            period=period,
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            total_documents=total_documents,
            total_size_bytes=total_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline analytics: {str(e)}"
        )


@router.get("/categories", response_model=CategoryAnalyticsResponse)
async def get_category_analytics(
    db: Session = Depends(get_db)
):
    """
    Get category distribution analytics.

    Returns detailed statistics about document categories.
    """
    try:
        # Get category statistics
        category_stats = db.query(
            Document.category,
            func.count(Document.id),
            func.sum(Document.file_size),
            func.avg(Document.processing_time)
        ).filter(Document.is_active == True)\
            .group_by(Document.category).all()
        
        # Calculate total for percentages
        total_documents = sum(count for _, count, _, _ in category_stats)
        
        distributions = []
        for category, count, total_size, avg_time in category_stats:
            percentage = (count / total_documents * 100) if total_documents > 0 else 0
            
            distributions.append(CategoryDistribution(
                category=category,
                count=count,
                percentage=percentage,
                total_size_bytes=int(total_size or 0),
                avg_processing_time=float(avg_time) if avg_time else None
            ))
        
        # Sort by count descending
        distributions.sort(key=lambda x: x.count, reverse=True)
        
        # Get uncategorized count
        uncategorized_count = db.query(func.count(Document.id))\
            .filter(
                Document.is_active == True,
                Document.category == DocumentCategory.UNCATEGORIZED
            ).scalar()
        
        uncategorized_percentage = (uncategorized_count / total_documents * 100) if total_documents > 0 else 0
        
        return CategoryAnalyticsResponse(
            distributions=distributions,
            uncategorized_count=uncategorized_count,
            uncategorized_percentage=uncategorized_percentage,
            total_documents=total_documents
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get category analytics: {str(e)}"
        )


@router.get("/queue", response_model=QueueStatus)
async def get_queue_status(
    db: Session = Depends(get_db)
):
    """
    Get processing queue status and recent jobs.

    Returns current queue statistics and recent processing jobs.
    """
    try:
        # Get job counts by status
        active_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == "PROGRESS").scalar()
        
        pending_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == "PENDING").scalar()
        
        failed_jobs = db.query(func.count(ProcessingJob.id))\
            .filter(ProcessingJob.status == "FAILURE").scalar()
        
        # Jobs completed today
        today = datetime.utcnow().date()
        completed_today = db.query(func.count(ProcessingJob.id))\
            .filter(
                ProcessingJob.status == "SUCCESS",
                func.date(ProcessingJob.completed_at) == today
            ).scalar()
        
        # Average wait time (time from created to started)
        avg_wait_time = db.query(func.avg(
            func.extract('epoch', ProcessingJob.started_at - ProcessingJob.created_at) / 60
        )).filter(
            ProcessingJob.started_at.isnot(None),
            ProcessingJob.status.in_(["SUCCESS", "PROGRESS"])
        ).scalar()
        
        # Get recent jobs
        recent_jobs = db.query(ProcessingJob)\
            .order_by(desc(ProcessingJob.created_at))\
            .limit(10).all()
        
        recent_jobs_data = []
        for job in recent_jobs:
            # Get document info
            document = db.query(Document).filter(Document.id == job.document_id).first()
            
            processing_time = None
            if job.started_at and job.completed_at:
                processing_time = (job.completed_at - job.started_at).total_seconds()
            
            recent_jobs_data.append(ProcessingJobStats(
                job_id=job.id,
                status=job.status,
                document_id=job.document_id,
                document_filename=document.filename if document else "Unknown",
                started_at=job.started_at or job.created_at,
                completed_at=job.completed_at,
                processing_time=processing_time,
                error_message=job.error_message
            ))
        
        # Estimate completion time for pending jobs
        estimated_completion = None
        if pending_jobs > 0 and avg_wait_time:
            estimated_completion = datetime.utcnow() + timedelta(minutes=avg_wait_time * pending_jobs)
        
        return QueueStatus(
            active_jobs=active_jobs,
            pending_jobs=pending_jobs,
            failed_jobs=failed_jobs,
            completed_today=completed_today,
            avg_wait_time_minutes=float(avg_wait_time) if avg_wait_time else None,
            estimated_completion_time=estimated_completion,
            recent_jobs=recent_jobs_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get system performance metrics.

    - **days**: Number of days to analyze (1-30)
    """
    try:
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get processing time statistics
        processing_times = db.query(Document.processing_time)\
            .filter(
                Document.is_active == True,
                Document.processed_at >= start_date,
                Document.processing_time.isnot(None),
                Document.processing_time > 0
            ).all()
        
        if not processing_times:
            return PerformanceMetrics(
                avg_processing_time_seconds=0.0,
                median_processing_time_seconds=0.0,
                p95_processing_time_seconds=0.0,
                throughput_documents_per_hour=0.0,
                error_rate_percentage=0.0,
                queue_efficiency_score=0.0
            )
        
        times = [pt[0] for pt in processing_times]
        times.sort()
        
        # Calculate metrics
        avg_time = sum(times) / len(times)
        median_time = times[len(times) // 2]
        p95_time = times[int(len(times) * 0.95)]
        
        # Throughput (documents per hour)
        total_docs = len(times)
        hours = days * 24
        throughput = total_docs / hours if hours > 0 else 0
        
        # Error rate
        total_processed = db.query(func.count(Document.id))\
            .filter(
                Document.is_active == True,
                Document.processed_at >= start_date
            ).scalar()
        
        error_rate = 0.0
        if total_processed > 0:
            failed_count = total_processed - len(times)
            error_rate = (failed_count / total_processed) * 100
        
        # Queue efficiency (based on wait times)
        avg_wait_time = db.query(func.avg(
            func.extract('epoch', ProcessingJob.started_at - ProcessingJob.created_at)
        )).filter(
            ProcessingJob.started_at.isnot(None),
            ProcessingJob.created_at >= start_date
        ).scalar()
        
        efficiency_score = 100.0
        if avg_wait_time:
            # Efficiency decreases with longer wait times
            efficiency_score = max(0, 100 - (avg_wait_time / 60))  # Convert to minutes
        
        return PerformanceMetrics(
            avg_processing_time_seconds=avg_time,
            median_processing_time_seconds=median_time,
            p95_processing_time_seconds=p95_time,
            throughput_documents_per_hour=throughput,
            error_rate_percentage=error_rate,
            queue_efficiency_score=efficiency_score
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/health", response_model=SystemHealthMetrics)
async def get_system_health(
    qdrant: QdrantManager = Depends(get_qdrant_manager),
    db: Session = Depends(get_db)
):
    """
    Get system health metrics.

    Returns status of all system components and resource usage.
    """
    try:
        # Database status
        db_status = "ok"
        try:
            db.execute("SELECT 1")
        except Exception:
            db_status = "error"
        
        # Qdrant status
        qdrant_status = "ok"
        try:
            qdrant.get_collection_info()
        except Exception:
            qdrant_status = "error"
        
        # Celery status (simplified check)
        celery_status = "ok"  # In a real implementation, check Celery worker status
        
        # System resource usage
        disk_usage = psutil.disk_usage('/').percent
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Active database connections
        active_connections = db.execute("SELECT count(*) FROM pg_stat_activity").scalar()
        
        # Last backup (placeholder - would need backup system integration)
        last_backup = None
        
        return SystemHealthMetrics(
            database_status=db_status,
            qdrant_status=qdrant_status,
            celery_status=celery_status,
            disk_usage_percentage=disk_usage,
            memory_usage_percentage=memory_usage,
            cpu_usage_percentage=cpu_usage,
            active_connections=active_connections,
            last_backup=last_backup
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )
