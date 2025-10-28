"""
File handler service for document validation and metadata extraction.

This service handles file validation, metadata extraction, and prepares
documents for processing by the Docling pipeline.
"""

import hashlib
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class FileHandler:
    """Service for handling file operations and metadata extraction."""
    
    def __init__(self):
        self.settings = get_settings()
        self.supported_extensions = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.rtf': 'application/rtf'
        }
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a file for processing.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check if it's a file (not directory)
            if not file_path.is_file():
                return False, "Path is not a file"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, "File is empty"
            
            max_size = self.settings.processing.max_file_size_mb * 1024 * 1024
            if file_size > max_size:
                return False, f"File too large ({file_size / 1024 / 1024:.1f}MB > {self.settings.processing.max_file_size_mb}MB)"
            
            # Check file extension
            extension = file_path.suffix.lower()
            if extension not in self.supported_extensions:
                return False, f"Unsupported file type: {extension}"
            
            # Check MIME type matches extension
            mime_type, _ = mimetypes.guess_type(str(file_path))
            expected_mime = self.supported_extensions.get(extension)
            
            if mime_type and expected_mime and mime_type != expected_mime:
                logger.warning(f"MIME type mismatch for {file_path}: {mime_type} != {expected_mime}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return False, f"Validation error: {str(e)}"
    
    def extract_metadata(self, file_path: Path) -> Dict:
        """
        Extract metadata from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file metadata
        """
        try:
            stat = file_path.stat()
            
            # Calculate file hash for deduplication
            file_hash = self._calculate_file_hash(file_path)
            
            metadata = {
                'original_filename': file_path.name,
                'file_path': str(file_path),
                'file_size': stat.st_size,
                'file_hash': file_hash,
                'file_extension': file_path.suffix.lower(),
                'mime_type': self.supported_extensions.get(file_path.suffix.lower()),
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'detected_at': datetime.utcnow(),
                'status': 'pending'
            }
            
            logger.info(f"Extracted metadata for {file_path}: {len(metadata)} fields")
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            raise
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            raise
    
    def move_to_archive(self, file_path: Path, processed_filename: Optional[str] = None) -> Path:
        """
        Move processed file to archive directory.
        
        Args:
            file_path: Original file path
            processed_filename: Optional new filename for archive
            
        Returns:
            Path to archived file
        """
        try:
            archive_path = Path(self.settings.data.archive_path)
            archive_path.mkdir(parents=True, exist_ok=True)
            
            if processed_filename:
                archived_file = archive_path / processed_filename
            else:
                # Add timestamp to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = file_path.stem, timestamp, file_path.suffix
                archived_file = archive_path / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            
            # Move file to archive
            file_path.rename(archived_file)
            logger.info(f"Moved file to archive: {file_path} -> {archived_file}")
            
            return archived_file
            
        except Exception as e:
            logger.error(f"Error moving file to archive {file_path}: {e}")
            raise
    
    def move_to_failed(self, file_path: Path, error_message: str) -> Path:
        """
        Move failed file to failed directory.
        
        Args:
            file_path: Original file path
            error_message: Error message for logging
            
        Returns:
            Path to failed file
        """
        try:
            failed_path = Path(self.settings.data.failed_path)
            failed_path.mkdir(parents=True, exist_ok=True)
            
            # Add timestamp and error info to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_hash = hashlib.md5(error_message.encode()).hexdigest()[:8]
            name_parts = file_path.stem, timestamp, error_hash, file_path.suffix
            failed_file = failed_path / f"{name_parts[0]}_{name_parts[1]}_{name_parts[2]}{name_parts[3]}"
            
            # Move file to failed directory
            file_path.rename(failed_file)
            logger.warning(f"Moved failed file: {file_path} -> {failed_file} (Error: {error_message})")
            
            return failed_file
            
        except Exception as e:
            logger.error(f"Error moving file to failed directory {file_path}: {e}")
            raise
    
    def cleanup_temp_files(self, temp_files: list[Path]):
        """
        Clean up temporary files created during processing.
        
        Args:
            temp_files: List of temporary file paths to clean up
        """
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file}: {e}")


def get_file_handler() -> FileHandler:
    """Get a FileHandler instance."""
    return FileHandler()
