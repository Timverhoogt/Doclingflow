"""
Semantic chunking service for document text.

This service splits document text into semantically meaningful chunks
with configurable size and overlap for optimal vector search performance.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Service for creating semantic chunks from document text."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Chunking configuration
        self.default_chunk_size = self.settings.processing.chunk_size
        self.default_overlap = self.settings.processing.chunk_overlap
        self.min_chunk_size = 100  # Minimum chunk size
        self.max_chunk_size = 2000  # Maximum chunk size
        
        # Sentence boundary patterns
        self.sentence_endings = [
            r'\.\s+',  # Period followed by space
            r'!\s+',   # Exclamation followed by space
            r'\?\s+',  # Question mark followed by space
            r';\s+',   # Semicolon followed by space
            r':\s+',   # Colon followed by space
        ]
        
        # Paragraph boundary patterns
        self.paragraph_endings = [
            r'\n\s*\n',  # Double newline
            r'\n\s*[A-Z][a-z]+.*\n',  # Newline followed by capitalized text
        ]
        
        # Petrochemical-specific section markers
        self.section_markers = [
            r'\n\s*(?:SECTION|Section)\s+\d+',
            r'\n\s*(?:CHAPTER|Chapter)\s+\d+',
            r'\n\s*(?:APPENDIX|Appendix)\s+[A-Z]',
            r'\n\s*(?:TABLE|Table)\s+\d+',
            r'\n\s*(?:FIGURE|Figure)\s+\d+',
            r'\n\s*(?:PROCEDURE|Procedure)\s+\d+',
            r'\n\s*(?:STEP|Step)\s+\d+',
        ]
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: Optional[int] = None, 
        overlap: Optional[int] = None,
        preserve_structure: bool = True
    ) -> List[Dict]:
        """
        Split text into semantic chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
            preserve_structure: Whether to preserve document structure
            
        Returns:
            List of chunk dictionaries with metadata
        """
        try:
            if not text or not text.strip():
                return []
            
            chunk_size = chunk_size or self.default_chunk_size
            overlap = overlap or self.default_overlap
            
            logger.info(f"Chunking text: {len(text)} characters, target size: {chunk_size}, overlap: {overlap}")
            
            if preserve_structure:
                chunks = self._chunk_with_structure(text, chunk_size, overlap)
            else:
                chunks = self._chunk_simple(text, chunk_size, overlap)
            
            # Add metadata to chunks
            for i, chunk in enumerate(chunks):
                chunk["chunk_id"] = i
                chunk["chunk_size"] = len(chunk["text"])
                chunk["word_count"] = len(chunk["text"].split())
                chunk["sentence_count"] = self._count_sentences(chunk["text"])
            
            logger.info(f"Created {len(chunks)} chunks from text")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            return []
    
    def _chunk_with_structure(self, text: str, chunk_size: int, overlap: int) -> List[Dict]:
        """Chunk text while preserving document structure."""
        
        # First, identify major structural boundaries
        sections = self._identify_sections(text)
        
        chunks = []
        current_position = 0
        
        for section in sections:
            section_text = text[section["start"]:section["end"]]
            
            # Chunk the section
            section_chunks = self._chunk_section(section_text, chunk_size, overlap, section)
            
            # Adjust positions to be relative to the full document
            for chunk in section_chunks:
                chunk["start"] += section["start"]
                chunk["end"] += section["start"]
                chunk["section"] = section["type"]
                chunk["section_title"] = section.get("title", "")
            
            chunks.extend(section_chunks)
            current_position = section["end"]
        
        return chunks
    
    def _chunk_section(self, section_text: str, chunk_size: int, overlap: int, section_info: Dict) -> List[Dict]:
        """Chunk a single section of text."""
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(section_text):
            # Determine chunk boundaries
            chunk_end = min(current_pos + chunk_size, len(section_text))
            
            # Try to break at sentence boundaries
            if chunk_end < len(section_text):
                chunk_end = self._find_sentence_boundary(section_text, current_pos, chunk_end)
            
            # Extract chunk text
            chunk_text = section_text[current_pos:chunk_end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunk = {
                    "text": chunk_text,
                    "start": current_pos,
                    "end": chunk_end,
                    "section": section_info["type"],
                    "section_title": section_info.get("title", ""),
                    "chunk_type": "content"
                }
                chunks.append(chunk)
            
            # Move to next chunk with overlap
            current_pos = max(current_pos + chunk_size - overlap, chunk_end)
            
            # Prevent infinite loops
            if current_pos <= chunks[-1]["start"] if chunks else 0:
                current_pos += chunk_size // 2
        
        return chunks
    
    def _chunk_simple(self, text: str, chunk_size: int, overlap: int) -> List[Dict]:
        """Simple chunking without structure preservation."""
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            chunk_end = min(current_pos + chunk_size, len(text))
            
            # Try to break at sentence boundaries
            if chunk_end < len(text):
                chunk_end = self._find_sentence_boundary(text, current_pos, chunk_end)
            
            chunk_text = text[current_pos:chunk_end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunk = {
                    "text": chunk_text,
                    "start": current_pos,
                    "end": chunk_end,
                    "section": "content",
                    "section_title": "",
                    "chunk_type": "content"
                }
                chunks.append(chunk)
            
            current_pos = max(current_pos + chunk_size - overlap, chunk_end)
            
            # Prevent infinite loops
            if current_pos <= chunks[-1]["start"] if chunks else 0:
                current_pos += chunk_size // 2
        
        return chunks
    
    def _identify_sections(self, text: str) -> List[Dict]:
        """Identify major sections in the document."""
        
        sections = []
        current_pos = 0
        
        # Find section markers
        for pattern in self.section_markers:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                if match.start() > current_pos:
                    # Add previous section
                    sections.append({
                        "start": current_pos,
                        "end": match.start(),
                        "type": "content",
                        "title": ""
                    })
                
                # Extract section title
                title_match = re.search(r'(?:SECTION|Section|CHAPTER|Chapter|APPENDIX|Appendix)\s+([^\n]+)', 
                                      text[match.start():match.start() + 100])
                title = title_match.group(1).strip() if title_match else ""
                
                sections.append({
                    "start": match.start(),
                    "end": match.end(),
                    "type": "section_header",
                    "title": title
                })
                
                current_pos = match.end()
        
        # Add final section
        if current_pos < len(text):
            sections.append({
                "start": current_pos,
                "end": len(text),
                "type": "content",
                "title": ""
            })
        
        # Merge small sections
        merged_sections = []
        for section in sections:
            if (section["type"] == "content" and 
                section["end"] - section["start"] < self.min_chunk_size and 
                merged_sections):
                # Merge with previous section
                merged_sections[-1]["end"] = section["end"]
            else:
                merged_sections.append(section)
        
        return merged_sections
    
    def _find_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """Find the best sentence boundary near the preferred end position."""
        
        # Look for sentence endings in reverse from preferred_end
        search_start = max(start, preferred_end - 200)  # Search within 200 chars
        search_text = text[search_start:preferred_end]
        
        best_boundary = preferred_end
        
        for pattern in self.sentence_endings:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                # Use the last match
                last_match = matches[-1]
                boundary = search_start + last_match.end()
                if boundary > start + self.min_chunk_size:
                    best_boundary = boundary
                    break
        
        return best_boundary
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        sentence_count = 0
        for pattern in self.sentence_endings:
            sentence_count += len(re.findall(pattern, text))
        
        # Add 1 if text doesn't end with sentence ending
        if text and not re.search(r'[.!?]\s*$', text):
            sentence_count += 1
        
        return max(1, sentence_count)
    
    def chunk_table(self, table_data: List[List[str]], table_caption: str = "") -> List[Dict]:
        """
        Create chunks from table data.
        
        Args:
            table_data: Table data as list of rows
            table_caption: Optional table caption
            
        Returns:
            List of table chunks
        """
        try:
            if not table_data:
                return []
            
            chunks = []
            
            # Create header chunk if caption exists
            if table_caption:
                header_chunk = {
                    "text": f"Table: {table_caption}",
                    "chunk_type": "table_header",
                    "table_caption": table_caption,
                    "chunk_id": 0
                }
                chunks.append(header_chunk)
            
            # Create chunks for table rows
            for i, row in enumerate(table_data):
                if not row:
                    continue
                
                # Convert row to text
                row_text = " | ".join(str(cell) for cell in row if cell)
                
                if row_text.strip():
                    chunk = {
                        "text": row_text,
                        "chunk_type": "table_row",
                        "row_index": i,
                        "table_caption": table_caption,
                        "chunk_id": len(chunks)
                    }
                    chunks.append(chunk)
            
            logger.info(f"Created {len(chunks)} chunks from table with {len(table_data)} rows")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking table: {e}")
            return []
    
    def chunk_structured_content(self, content: Dict) -> List[Dict]:
        """
        Chunk structured content (tables, images, etc.).
        
        Args:
            content: Structured content dictionary
            
        Returns:
            List of chunks for structured content
        """
        try:
            chunks = []
            
            # Process tables
            tables = content.get("tables", [])
            for table in tables:
                table_chunks = self.chunk_table(
                    table.get("data", []),
                    table.get("caption", "")
                )
                chunks.extend(table_chunks)
            
            # Process images (create descriptive chunks)
            images = content.get("images", [])
            for i, image in enumerate(images):
                image_chunk = {
                    "text": f"Image {i + 1}: {image.get('caption', 'No caption available')}",
                    "chunk_type": "image_description",
                    "image_index": i,
                    "image_caption": image.get("caption", ""),
                    "chunk_id": len(chunks)
                }
                chunks.append(image_chunk)
            
            # Process structure elements
            structure = content.get("structure", [])
            for element in structure:
                if element.get("text"):
                    structure_chunk = {
                        "text": element["text"],
                        "chunk_type": f"structure_{element.get('type', 'unknown')}",
                        "structure_level": element.get("level", 1),
                        "chunk_id": len(chunks)
                    }
                    chunks.append(structure_chunk)
            
            logger.info(f"Created {len(chunks)} chunks from structured content")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking structured content: {e}")
            return []
    
    def get_chunk_statistics(self, chunks: List[Dict]) -> Dict:
        """Get statistics about chunks."""
        if not chunks:
            return {}
        
        chunk_sizes = [chunk["chunk_size"] for chunk in chunks]
        word_counts = [chunk["word_count"] for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_characters": sum(chunk_sizes),
            "total_words": sum(word_counts),
            "average_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "average_word_count": sum(word_counts) / len(word_counts),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "chunk_types": {
                chunk_type: len([c for c in chunks if c.get("chunk_type") == chunk_type])
                for chunk_type in set(c.get("chunk_type", "unknown") for c in chunks)
            }
        }


def get_semantic_chunker() -> SemanticChunker:
    """Get a SemanticChunker instance."""
    return SemanticChunker()
