"""
Main document processing Celery task.

This module contains the main processing task that orchestrates the complete
document processing pipeline: Docling → Classify → Extract → Chunk → Embed → Store.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from celery import current_task
from sqlalchemy.orm import Session

from backend.core.database import get_db_session
from backend.core.config import get_settings
from backend.services.docling_processor import get_docling_processor
from backend.services.classifier import get_document_classifier
from backend.services.entity_extractor import get_entity_extractor
from backend.services.chunker import get_semantic_chunker
from backend.services.embedder import get_embedding_service
from backend.services.vector_store import get_vector_store
from backend.services.file_handler import get_file_handler
from backend.schemas.models import Document, ProcessingJob
from backend.tasks import get_celery_app

logger = logging.getLogger(__name__)
celery_app = get_celery_app()


@celery_app.task(bind=True, name="backend.tasks.processing.process_document_pipeline")
def process_document_pipeline_task(self, document_id: int) -> Dict:
    """
    Process a document through the complete pipeline.
    
    Args:
        document_id: ID of the document to process
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting document processing pipeline for document {document_id}")
    
    try:
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={"status": "initializing", "document_id": document_id}
        )
        
        # Get document from database
        with get_db_session() as db:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found",
                    "document_id": document_id
                }
            
            # Update processing job
            job = db.query(ProcessingJob).filter(
                ProcessingJob.document_id == document_id,
                ProcessingJob.task_id == self.request.id
            ).first()
            
            if job:
                job.status = "processing"
                job.started_at = document.detected_at
                db.commit()
        
        file_path = Path(document.file_path)
        
        # Step 1: Process with Docling
        self.update_state(
            state="PROGRESS",
            meta={"status": "processing_with_docling", "document_id": document_id}
        )
        
        docling_processor = get_docling_processor()
        docling_result = docling_processor.process_document(file_path)
        
        logger.info(f"Docling processing completed for document {document_id}")
        
        # Step 2: Classify document
        self.update_state(
            state="PROGRESS",
            meta={"status": "classifying_document", "document_id": document_id}
        )
        
        classifier = get_document_classifier()
        classification_result = await classifier.classify_document(
            docling_result["text_content"],
            document.original_filename
        )
        
        logger.info(f"Document classified as: {classification_result['category']}")
        
        # Step 3: Extract entities
        self.update_state(
            state="PROGRESS",
            meta={"status": "extracting_entities", "document_id": document_id}
        )
        
        entity_extractor = get_entity_extractor()
        entity_result = await entity_extractor.extract_entities(
            docling_result["text_content"],
            document.original_filename
        )
        
        logger.info(f"Extracted {entity_result['total_entities']} entities")
        
        # Step 4: Create chunks
        self.update_state(
            state="PROGRESS",
            meta={"status": "creating_chunks", "document_id": document_id}
        )
        
        chunker = get_semantic_chunker()
        
        # Chunk main text content
        text_chunks = chunker.chunk_text(
            docling_result["text_content"],
            preserve_structure=True
        )
        
        # Chunk structured content (tables, images, etc.)
        structured_chunks = chunker.chunk_structured_content(docling_result)
        
        # Combine all chunks
        all_chunks = text_chunks + structured_chunks
        
        logger.info(f"Created {len(all_chunks)} chunks")
        
        # Step 5: Generate embeddings
        self.update_state(
            state="PROGRESS",
            meta={"status": "generating_embeddings", "document_id": document_id}
        )
        
        embedder = get_embedding_service()
        
        # Prepare chunks for embedding
        chunks_for_embedding = []
        for i, chunk in enumerate(all_chunks):
            chunk_data = {
                "chunk_id": f"{document_id}_{i}",
                "text": chunk["text"],
                "chunk_type": chunk.get("chunk_type", "content"),
                "section": chunk.get("section", "content"),
                "section_title": chunk.get("section_title", ""),
                "start": chunk.get("start", 0),
                "end": chunk.get("end", len(chunk["text"])),
                "document_id": document_id,
                "document_filename": document.original_filename,
                "document_category": classification_result["category"],
                "created_at": document.detected_at
            }
            chunks_for_embedding.append(chunk_data)
        
        # Generate embeddings
        embedded_chunks = await embedder.embed_chunks(chunks_for_embedding)
        
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
        
        # Step 6: Store in vector database
        self.update_state(
            state="PROGRESS",
            meta={"status": "storing_vectors", "document_id": document_id}
        )
        
        vector_store = get_vector_store()
        storage_result = vector_store.upsert_chunks(embedded_chunks)
        
        logger.info(f"Stored {storage_result['upserted']} chunks in vector store")
        
        # Step 7: Update database with results
        self.update_state(
            state="PROGRESS",
            meta={"status": "updating_database", "document_id": document_id}
        )
        
        with get_db_session() as db:
            # Update document
            document.status = "processed"
            document.category = classification_result["category"]
            document.confidence_score = classification_result["confidence"]
            document.processing_metadata = {
                "docling_result": {
                    "page_count": docling_result["metadata"]["page_count"],
                    "processing_method": docling_result["metadata"]["processing_method"]
                },
                "classification": classification_result,
                "entities": entity_result,
                "chunks": {
                    "total_chunks": len(all_chunks),
                    "text_chunks": len(text_chunks),
                    "structured_chunks": len(structured_chunks),
                    "embedded_chunks": len(embedded_chunks)
                },
                "vector_storage": storage_result
            }
            
            # Update processing job
            if job:
                job.status = "completed"
                job.completed_at = document.detected_at
                job.result_metadata = {
                    "chunks_processed": len(embedded_chunks),
                    "entities_extracted": entity_result["total_entities"],
                    "category": classification_result["category"],
                    "confidence": classification_result["confidence"]
                }
            
            db.commit()
        
        # Step 8: Move file to archive
        self.update_state(
            state="PROGRESS",
            meta={"status": "archiving_file", "document_id": document_id}
        )
        
        file_handler = get_file_handler()
        archived_path = file_handler.move_to_archive(file_path)
        
        # Update document with archived path
        with get_db_session() as db:
            document = db.query(Document).filter(Document.id == document_id).first()
            document.file_path = str(archived_path)
            db.commit()
        
        logger.info(f"Document processing completed successfully: {document_id}")
        
        return {
            "success": True,
            "document_id": document_id,
            "category": classification_result["category"],
            "confidence": classification_result["confidence"],
            "chunks_processed": len(embedded_chunks),
            "entities_extracted": entity_result["total_entities"],
            "archived_path": str(archived_path),
            "processing_time": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        
        # Update database with error
        try:
            with get_db_session() as db:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = "failed"
                    document.error_message = str(e)
                
                job = db.query(ProcessingJob).filter(
                    ProcessingJob.document_id == document_id,
                    ProcessingJob.task_id == self.request.id
                ).first()
                
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = document.detected_at if document else None
                
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update database with error: {db_error}")
        
        # Move file to failed directory
        try:
            file_handler = get_file_handler()
            failed_path = file_handler.move_to_failed(file_path, str(e))
        except Exception as move_error:
            logger.error(f"Failed to move file to failed directory: {move_error}")
            failed_path = file_path
        
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
            "failed_path": str(failed_path)
        }


