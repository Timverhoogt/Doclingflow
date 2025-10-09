"""
Pydantic schemas for document classification.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.schemas.models import DocumentCategory


class ClassificationCategorySchema(BaseModel):
    """Classification category schema."""
    name: str
    keywords: List[str] = []
    description: Optional[str] = None


class ClassificationRequest(BaseModel):
    """Request schema for document classification."""
    content: str = Field(..., description="Document content to classify")
    filename: Optional[str] = Field(None, description="Original filename for context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ClassificationResult(BaseModel):
    """Classification result schema."""
    category: DocumentCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    alternative_categories: Optional[List[Dict[str, Any]]] = None
    # alternative_categories format:
    # [{"category": "Safety Data Sheets", "confidence": 0.3}, ...]


class ClassificationResponse(BaseModel):
    """Response schema for classification endpoint."""
    document_id: Optional[int] = None
    result: ClassificationResult


class EntityExtractionRequest(BaseModel):
    """Request schema for entity extraction."""
    content: str = Field(..., description="Document content")
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Types of entities to extract"
    )


class EntityExtractionResult(BaseModel):
    """Entity extraction result schema."""
    entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Extracted entities by type"
    )
    # Format: {
    #     "equipment_ids": ["T-101", "P-202"],
    #     "chemical_names": ["Benzene", "Toluene"],
    #     "dates": ["2024-01-15"],
    #     "locations": ["Tank Farm A"],
    #     "personnel": ["John Doe"],
    #     "measurements": ["500 psi", "150°C"]
    # }
    total_entities: int = Field(default=0, description="Total number of entities extracted")


class EntityExtractionResponse(BaseModel):
    """Response schema for entity extraction endpoint."""
    document_id: Optional[int] = None
    result: EntityExtractionResult


class ClassificationStatsResponse(BaseModel):
    """Statistics for classification performance."""
    total_classified: int
    by_category: Dict[str, int]
    avg_confidence: float
    low_confidence_count: int = Field(
        default=0,
        description="Number of documents with confidence < 0.7"
    )
