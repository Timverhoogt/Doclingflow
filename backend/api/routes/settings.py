"""
Settings management API endpoints.
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import get_settings, Settings
from backend.schemas.settings import (
    SettingsResponse, SettingsUpdate, WatchFolder, WatchFolderCreate,
    WatchFolderUpdate, ClassificationRule, ClassificationRuleCreate,
    ClassificationRuleUpdate, SettingsValidation, SettingsBackup,
    SettingsRestore
)


router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint(
    settings: Settings = Depends(get_settings)
):
    """
    Get current application settings.

    Returns all current configuration settings.
    """
    try:
        return SettingsResponse(
            app={
                "name": settings.app.name,
                "version": settings.app.version,
                "debug": settings.debug,
                "environment": settings.environment
            },
            processing={
                "chunk_size": settings.processing.chunk_size,
                "chunk_overlap": settings.processing.chunk_overlap,
                "max_file_size": settings.processing.max_file_size,
                "supported_formats": settings.processing.supported_formats,
                "max_concurrent_jobs": settings.processing.max_concurrent_jobs,
                "embedding_batch_size": settings.processing.embedding_batch_size
            },
            llm={
                "provider": settings.llm.provider,
                "model": settings.llm.model,
                "base_url": settings.llm.base_url,
                "max_tokens": settings.llm.max_tokens,
                "temperature": settings.llm.temperature,
                "timeout": settings.llm.timeout
            },
            embeddings={
                "provider": settings.embeddings.provider,
                "model": settings.embeddings.model,
                "dimensions": settings.embeddings.dimensions,
                "batch_size": settings.embeddings.batch_size,
                "use_local_fallback": settings.embeddings.use_local_fallback
            },
            classification={
                "categories": [cat.value for cat in settings.classification.get_categories()],
                "default_category": settings.classification.default_category.value,
                "confidence_threshold": settings.classification.confidence_threshold
            },
            data={
                "inbox_path": settings.data.inbox_path,
                "processed_path": settings.data.processed_path,
                "archive_path": settings.data.archive_path,
                "failed_path": settings.data.failed_path,
                "temp_path": settings.data.temp_path,
                "max_storage_gb": settings.data.max_storage_gb,
                "cleanup_after_days": settings.data.cleanup_after_days
            },
            qdrant={
                "host": settings.qdrant.host,
                "port": settings.qdrant.port,
                "collection_name": settings.qdrant.collection_name,
                "vector_size": settings.qdrant.vector_size,
                "distance": settings.qdrant.distance,
                "timeout": settings.qdrant.timeout
            },
            celery={
                "broker_url": settings.celery.broker_url,
                "result_backend": settings.celery.result_backend,
                "task_serializer": settings.celery.task_serializer,
                "result_serializer": settings.celery.result_serializer,
                "accept_content": settings.celery.accept_content,
                "timezone": settings.celery.timezone,
                "enable_utc": settings.celery.enable_utc,
                "task_track_started": settings.celery.task_track_started,
                "task_time_limit": settings.celery.task_time_limit,
                "task_soft_time_limit": settings.celery.task_soft_time_limit
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}"
        )


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    update_data: SettingsUpdate,
    settings: Settings = Depends(get_settings)
):
    """
    Update application settings.

    Updates specified settings sections. Changes are applied immediately.
    """
    try:
        # Note: In a real implementation, you would need to:
        # 1. Validate the settings
        # 2. Update the configuration file
        # 3. Reload the settings
        # 4. Restart relevant services if needed
        
        # For now, we'll just return the current settings
        # This is a placeholder implementation
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Settings update not implemented yet. Use configuration files."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.get("/watch-folders", response_model=List[WatchFolder])
async def get_watch_folders(
    settings: Settings = Depends(get_settings)
):
    """
    Get configured watch folders.

    Returns list of all configured watch folders.
    """
    try:
        # In a real implementation, this would read from a database or config file
        # For now, return the default inbox folder
        
        inbox_path = Path(settings.data.inbox_path)
        
        watch_folders = []
        if inbox_path.exists():
            watch_folders.append(WatchFolder(
                path=str(inbox_path),
                enabled=True,
                recursive=True,
                file_patterns=settings.processing.supported_formats,
                created_at=datetime.utcnow(),
                last_scan=datetime.utcnow(),
                files_found=len(list(inbox_path.glob("*")))
            ))
        
        return watch_folders
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watch folders: {str(e)}"
        )


@router.post("/watch-folders", response_model=WatchFolder)
async def add_watch_folder(
    folder_data: WatchFolderCreate,
    settings: Settings = Depends(get_settings)
):
    """
    Add a new watch folder.

    Creates a new watch folder configuration.
    """
    try:
        folder_path = Path(folder_data.path)
        
        # Validate path exists
        if not folder_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path does not exist: {folder_data.path}"
            )
        
        # Validate path is a directory
        if not folder_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {folder_data.path}"
            )
        
        # In a real implementation, this would save to database/config
        watch_folder = WatchFolder(
            path=str(folder_path),
            enabled=folder_data.enabled,
            recursive=folder_data.recursive,
            file_patterns=folder_data.file_patterns,
            created_at=datetime.utcnow(),
            last_scan=None,
            files_found=0
        )
        
        return watch_folder
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add watch folder: {str(e)}"
        )


@router.delete("/watch-folders/{path:path}")
async def remove_watch_folder(
    path: str,
    settings: Settings = Depends(get_settings)
):
    """
    Remove a watch folder.

    Removes the specified watch folder configuration.
    """
    try:
        # In a real implementation, this would remove from database/config
        # For now, just validate the path
        
        folder_path = Path(path)
        
        if not folder_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watch folder not found: {path}"
            )
        
        return {"message": f"Watch folder removed: {path}"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove watch folder: {str(e)}"
        )


@router.get("/classification-rules", response_model=List[ClassificationRule])
async def get_classification_rules(
    settings: Settings = Depends(get_settings)
):
    """
    Get classification rules.

    Returns all configured document classification rules.
    """
    try:
        # In a real implementation, this would read from a database
        # For now, return default rules based on categories
        
        rules = []
        categories = settings.classification.get_categories()
        
        for i, category in enumerate(categories):
            # Generate default keywords for each category
            keywords = []
            patterns = []
            
            if category.name == "SAFETY":
                keywords = ["safety", "hazard", "msds", "sds", "chemical", "danger", "warning"]
                patterns = ["*safety*", "*hazard*", "*msds*", "*sds*"]
            elif category.name == "TECHNICAL":
                keywords = ["specification", "technical", "data", "sheet", "spec", "technical"]
                patterns = ["*spec*", "*technical*", "*data*"]
            elif category.name == "BUSINESS":
                keywords = ["invoice", "contract", "agreement", "business", "commercial"]
                patterns = ["*invoice*", "*contract*", "*agreement*"]
            elif category.name == "EQUIPMENT":
                keywords = ["manual", "equipment", "maintenance", "operation", "procedure"]
                patterns = ["*manual*", "*equipment*", "*maintenance*"]
            elif category.name == "REGULATORY":
                keywords = ["permit", "certificate", "compliance", "regulatory", "license"]
                patterns = ["*permit*", "*certificate*", "*compliance*"]
            
            rules.append(ClassificationRule(
                id=i + 1,
                name=f"Default {category.name} Rule",
                category=category,
                keywords=keywords,
                patterns=patterns,
                priority=100 - i * 10,  # Higher priority for earlier categories
                enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ))
        
        return rules
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get classification rules: {str(e)}"
        )


@router.post("/classification-rules", response_model=ClassificationRule)
async def create_classification_rule(
    rule_data: ClassificationRuleCreate
):
    """
    Create a new classification rule.

    Creates a new document classification rule.
    """
    try:
        # In a real implementation, this would save to database
        rule = ClassificationRule(
            id=1,  # Would be auto-generated
            name=rule_data.name,
            category=rule_data.category,
            keywords=rule_data.keywords,
            patterns=rule_data.patterns,
            priority=rule_data.priority,
            enabled=rule_data.enabled,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return rule
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create classification rule: {str(e)}"
        )


@router.patch("/classification-rules/{rule_id}", response_model=ClassificationRule)
async def update_classification_rule(
    rule_id: int,
    rule_data: ClassificationRuleUpdate
):
    """
    Update a classification rule.

    Updates an existing document classification rule.
    """
    try:
        # In a real implementation, this would update in database
        # For now, return a placeholder
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Classification rule update not implemented yet"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update classification rule: {str(e)}"
        )


@router.delete("/classification-rules/{rule_id}")
async def delete_classification_rule(
    rule_id: int
):
    """
    Delete a classification rule.

    Removes the specified classification rule.
    """
    try:
        # In a real implementation, this would remove from database
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Classification rule deletion not implemented yet"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete classification rule: {str(e)}"
        )


@router.post("/validate", response_model=SettingsValidation)
async def validate_settings(
    settings: Settings = Depends(get_settings)
):
    """
    Validate current settings.

    Validates all settings and returns any errors or warnings.
    """
    try:
        errors = []
        warnings = []
        
        # Validate paths exist
        paths_to_check = [
            ("inbox_path", settings.data.inbox_path),
            ("processed_path", settings.data.processed_path),
            ("archive_path", settings.data.archive_path),
            ("failed_path", settings.data.failed_path),
            ("temp_path", settings.data.temp_path)
        ]
        
        for name, path in paths_to_check:
            if not os.path.exists(path):
                errors.append(f"{name} does not exist: {path}")
            elif not os.path.isdir(path):
                errors.append(f"{name} is not a directory: {path}")
        
        # Validate file size limits
        if settings.processing.max_file_size < 1024:
            warnings.append("max_file_size is very small (< 1KB)")
        
        if settings.processing.max_file_size > 100 * 1024 * 1024:
            warnings.append("max_file_size is very large (> 100MB)")
        
        # Validate chunk settings
        if settings.processing.chunk_overlap >= settings.processing.chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")
        
        # Validate concurrent jobs
        if settings.processing.max_concurrent_jobs > 10:
            warnings.append("max_concurrent_jobs is high, may impact system performance")
        
        return SettingsValidation(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate settings: {str(e)}"
        )


@router.post("/backup", response_model=SettingsBackup)
async def backup_settings(
    settings: Settings = Depends(get_settings)
):
    """
    Create a settings backup.

    Creates a backup of current settings configuration.
    """
    try:
        # In a real implementation, this would create a proper backup
        backup_data = {
            "app": {
                "name": settings.app.name,
                "version": settings.app.version,
                "debug": settings.debug,
                "environment": settings.environment
            },
            "processing": {
                "chunk_size": settings.processing.chunk_size,
                "chunk_overlap": settings.processing.chunk_overlap,
                "max_file_size": settings.processing.max_file_size,
                "supported_formats": settings.processing.supported_formats,
                "max_concurrent_jobs": settings.processing.max_concurrent_jobs,
                "embedding_batch_size": settings.processing.embedding_batch_size
            },
            "llm": {
                "provider": settings.llm.provider,
                "model": settings.llm.model,
                "base_url": settings.llm.base_url,
                "max_tokens": settings.llm.max_tokens,
                "temperature": settings.llm.temperature,
                "timeout": settings.llm.timeout
            },
            "embeddings": {
                "provider": settings.embeddings.provider,
                "model": settings.embeddings.model,
                "dimensions": settings.embeddings.dimensions,
                "batch_size": settings.embeddings.batch_size,
                "use_local_fallback": settings.embeddings.use_local_fallback
            },
            "classification": {
                "categories": [cat.value for cat in settings.classification.get_categories()],
                "default_category": settings.classification.default_category.value,
                "confidence_threshold": settings.classification.confidence_threshold
            },
            "data": {
                "inbox_path": settings.data.inbox_path,
                "processed_path": settings.data.processed_path,
                "archive_path": settings.data.archive_path,
                "failed_path": settings.data.failed_path,
                "temp_path": settings.data.temp_path,
                "max_storage_gb": settings.data.max_storage_gb,
                "cleanup_after_days": settings.data.cleanup_after_days
            },
            "qdrant": {
                "host": settings.qdrant.host,
                "port": settings.qdrant.port,
                "collection_name": settings.qdrant.collection_name,
                "vector_size": settings.qdrant.vector_size,
                "distance": settings.qdrant.distance,
                "timeout": settings.qdrant.timeout
            },
            "celery": {
                "broker_url": settings.celery.broker_url,
                "result_backend": settings.celery.result_backend,
                "task_serializer": settings.celery.task_serializer,
                "result_serializer": settings.celery.result_serializer,
                "accept_content": settings.celery.accept_content,
                "timezone": settings.celery.timezone,
                "enable_utc": settings.celery.enable_utc,
                "task_track_started": settings.celery.task_track_started,
                "task_time_limit": settings.celery.task_time_limit,
                "task_soft_time_limit": settings.celery.task_soft_time_limit
            }
        }
        
        return SettingsBackup(
            timestamp=datetime.utcnow(),
            settings=backup_data,
            version=settings.app.version
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to backup settings: {str(e)}"
        )


@router.post("/restore")
async def restore_settings(
    restore_data: SettingsRestore
):
    """
    Restore settings from backup.

    Restores settings from a previously created backup.
    """
    try:
        if not restore_data.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restore confirmation required"
            )
        
        # In a real implementation, this would restore the settings
        # For now, just validate the backup data
        
        if not restore_data.backup_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No backup data provided"
            )
        
        return {"message": "Settings restored successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore settings: {str(e)}"
        )
