"""
Docling document processor service.

This service handles document parsing using Docling for various file formats
including PDF, DOCX, XLSX, and PPTX files.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class DoclingProcessor:
    """Service for processing documents using Docling."""
    
    def __init__(self):
        self.settings = get_settings()
        self.converter = self._initialize_converter()
        
        # Supported formats
        self.supported_formats = {
            '.pdf': InputFormat.PDF,
            '.docx': InputFormat.DOCX,
            '.xlsx': InputFormat.XLSX,
            '.pptx': InputFormat.PPTX,
            '.txt': InputFormat.TXT,
            '.md': InputFormat.MD,
        }
    
    def _initialize_converter(self) -> DocumentConverter:
        """Initialize the Docling document converter."""
        try:
            # Configure PDF pipeline options
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = self.settings.processing.enable_ocr
            pdf_options.do_table_structure = self.settings.processing.extract_tables
            
            # Create converter with options
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pdf_options,
                }
            )
            
            logger.info("Docling converter initialized successfully")
            return converter
            
        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            raise
    
    def process_document(self, file_path: Path) -> Dict:
        """
        Process a document using Docling.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing processed document data
        """
        try:
            logger.info(f"Processing document with Docling: {file_path}")
            
            # Check if format is supported
            file_extension = file_path.suffix.lower()
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Convert document
            result = self.converter.convert(str(file_path))
            
            # Extract content
            document_data = self._extract_document_data(result, file_path)
            
            logger.info(f"Successfully processed document: {file_path}")
            return document_data
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise
    
    def _extract_document_data(self, result, file_path: Path) -> Dict:
        """Extract structured data from Docling result."""
        try:
            # Get the document
            document = result.document
            
            # Extract basic metadata
            metadata = {
                "title": document.name or file_path.stem,
                "page_count": len(document.pages) if hasattr(document, 'pages') else 1,
                "file_path": str(file_path),
                "processing_method": "docling"
            }
            
            # Extract text content
            text_content = self._extract_text_content(document)
            
            # Extract tables if available
            tables = self._extract_tables(document)
            
            # Extract images if available
            images = self._extract_images(document)
            
            # Extract structure (headings, sections)
            structure = self._extract_structure(document)
            
            return {
                "metadata": metadata,
                "text_content": text_content,
                "tables": tables,
                "images": images,
                "structure": structure,
                "raw_result": result  # Keep raw result for advanced processing
            }
            
        except Exception as e:
            logger.error(f"Error extracting document data: {e}")
            raise
    
    def _extract_text_content(self, document) -> str:
        """Extract text content from document."""
        try:
            # Get the main text content
            if hasattr(document, 'text'):
                return document.text
            elif hasattr(document, 'export_to_markdown'):
                return document.export_to_markdown()
            else:
                # Fallback: concatenate text from all elements
                text_parts = []
                for element in document.iterate_items():
                    if hasattr(element, 'text') and element.text:
                        text_parts.append(element.text)
                return "\n".join(text_parts)
                
        except Exception as e:
            logger.warning(f"Error extracting text content: {e}")
            return ""
    
    def _extract_tables(self, document) -> List[Dict]:
        """Extract tables from document."""
        try:
            tables = []
            
            for element in document.iterate_items():
                if hasattr(element, 'label') and element.label == 'table':
                    table_data = {
                        "caption": getattr(element, 'caption', ''),
                        "data": self._extract_table_data(element),
                        "position": getattr(element, 'bbox', None)
                    }
                    tables.append(table_data)
            
            logger.info(f"Extracted {len(tables)} tables from document")
            return tables
            
        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")
            return []
    
    def _extract_table_data(self, table_element) -> List[List[str]]:
        """Extract data from a table element."""
        try:
            if hasattr(table_element, 'export_to_dict'):
                return table_element.export_to_dict()
            elif hasattr(table_element, 'cells'):
                # Convert cells to 2D array
                rows = []
                for row in table_element.cells:
                    row_data = []
                    for cell in row:
                        row_data.append(str(cell) if cell else "")
                    rows.append(row_data)
                return rows
            else:
                return []
                
        except Exception as e:
            logger.warning(f"Error extracting table data: {e}")
            return []
    
    def _extract_images(self, document) -> List[Dict]:
        """Extract images from document."""
        try:
            images = []
            
            for element in document.iterate_items():
                if hasattr(element, 'label') and element.label == 'figure':
                    image_data = {
                        "caption": getattr(element, 'caption', ''),
                        "position": getattr(element, 'bbox', None),
                        "type": "figure"
                    }
                    images.append(image_data)
            
            logger.info(f"Extracted {len(images)} images from document")
            return images
            
        except Exception as e:
            logger.warning(f"Error extracting images: {e}")
            return []
    
    def _extract_structure(self, document) -> List[Dict]:
        """Extract document structure (headings, sections)."""
        try:
            structure = []
            
            for element in document.iterate_items():
                if hasattr(element, 'label') and element.label in ['heading', 'title']:
                    structure_item = {
                        "type": element.label,
                        "text": getattr(element, 'text', ''),
                        "level": getattr(element, 'level', 1),
                        "position": getattr(element, 'bbox', None)
                    }
                    structure.append(structure_item)
            
            logger.info(f"Extracted {len(structure)} structural elements")
            return structure
            
        except Exception as e:
            logger.warning(f"Error extracting structure: {e}")
            return []
    
    def extract_text_only(self, file_path: Path) -> str:
        """
        Extract only text content from a document (lightweight processing).
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        try:
            logger.info(f"Extracting text from: {file_path}")
            
            result = self.converter.convert(str(file_path))
            text_content = self._extract_text_content(result.document)
            
            logger.info(f"Extracted {len(text_content)} characters from {file_path}")
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise
    
    def get_document_info(self, file_path: Path) -> Dict:
        """
        Get basic document information without full processing.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document information
        """
        try:
            file_extension = file_path.suffix.lower()
            
            info = {
                "file_path": str(file_path),
                "file_extension": file_extension,
                "supported_format": file_extension in self.supported_formats,
                "estimated_pages": self._estimate_page_count(file_path),
                "file_size": file_path.stat().st_size
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting document info for {file_path}: {e}")
            raise
    
    def _estimate_page_count(self, file_path: Path) -> Optional[int]:
        """Estimate page count for a document."""
        try:
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.pdf':
                # Use PyPdfium for quick page count
                backend = PyPdfiumDocumentBackend()
                doc = backend.read(str(file_path))
                return len(doc.pages) if hasattr(doc, 'pages') else None
            elif file_extension in ['.docx', '.pptx']:
                # For Office documents, we'd need to open them
                # For now, return None (will be determined during full processing)
                return None
            else:
                return 1  # Text files are typically single page
                
        except Exception as e:
            logger.warning(f"Could not estimate page count for {file_path}: {e}")
            return None


def get_docling_processor() -> DoclingProcessor:
    """Get a DoclingProcessor instance."""
    return DoclingProcessor()
