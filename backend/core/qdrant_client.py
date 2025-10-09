"""
Qdrant vector database client wrapper.
"""

from typing import List, Dict, Any, Optional
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    SearchRequest, ScoredPoint
)

from backend.core.config import get_settings


class QdrantManager:
    """Manages Qdrant vector database operations."""

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.collection_name = self.settings.qdrant.collection_name
        self._connect()

    def _connect(self):
        """Initialize connection to Qdrant."""
        self.client = QdrantClient(
            host=self.settings.qdrant.host,
            port=self.settings.qdrant.port,
            timeout=60
        )

    def _get_distance_metric(self) -> Distance:
        """Get distance metric from settings."""
        metric_map = {
            "Cosine": Distance.COSINE,
            "Euclidean": Distance.EUCLID,
            "Dot": Distance.DOT,
        }
        return metric_map.get(
            self.settings.qdrant.distance_metric,
            Distance.COSINE
        )

    def collection_exists(self) -> bool:
        """Check if collection exists."""
        try:
            collections = self.client.get_collections()
            return any(
                col.name == self.collection_name
                for col in collections.collections
            )
        except Exception as e:
            print(f"Error checking collection: {e}")
            return False

    def create_collection(
        self,
        vector_size: Optional[int] = None,
        force_recreate: bool = False
    ) -> bool:
        """
        Create collection in Qdrant.

        Args:
            vector_size: Size of vectors (default from settings)
            force_recreate: Delete existing collection and recreate

        Returns:
            True if collection created successfully
        """
        if vector_size is None:
            vector_size = self.settings.embeddings.dimensions

        try:
            # Delete if force recreate
            if force_recreate and self.collection_exists():
                self.client.delete_collection(self.collection_name)

            # Create collection if it doesn't exist
            if not self.collection_exists():
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=self._get_distance_metric()
                    )
                )
                print(f"Created collection: {self.collection_name}")
                return True

            return True
        except Exception as e:
            print(f"Error creating collection: {e}")
            return False

    def upsert_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Insert or update vectors in collection.

        Args:
            vectors: List of embedding vectors
            payloads: List of metadata dictionaries for each vector
            ids: Optional list of point IDs (generated if not provided)

        Returns:
            List of point IDs
        """
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]

        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return ids
        except Exception as e:
            print(f"Error upserting vectors: {e}")
            raise

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[ScoredPoint]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Metadata filters (e.g., {"category": "Safety Data Sheets"})

        Returns:
            List of search results with scores and payloads
        """
        search_filter = None
        if filter_conditions:
            must_conditions = [
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
                for key, value in filter_conditions.items()
            ]
            search_filter = Filter(must=must_conditions)

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            return results
        except Exception as e:
            print(f"Error searching vectors: {e}")
            raise

    def delete_vectors(self, ids: List[str]) -> bool:
        """
        Delete vectors by IDs.

        Args:
            ids: List of point IDs to delete

        Returns:
            True if deletion successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            return True
        except Exception as e:
            print(f"Error deleting vectors: {e}")
            return False

    def delete_by_filter(self, filter_conditions: Dict[str, Any]) -> bool:
        """
        Delete vectors matching filter conditions.

        Args:
            filter_conditions: Metadata filters

        Returns:
            True if deletion successful
        """
        must_conditions = [
            FieldCondition(
                key=key,
                match=MatchValue(value=value)
            )
            for key, value in filter_conditions.items()
        ]
        search_filter = Filter(must=must_conditions)

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=search_filter
            )
            return True
        except Exception as e:
            print(f"Error deleting vectors by filter: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information and statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value
                }
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {}

    def scroll_all_points(
        self,
        limit: int = 100,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scroll through all points in collection.

        Args:
            limit: Number of points to retrieve per batch
            with_vectors: Include vectors in results

        Returns:
            List of all points
        """
        all_points = []
        offset = None

        try:
            while True:
                results, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                    with_vectors=with_vectors
                )

                all_points.extend(results)

                if next_offset is None:
                    break

                offset = next_offset

            return all_points
        except Exception as e:
            print(f"Error scrolling points: {e}")
            return []

    def close(self):
        """Close Qdrant client connection."""
        if self.client:
            self.client.close()


# Global Qdrant manager instance
_qdrant_manager: Optional[QdrantManager] = None


def get_qdrant_manager() -> QdrantManager:
    """Get global Qdrant manager instance."""
    global _qdrant_manager
    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()
    return _qdrant_manager


def close_qdrant():
    """Close Qdrant connections."""
    global _qdrant_manager
    if _qdrant_manager is not None:
        _qdrant_manager.close()
        _qdrant_manager = None
