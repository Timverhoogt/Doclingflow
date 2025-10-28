"""
Pydantic schemas for search API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from backend.schemas.models import DocumentCategory


class SearchRequest(BaseModel):
    """Base search request schema."""
    query: str = Field(..., min_length=1, max_length=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SemanticSearchRequest(SearchRequest):
    """Semantic search request schema."""
    category: Optional[DocumentCategory] = None
    file_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    is_archived: Optional[bool] = False
    similarity_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)


class HybridSearchRequest(SearchRequest):
    """Hybrid search request schema."""
    category: Optional[DocumentCategory] = None
    file_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    is_archived: Optional[bool] = False
    similarity_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: Optional[float] = Field(default=0.3, ge=0.0, le=1.0)
    semantic_weight: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Individual search result schema."""
    chunk_id: int
    document_id: int
    document_filename: str
    document_category: Optional[DocumentCategory] = None
    content: str
    page_number: Optional[int] = None
    similarity_score: float
    chunk_index: int
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response schema."""
    query: str
    total_results: int
    page: int
    page_size: int
    results: List[SearchResult]
    search_time_ms: float
    search_type: str  # "semantic" or "hybrid"


class SearchFilters(BaseModel):
    """Available search filters schema."""
    categories: List[DocumentCategory]
    file_types: List[str]
    date_range: Optional[Dict[str, datetime]] = None


class SearchSuggestion(BaseModel):
    """Search suggestion schema."""
    suggestion: str
    type: str  # "query_expansion", "spelling", "category"


class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response schema."""
    query: str
    suggestions: List[SearchSuggestion]
