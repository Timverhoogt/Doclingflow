"""
Vector store service for Qdrant operations.

This service handles vector storage, search, and management using Qdrant
for document chunks and embeddings.
"""

import logging
import uuid
from typing import Dict, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from backend.core.config import get_settings
from backend.core.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)


class VectorStore:
    """Service for vector storage operations with Qdrant."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = get_qdrant_client()
        
        # Collection configuration
        self.collection_name = self.settings.qdrant.collection_name
        self.vector_size = self.settings.qdrant.vector_size
        self.distance_metric = Distance.COSINE
        
        # Ensure collection exists
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Ensure the main collection exists."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.create_collection(self.collection_name, self.vector_size)
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def create_collection(
        self, 
        collection_name: str, 
        vector_size: int, 
        distance_metric: Distance = Distance.COSINE
    ) -> bool:
        """
        Create a new collection.
        
        Args:
            collection_name: Name of the collection
            vector_size: Size of vectors in the collection
            distance_metric: Distance metric for similarity calculation
            
        Returns:
            True if collection was created successfully
        """
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_metric
                )
            )
            
            logger.info(f"Created collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection was deleted successfully
        """
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {e}")
            return False
    
    def upsert_chunks(
        self, 
        chunks: List[Dict], 
        collection_name: Optional[str] = None
    ) -> Dict:
        """
        Upsert document chunks with embeddings to the vector store.
        
        Args:
            chunks: List of chunk dictionaries with embeddings
            collection_name: Collection name (defaults to main collection)
            
        Returns:
            Dictionary with upsert results
        """
        try:
            collection_name = collection_name or self.collection_name
            
            if not chunks:
                return {"success": True, "upserted": 0}
            
            logger.info(f"Upserting {len(chunks)} chunks to collection {collection_name}")
            
            # Prepare points for upsert
            points = []
            successful_chunks = 0
            
            for chunk in chunks:
                try:
                    # Validate chunk has required fields
                    if not self._validate_chunk(chunk):
                        logger.warning(f"Skipping invalid chunk: {chunk.get('chunk_id', 'unknown')}")
                        continue
                    
                    # Create point
                    point = self._create_point_from_chunk(chunk)
                    points.append(point)
                    successful_chunks += 1
                    
                except Exception as e:
                    logger.error(f"Error preparing chunk {chunk.get('chunk_id', 'unknown')}: {e}")
                    continue
            
            if not points:
                return {"success": False, "error": "No valid chunks to upsert"}
            
            # Upsert points
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"Successfully upserted {successful_chunks} chunks")
            
            return {
                "success": True,
                "upserted": successful_chunks,
                "total_chunks": len(chunks),
                "failed": len(chunks) - successful_chunks
            }
            
        except Exception as e:
            logger.error(f"Error upserting chunks: {e}")
            return {
                "success": False,
                "error": str(e),
                "upserted": 0
            }
    
    def _validate_chunk(self, chunk: Dict) -> bool:
        """Validate a chunk has required fields."""
        required_fields = ["text", "embedding", "chunk_id"]
        
        for field in required_fields:
            if field not in chunk:
                return False
        
        if not isinstance(chunk["embedding"], list) or not chunk["embedding"]:
            return False
        
        return True
    
    def _create_point_from_chunk(self, chunk: Dict) -> PointStruct:
        """Create a Qdrant point from a chunk dictionary."""
        
        # Generate unique ID if not present
        point_id = chunk.get("point_id") or str(uuid.uuid4())
        
        # Prepare payload (metadata)
        payload = {
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "chunk_size": chunk.get("chunk_size", len(chunk["text"])),
            "word_count": chunk.get("word_count", len(chunk["text"].split())),
            "chunk_type": chunk.get("chunk_type", "content"),
            "section": chunk.get("section", "content"),
            "section_title": chunk.get("section_title", ""),
            "document_id": chunk.get("document_id"),
            "document_filename": chunk.get("document_filename", ""),
            "document_category": chunk.get("document_category", ""),
            "embedding_model": chunk.get("embedding_model", "unknown"),
            "created_at": chunk.get("created_at"),
        }
        
        # Add optional fields
        if "start" in chunk:
            payload["start"] = chunk["start"]
        if "end" in chunk:
            payload["end"] = chunk["end"]
        
        return PointStruct(
            id=point_id,
            vector=chunk["embedding"],
            payload=payload
        )
    
    def search_similar(
        self,
        query_embedding: List[float],
        collection_name: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query embedding vector
            collection_name: Collection name (defaults to main collection)
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional filters for search
            
        Returns:
            List of search results with metadata
        """
        try:
            collection_name = collection_name or self.collection_name
            
            logger.info(f"Searching for similar vectors in {collection_name}")
            
            # Prepare search parameters
            search_params = {
                "collection_name": collection_name,
                "query_vector": query_embedding,
                "limit": limit,
                "score_threshold": score_threshold,
                "with_payload": True,
                "with_vectors": False  # Don't return vectors to save bandwidth
            }
            
            # Add filters if provided
            if filters:
                search_params["query_filter"] = self._build_filter(filters)
            
            # Perform search
            results = self.client.search(**search_params)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_result = {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "text": result.payload.get("text", ""),
                    "chunk_id": result.payload.get("chunk_id"),
                    "document_id": result.payload.get("document_id"),
                    "document_filename": result.payload.get("document_filename", ""),
                    "document_category": result.payload.get("document_category", ""),
                    "chunk_type": result.payload.get("chunk_type", "content"),
                    "section": result.payload.get("section", "content"),
                    "section_title": result.payload.get("section_title", "")
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Found {len(formatted_results)} similar vectors")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar vectors: {e}")
            return []
    
    def _build_filter(self, filters: Dict) -> Filter:
        """Build Qdrant filter from filter dictionary."""
        conditions = []
        
        for field, value in filters.items():
            if isinstance(value, list):
                # Multiple values (OR condition)
                for val in value:
                    conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=val)
                        )
                    )
            else:
                # Single value
                conditions.append(
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    )
                )
        
        return Filter(must=conditions) if conditions else None
    
    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict:
        """
        Get information about a collection.
        
        Args:
            collection_name: Collection name (defaults to main collection)
            
        Returns:
            Dictionary with collection information
        """
        try:
            collection_name = collection_name or self.collection_name
            
            info = self.client.get_collection(collection_name)
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status,
                "payload_schema": info.payload_schema,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_document_chunks(self, document_id: int, collection_name: Optional[str] = None) -> bool:
        """
        Delete all chunks for a specific document.
        
        Args:
            document_id: Document ID
            collection_name: Collection name (defaults to main collection)
            
        Returns:
            True if chunks were deleted successfully
        """
        try:
            collection_name = collection_name or self.collection_name
            
            logger.info(f"Deleting chunks for document {document_id}")
            
            # Create filter for document ID
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            # Delete points matching the filter
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=filter_condition)
            )
            
            logger.info(f"Successfully deleted chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document chunks: {e}")
            return False
    
    def get_document_chunks(
        self, 
        document_id: int, 
        collection_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: Document ID
            collection_name: Collection name (defaults to main collection)
            limit: Maximum number of chunks to return
            
        Returns:
            List of chunk dictionaries
        """
        try:
            collection_name = collection_name or self.collection_name
            
            # Create filter for document ID
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            # Search with filter
            results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=filter_condition,
                limit=limit or 1000,
                with_payload=True,
                with_vectors=False
            )
            
            chunks = []
            for point in results[0]:  # results is a tuple (points, next_page_offset)
                chunk = {
                    "id": point.id,
                    "payload": point.payload,
                    "text": point.payload.get("text", ""),
                    "chunk_id": point.payload.get("chunk_id"),
                    "chunk_type": point.payload.get("chunk_type", "content"),
                    "section": point.payload.get("section", "content"),
                    "section_title": point.payload.get("section_title", "")
                }
                chunks.append(chunk)
            
            logger.info(f"Retrieved {len(chunks)} chunks for document {document_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            return []
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict:
        """
        Get statistics for a collection.
        
        Args:
            collection_name: Collection name (defaults to main collection)
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection_name = collection_name or self.collection_name
            
            info = self.client.get_collection(collection_name)
            
            return {
                "collection_name": collection_name,
                "total_points": info.points_count,
                "total_vectors": info.vectors_count,
                "indexed_vectors": info.indexed_vectors_count,
                "segments": info.segments_count,
                "status": info.status,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_vector_store() -> VectorStore:
    """Get a VectorStore instance."""
    return VectorStore()
