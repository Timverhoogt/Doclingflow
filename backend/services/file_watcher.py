"""
File watcher service for monitoring document inbox folder.

This service uses watchdog to monitor the inbox directory for new files
and triggers document processing when files are added.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend.core.config import get_settings
from backend.tasks.ingestion import process_document_task

logger = logging.getLogger(__name__)


class DocumentFileHandler(FileSystemEventHandler):
    """Handler for file system events in the inbox directory."""
    
    def __init__(self):
        self.settings = get_settings()
        self.processed_files: Set[str] = set()
        self.supported_extensions = {
            '.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.md', '.rtf'
        }
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if file has supported extension
        if file_path.suffix.lower() not in self.supported_extensions:
            logger.info(f"Skipping unsupported file type: {file_path}")
            return
        
        # Avoid processing the same file multiple times
        file_key = str(file_path.absolute())
        if file_key in self.processed_files:
            return
        
        self.processed_files.add(file_key)
        
        # Wait a moment for file to be fully written
        time.sleep(1)
        
        # Check if file still exists and has content
        if not file_path.exists() or file_path.stat().st_size == 0:
            logger.warning(f"File {file_path} no longer exists or is empty")
            self.processed_files.discard(file_key)
            return
        
        logger.info(f"New document detected: {file_path}")
        
        # Queue the document for processing
        try:
            process_document_task.delay(str(file_path))
            logger.info(f"Queued document for processing: {file_path}")
        except Exception as e:
            logger.error(f"Failed to queue document {file_path}: {e}")
            self.processed_files.discard(file_key)
    
    def on_moved(self, event):
        """Handle file move events (like copy operations)."""
        if event.is_directory:
            return
            
        file_path = Path(event.dest_path)
        
        # Check if file has supported extension
        if file_path.suffix.lower() not in self.supported_extensions:
            return
        
        # Avoid processing the same file multiple times
        file_key = str(file_path.absolute())
        if file_key in self.processed_files:
            return
        
        self.processed_files.add(file_key)
        
        # Wait a moment for file to be fully written
        time.sleep(1)
        
        # Check if file still exists and has content
        if not file_path.exists() or file_path.stat().st_size == 0:
            logger.warning(f"File {file_path} no longer exists or is empty")
            self.processed_files.discard(file_key)
            return
        
        logger.info(f"Document moved to inbox: {file_path}")
        
        # Queue the document for processing
        try:
            process_document_task.delay(str(file_path))
            logger.info(f"Queued document for processing: {file_path}")
        except Exception as e:
            logger.error(f"Failed to queue document {file_path}: {e}")
            self.processed_files.discard(file_key)


class FileWatcher:
    """File watcher service for monitoring document inbox."""
    
    def __init__(self):
        self.settings = get_settings()
        self.observer: Optional[Observer] = None
        self.event_handler = DocumentFileHandler()
    
    def start(self):
        """Start monitoring the inbox directory."""
        inbox_path = Path(self.settings.data.inbox_path)
        
        # Create inbox directory if it doesn't exist
        inbox_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting file watcher for: {inbox_path}")
        
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(inbox_path),
            recursive=True
        )
        
        self.observer.start()
        logger.info("File watcher started successfully")
    
    def stop(self):
        """Stop monitoring the inbox directory."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")
    
    def is_running(self) -> bool:
        """Check if the file watcher is running."""
        return self.observer is not None and self.observer.is_alive()


def start_file_watcher():
    """Start the file watcher service."""
    watcher = FileWatcher()
    watcher.start()
    return watcher


if __name__ == "__main__":
    # For testing the file watcher standalone
    logging.basicConfig(level=logging.INFO)
    
    watcher = start_file_watcher()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("File watcher stopped")
