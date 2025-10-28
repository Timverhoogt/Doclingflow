"""
Document ingestion Celery tasks.

This module contains Celery tasks for handling document ingestion,
including file validation, metadata extraction, and queuing for processing.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from celery import current_task
from sqlalchemy.orm import Session

from backend.core.database import get_db_session
from backend.core.config import get_settings
from backend.services.file_handler import get_file_handler
from backend.schemas.models import Document, ProcessingJob
from backend.tasks import get_celery_app

logger = logging.getLogger(__name__)
celery_app = get_celery_app()


@celery_app.task(bind=True, name="backend.tasks.ingestion.process_document")
def process_document_task(self, file_path: str) -> Dict:
    """
    Process a document file for ingestion.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Dictionary with processing results
    """
    file_path_obj = Path(file_path)
    file_handler = get_file_handler()
    
    logger.info(f"Starting document ingestion: {file_path}")
    
    try:
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={"status": "validating", "file": str(file_path)}
        )
        
        # Validate file
        is_valid, error_message = file_handler.validate_file(file_path_obj)
        if not is_valid:
            logger.error(f"File validation failed for {file_path}: {error_message}")
            
            # Move to failed directory
            failed_path = file_handler.move_to_failed(file_path_obj, error_message)
            
            return {
                "success": False,
                "error": f"Validation failed: {error_message}",
                "file_path": str(failed_path),
                "status": "failed"
            }
        
        # Extract metadata
        self.update_state(
            state="PROGRESS",
            meta={"status": "extracting_metadata", "file": str(file_path)}
        )
        
        metadata = file_handler.extract_metadata(file_path_obj)
        
        # Check for duplicate files
        with get_db_session() as db:
            existing_doc = db.query(Document).filter(
                Document.file_hash == metadata["file_hash"]
            ).first()
            
            if existing_doc:
                logger.info(f"Duplicate file detected: {file_path} (hash: {metadata['file_hash'][:8]}...)")
                
                # Move to archive with duplicate marker
                archived_path = file_handler.move_to_archive(
                    file_path_obj, 
                    f"duplicate_{metadata['original_filename']}"
                )
                
                return {
                    "success": True,
                    "status": "duplicate",
                    "file_path": str(archived_path),
                    "existing_document_id": existing_doc.id,
                    "message": "File already processed"
                }
        
        # Create document record
        self.update_state(
            state="PROGRESS",
            meta={"status": "creating_record", "file": str(file_path)}
        )
        
        with get_db_session() as db:
            document = Document(
                original_filename=metadata["original_filename"],
                file_path=str(file_path_obj),
                file_size=metadata["file_size"],
                file_hash=metadata["file_hash"],
                file_extension=metadata["file_extension"],
                mime_type=metadata["mime_type"],
                status="pending",
                created_at=metadata["created_at"],
                modified_at=metadata["modified_at"],
                detected_at=metadata["detected_at"]
            )
            
            db.add(document)
            db.flush()  # Get the ID
            
            # Create processing job
            processing_job = ProcessingJob(
                document_id=document.id,
                status="pending",
                task_id=self.request.id,
                created_at=metadata["detected_at"]
            )
            
            db.add(processing_job)
            db.commit()
            
            logger.info(f"Created document record: ID {document.id}")
        
        # Queue for full processing
        self.update_state(
            state="PROGRESS",
            meta={"status": "queuing_processing", "file": str(file_path)}
        )
        
        # Import here to avoid circular imports
        from backend.tasks.processing import process_document_pipeline_task
        
        processing_task = process_document_pipeline_task.delay(document.id)
        
        logger.info(f"Queued document {document.id} for processing: {processing_task.id}")
        
        return {
            "success": True,
            "status": "queued",
            "document_id": document.id,
            "processing_task_id": processing_task.id,
            "file_path": str(file_path_obj)
        }
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        
        # Move to failed directory
        try:
            failed_path = file_handler.move_to_failed(file_path_obj, str(e))
        except Exception as move_error:
            logger.error(f"Failed to move file to failed directory: {move_error}")
            failed_path = file_path_obj
        
        # Update any existing processing job
        try:
            with get_db_session() as db:
                job = db.query(ProcessingJob).filter(
                    ProcessingJob.task_id == self.request.id
                ).first()
                
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = metadata.get("detected_at")
                    db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update processing job: {db_error}")
        
        return {
            "success": False,
            "error": str(e),
            "file_path": str(failed_path),
            "status": "failed"
        }


@celery_app.task(name="backend.tasks.ingestion.batch_process_documents")
def batch_process_documents_task(file_paths: list[str]) -> Dict:
    """
    Process multiple documents in batch.
    
    Args:
        file_paths: List of file paths to process
        
    Returns:
        Dictionary with batch processing results
    """
    logger.info(f"Starting batch processing of {len(file_paths)} documents")
    
    results = []
    successful = 0
    failed = 0
    duplicates = 0
    
    for file_path in file_paths:
        try:
            result = process_document_task.delay(file_path)
            results.append({
                "file_path": file_path,
                "task_id": result.id,
                "status": "queued"
            })
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to queue document {file_path}: {e}")
            results.append({
                "file_path": file_path,
                "error": str(e),
                "status": "failed"
            })
            failed += 1
    
    logger.info(f"Batch processing completed: {successful} queued, {failed} failed")
    
    return {
        "total": len(file_paths),
        "successful": successful,
        "failed": failed,
        "duplicates": duplicates,
        "results": results
    }


@celery_app.task(name="backend.tasks.ingestion.retry_failed_document")
def retry_failed_document_task(document_id: int) -> Dict:
    """
    Retry processing a failed document.
    
    Args:
        document_id: ID of the document to retry
        
    Returns:
        Dictionary with retry results
    """
    logger.info(f"Retrying failed document: {document_id}")
    
    try:
        with get_db_session() as db:
            document = db.query(Document).filter(Document.id == document_id).first()
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            if document.status not in ["failed", "error"]:
                return {
                    "success": False,
                    "error": f"Document {document_id} is not in failed state (status: {document.status})"
                }
            
            # Reset document status
            document.status = "pending"
            
            # Create new processing job
            processing_job = ProcessingJob(
                document_id=document.id,
                status="pending",
                created_at=document.detected_at
            )
            
            db.add(processing_job)
            db.commit()
            
            # Queue for processing
            from backend.tasks.processing import process_document_pipeline_task
            
            processing_task = process_document_pipeline_task.delay(document.id)
            
            logger.info(f"Retried document {document_id}: {processing_task.id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "processing_task_id": processing_task.id
            }
            
    except Exception as e:
        logger.error(f"Error retrying document {document_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
