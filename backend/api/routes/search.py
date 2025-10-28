"""
Search and retrieval API endpoints.
"""

import time
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from backend.core.database import get_db
from backend.core.qdrant_client import get_qdrant_manager, QdrantManager
from backend.core.config import get_settings
from backend.api.dependencies import get_pagination, Pagination
from backend.schemas.models import Document, DocumentCategory, DocumentChunk
from backend.schemas.search import (
    SemanticSearchRequest, HybridSearchRequest, SearchResponse,
    SearchResult, SearchFilters, SearchSuggestionsResponse, SearchSuggestion
)
from backend.services.embedder import get_embedding_service


router = APIRouter()


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    qdrant: QdrantManager = Depends(get_qdrant_manager),
    embedder = Depends(get_embedding_service)
):
    """
    Perform semantic search using vector similarity.

    - **query**: Search query text
    - **category**: Filter by document category
    - **file_type**: Filter by file type
    - **from_date/to_date**: Filter by date range
    - **similarity_threshold**: Minimum similarity score (0.0-1.0)
    - **page/page_size**: Pagination parameters
    """
    start_time = time.time()
    
    try:
        # Generate query embedding
        embedding_result = await embedder.generate_embeddings(request.query)
        if not embedding_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate query embedding: {embedding_result.get('error')}"
            )
        query_embedding = embedding_result["embeddings"][0]
        
        # Build filter conditions
        filter_conditions = []
        
        if request.category:
            filter_conditions.append({"category": request.category.value})
        
        if request.file_type:
            filter_conditions.append({"file_type": request.file_type})
        
        if request.from_date:
            filter_conditions.append({"uploaded_at": {"gte": request.from_date.isoformat()}})
        
        if request.to_date:
            filter_conditions.append({"uploaded_at": {"lte": request.to_date.isoformat()}})
        
        if request.is_archived is not None:
            filter_conditions.append({"is_archived": request.is_archived})
        
        # Perform vector search
        search_results = qdrant.search(
            query_vector=query_embedding,
            limit=request.page_size,
            offset=(request.page - 1) * request.page_size,
            score_threshold=request.similarity_threshold,
            filter_conditions=filter_conditions if filter_conditions else None
        )
        
        # Get document and chunk details
        results = []
        for result in search_results:
            chunk_id = result.payload.get("chunk_id")
            if not chunk_id:
                continue
                
            # Get chunk details from database
            chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if not chunk:
                continue
                
            # Get document details
            document = db.query(Document).filter(Document.id == chunk.document_id).first()
            if not document:
                continue
            
            results.append(SearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                document_filename=document.filename,
                document_category=document.category,
                content=chunk.content,
                page_number=chunk.page_number,
                similarity_score=result.score,
                chunk_index=chunk.chunk_index,
                metadata=chunk.metadata
            ))
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return SearchResponse(
            query=request.query,
            total_results=len(results),  # This is approximate for vector search
            page=request.page,
            page_size=request.page_size,
            results=results,
            search_time_ms=search_time,
            search_type="semantic"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    db: Session = Depends(get_db),
    qdrant: QdrantManager = Depends(get_qdrant_manager),
    embedder = Depends(get_embedding_service)
):
    """
    Perform hybrid search combining semantic and keyword search.

    - **query**: Search query text
    - **category**: Filter by document category
    - **file_type**: Filter by file type
    - **from_date/to_date**: Filter by date range
    - **similarity_threshold**: Minimum similarity score (0.0-1.0)
    - **keyword_weight**: Weight for keyword search (0.0-1.0)
    - **semantic_weight**: Weight for semantic search (0.0-1.0)
    - **page/page_size**: Pagination parameters
    """
    start_time = time.time()
    
    try:
        # Generate query embedding for semantic search
        embedding_result = await embedder.generate_embeddings(request.query)
        if not embedding_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate query embedding: {embedding_result.get('error')}"
            )
        query_embedding = embedding_result["embeddings"][0]
        
        # Build filter conditions
        filter_conditions = []
        
        if request.category:
            filter_conditions.append({"category": request.category.value})
        
        if request.file_type:
            filter_conditions.append({"file_type": request.file_type})
        
        if request.from_date:
            filter_conditions.append({"uploaded_at": {"gte": request.from_date.isoformat()}})
        
        if request.to_date:
            filter_conditions.append({"uploaded_at": {"lte": request.to_date.isoformat()}})
        
        if request.is_archived is not None:
            filter_conditions.append({"is_archived": request.is_archived})
        
        # Perform semantic search
        semantic_results = qdrant.search(
            query_vector=query_embedding,
            limit=request.page_size * 2,  # Get more results for hybrid scoring
            score_threshold=request.similarity_threshold,
            filter_conditions=filter_conditions if filter_conditions else None
        )
        
        # Perform keyword search
        keyword_query = db.query(DocumentChunk).join(Document)
        
        # Apply filters
        if request.category:
            keyword_query = keyword_query.filter(Document.category == request.category)
        
        if request.file_type:
            keyword_query = keyword_query.filter(Document.file_type == request.file_type)
        
        if request.from_date:
            keyword_query = keyword_query.filter(Document.uploaded_at >= request.from_date)
        
        if request.to_date:
            keyword_query = keyword_query.filter(Document.uploaded_at <= request.to_date)
        
        if request.is_archived is not None:
            keyword_query = keyword_query.filter(Document.is_archived == request.is_archived)
        
        # Text search in content
        keyword_query = keyword_query.filter(
            DocumentChunk.content.ilike(f"%{request.query}%")
        )
        
        keyword_results = keyword_query.limit(request.page_size * 2).all()
        
        # Combine and score results
        combined_scores = {}
        
        # Process semantic results
        for result in semantic_results:
            chunk_id = result.payload.get("chunk_id")
            if chunk_id:
                combined_scores[chunk_id] = {
                    "semantic_score": result.score,
                    "keyword_score": 0.0,
                    "chunk_id": chunk_id
                }
        
        # Process keyword results
        for chunk in keyword_results:
            chunk_id = chunk.id
            if chunk_id in combined_scores:
                # Calculate keyword score based on text match frequency
                content_lower = chunk.content.lower()
                query_lower = request.query.lower()
                keyword_score = content_lower.count(query_lower) / len(content_lower.split())
                combined_scores[chunk_id]["keyword_score"] = min(keyword_score, 1.0)
            else:
                combined_scores[chunk_id] = {
                    "semantic_score": 0.0,
                    "keyword_score": 1.0,  # High score for keyword-only matches
                    "chunk_id": chunk_id
                }
        
        # Calculate hybrid scores
        hybrid_results = []
        for chunk_id, scores in combined_scores.items():
            hybrid_score = (
                scores["semantic_score"] * request.semantic_weight +
                scores["keyword_score"] * request.keyword_weight
            )
            
            if hybrid_score >= request.similarity_threshold:
                hybrid_results.append((chunk_id, hybrid_score))
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x[1], reverse=True)
        
        # Apply pagination
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_results = hybrid_results[start_idx:end_idx]
        
        # Get detailed results
        results = []
        for chunk_id, score in paginated_results:
            chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if not chunk:
                continue
                
            document = db.query(Document).filter(Document.id == chunk.document_id).first()
            if not document:
                continue
            
            results.append(SearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                document_filename=document.filename,
                document_category=document.category,
                content=chunk.content,
                page_number=chunk.page_number,
                similarity_score=score,
                chunk_index=chunk.chunk_index,
                metadata=chunk.metadata
            ))
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return SearchResponse(
            query=request.query,
            total_results=len(hybrid_results),
            page=request.page,
            page_size=request.page_size,
            results=results,
            search_time_ms=search_time,
            search_type="hybrid"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid search failed: {str(e)}"
        )