@celery_app.task(name="backend.tasks.processing.reprocess_document")
def reprocess_document_task(document_id: int) -> Dict:
    """
    Reprocess a document (useful for failed documents or after configuration changes).
    
    Args:
        document_id: ID of the document to reprocess
        
    Returns:
        Dictionary with reprocessing results
    """
    logger.info(f"Reprocessing document {document_id}")
    
    try:
        # Delete existing chunks from vector store
        vector_store = get_vector_store()
        vector_store.delete_document_chunks(document_id)
        
        # Reset document status
        with get_db_session() as db:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            document.status = "pending"
            document.error_message = None
            document.processing_metadata = None
            db.commit()
        
        # Queue for processing
        processing_task = process_document_pipeline_task.delay(document_id)
        
        return {
            "success": True,
            "document_id": document_id,
            "processing_task_id": processing_task.id,
            "message": "Document queued for reprocessing"
        }
        
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id
        }


@celery_app.task(name="backend.tasks.processing.batch_process_documents")
def batch_process_documents_task(document_ids: List[int]) -> Dict:
    """
    Process multiple documents in batch.
    
    Args:
        document_ids: List of document IDs to process
        
    Returns:
        Dictionary with batch processing results
    """
    logger.info(f"Starting batch processing of {len(document_ids)} documents")
    
    results = []
    successful = 0
    failed = 0
    
    for document_id in document_ids:
        try:
            result = process_document_pipeline_task.delay(document_id)
            results.append({
                "document_id": document_id,
                "task_id": result.id,
                "status": "queued"
            })
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to queue document {document_id}: {e}")
            results.append({
                "document_id": document_id,
                "error": str(e),
                "status": "failed"
            })
            failed += 1
    
    logger.info(f"Batch processing queued: {successful} documents, {failed} failed")
    
    return {
        "total": len(document_ids),
        "successful": successful,
        "failed": failed,
        "results": results
    }


@celery_app.task(name="backend.tasks.processing.cleanup_failed_documents")
def cleanup_failed_documents_task() -> Dict:
    """
    Clean up failed documents and their associated data.
    
    Returns:
        Dictionary with cleanup results
    """
    logger.info("Starting cleanup of failed documents")
    
    try:
        with get_db_session() as db:
            # Find failed documents
            failed_documents = db.query(Document).filter(
                Document.status.in_(["failed", "error"])
            ).all()
            
            cleanup_count = 0
            
            for document in failed_documents:
                try:
                    # Delete chunks from vector store
                    vector_store = get_vector_store()
                    vector_store.delete_document_chunks(document.id)
                    
                    # Delete processing jobs
                    db.query(ProcessingJob).filter(
                        ProcessingJob.document_id == document.id
                    ).delete()
                    
                    # Delete document record
                    db.delete(document)
                    
                    cleanup_count += 1
                    
                except Exception as e:
                    logger.error(f"Error cleaning up document {document.id}: {e}")
            
            db.commit()
        
        logger.info(f"Cleaned up {cleanup_count} failed documents")
        
        return {
            "success": True,
            "cleaned_up": cleanup_count,
            "message": f"Cleaned up {cleanup_count} failed documents"
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {
            "success": False,
            "error": str(e)
        }