@router.get("/filters", response_model=SearchFilters)
async def get_search_filters(db: Session = Depends(get_db)):
    """
    Get available search filters.

    Returns available categories, file types, and date ranges for filtering.
    """
    # Get available categories
    categories = [cat for cat in DocumentCategory]
    
    # Get available file types
    file_types = db.query(Document.file_type).distinct().all()
    file_types = [ft[0] for ft in file_types if ft[0]]
    
    # Get date range
    date_range = db.query(
        func.min(Document.uploaded_at),
        func.max(Document.uploaded_at)
    ).filter(Document.is_active == True).first()
    
    date_range_dict = None
    if date_range[0] and date_range[1]:
        date_range_dict = {
            "from": date_range[0],
            "to": date_range[1]
        }
    
    return SearchFilters(
        categories=categories,
        file_types=file_types,
        date_range=date_range_dict
    )


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """
    Get search suggestions for a query.

    Returns query expansion suggestions, spelling corrections, and category suggestions.
    """
    suggestions = []
    
    # Simple query expansion based on document content
    # Find common terms that appear with the query
    query_words = query.lower().split()
    
    # Get chunks that contain the query
    matching_chunks = db.query(DocumentChunk.content)\
        .join(Document)\
        .filter(
            Document.is_active == True,
            DocumentChunk.content.ilike(f"%{query}%")
        ).limit(100).all()
    
    # Extract common terms
    term_frequency = {}
    for chunk_content, in matching_chunks:
        words = chunk_content.lower().split()
        for word in words:
            if len(word) > 3 and word not in query_words:
                term_frequency[word] = term_frequency.get(word, 0) + 1
    
    # Get top terms
    top_terms = sorted(term_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
    for term, freq in top_terms:
        suggestions.append(SearchSuggestion(
            suggestion=f"{query} {term}",
            type="query_expansion"
        ))
    
    # Category suggestions based on query content
    category_keywords = {
        DocumentCategory.SAFETY: ["safety", "hazard", "msds", "sds", "chemical", "danger"],
        DocumentCategory.TECHNICAL: ["specification", "technical", "data", "sheet", "spec"],
        DocumentCategory.BUSINESS: ["invoice", "contract", "agreement", "business", "commercial"],
        DocumentCategory.EQUIPMENT: ["manual", "equipment", "maintenance", "operation", "procedure"],
        DocumentCategory.REGULATORY: ["permit", "certificate", "compliance", "regulatory", "license"]
    }
    
    query_lower = query.lower()
    for category, keywords in category_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            suggestions.append(SearchSuggestion(
                suggestion=f"category:{category.value}",
                type="category"
            ))
    
    return SearchSuggestionsResponse(
        query=query,
        suggestions=suggestions[:10]  # Limit to 10 suggestions
    )
