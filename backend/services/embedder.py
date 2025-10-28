"""
Embedding service for generating vector embeddings.

This service generates embeddings for text chunks using OpenAI's text-embedding-3-small
model via OpenRouter API, with fallback to local sentence-transformers.
"""

import logging
from typing import Dict, List, Optional, Union

import numpy as np
from backend.core.config import get_settings
from backend.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm_client = get_llm_client()
        self.local_embedder = None
        
        # Embedding configuration
        self.default_model = self.settings.llm.embedding_model
        self.batch_size = self.settings.processing.embedding_batch_size
        self.max_retries = 3
        
        # Initialize local embedder as fallback
        self._initialize_local_embedder()
    
    def _initialize_local_embedder(self):
        """Initialize local sentence-transformers embedder as fallback."""
        try:
            import sentence_transformers
            self.local_embedder = sentence_transformers.SentenceTransformer(
                'all-MiniLM-L6-v2'  # Lightweight, fast model
            )
            logger.info("Local sentence-transformers embedder initialized")
        except ImportError:
            logger.warning("sentence-transformers not available, using API only")
        except Exception as e:
            logger.warning(f"Failed to initialize local embedder: {e}")
    
    async def generate_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: Optional[str] = None,
        use_local_fallback: bool = True
    ) -> Dict:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Text or list of texts to embed
            model: Embedding model to use
            use_local_fallback: Whether to use local embedder if API fails
            
        Returns:
            Dictionary with embeddings and metadata
        """
        try:
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            if not texts:
                return {
                    "embeddings": [],
                    "metadata": {"model": "none", "method": "empty"},
                    "success": True
                }
            
            model = model or self.default_model
            
            logger.info(f"Generating embeddings for {len(texts)} texts using {model}")
            
            # Try API first
            try:
                result = await self._generate_api_embeddings(texts, model)
                if result["success"]:
                    return result
            except Exception as e:
                logger.warning(f"API embedding generation failed: {e}")
            
            # Fallback to local embedder
            if use_local_fallback and self.local_embedder:
                logger.info("Falling back to local sentence-transformers")
                return self._generate_local_embeddings(texts)
            
            return {
                "embeddings": [],
                "error": "Both API and local embedding generation failed",
                "success": False
            }
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return {
                "embeddings": [],
                "error": str(e),
                "success": False
            }
    
    async def _generate_api_embeddings(self, texts: List[str], model: str) -> Dict:
        """Generate embeddings using OpenRouter API."""
        
        # Process in batches to avoid API limits
        all_embeddings = []
        total_tokens = 0
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            
            # Retry logic
            for attempt in range(self.max_retries):
                try:
                    result = await self.llm_client.generate_embeddings(
                        texts=batch_texts,
                        model=model
                    )
                    
                    if result["success"]:
                        all_embeddings.extend(result["embeddings"])
                        total_tokens += result["metadata"].get("usage", {}).get("total_tokens", 0)
                        break
                    else:
                        logger.warning(f"API embedding attempt {attempt + 1} failed: {result.get('error')}")
                        
                except Exception as e:
                    logger.warning(f"API embedding attempt {attempt + 1} error: {e}")
                    
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise Exception(f"All {self.max_retries} API attempts failed")
        
        return {
            "embeddings": all_embeddings,
            "metadata": {
                "model": model,
                "method": "api",
                "total_tokens": total_tokens,
                "text_count": len(texts)
            },
            "success": True
        }
    
    def _generate_local_embeddings(self, texts: List[str]) -> Dict:
        """Generate embeddings using local sentence-transformers."""
        
        try:
            if not self.local_embedder:
                raise Exception("Local embedder not available")
            
            # Process in batches to manage memory
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i + self.batch_size]
                
                # Generate embeddings
                embeddings = self.local_embedder.encode(
                    batch_texts,
                    convert_to_tensor=False,
                    show_progress_bar=False
                )
                
                all_embeddings.extend(embeddings.tolist())
            
            return {
                "embeddings": all_embeddings,
                "metadata": {
                    "model": "all-MiniLM-L6-v2",
                    "method": "local",
                    "text_count": len(texts),
                    "dimensions": len(all_embeddings[0]) if all_embeddings else 0
                },
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error generating local embeddings: {e}")
            return {
                "embeddings": [],
                "error": str(e),
                "success": False
            }
    
    async def embed_chunks(self, chunks: List[Dict], model: Optional[str] = None) -> List[Dict]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of chunk dictionaries
            model: Embedding model to use
            
        Returns:
            List of chunks with embeddings added
        """
        try:
            if not chunks:
                return []
            
            logger.info(f"Embedding {len(chunks)} chunks")
            
            # Extract texts from chunks
            texts = [chunk["text"] for chunk in chunks]
            
            # Generate embeddings
            result = await self.generate_embeddings(texts, model)
            
            if not result["success"]:
                logger.error(f"Failed to generate embeddings: {result.get('error')}")
                return chunks  # Return chunks without embeddings
            
            embeddings = result["embeddings"]
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                if i < len(embeddings):
                    chunk["embedding"] = embeddings[i]
                    chunk["embedding_model"] = result["metadata"]["model"]
                    chunk["embedding_method"] = result["metadata"]["method"]
                else:
                    logger.warning(f"No embedding available for chunk {i}")
            
            logger.info(f"Successfully embedded {len(embeddings)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error embedding chunks: {e}")
            return chunks
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (-1 to 1)
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def find_most_similar_chunks(
        self, 
        query_embedding: List[float], 
        chunk_embeddings: List[List[float]], 
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find most similar chunks to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            chunk_embeddings: List of chunk embedding vectors
            top_k: Number of top similar chunks to return
            
        Returns:
            List of similarity scores and indices
        """
        try:
            similarities = []
            
            for i, chunk_embedding in enumerate(chunk_embeddings):
                similarity = self.calculate_similarity(query_embedding, chunk_embedding)
                similarities.append({
                    "index": i,
                    "similarity": similarity
                })
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar chunks: {e}")
            return []
    
    def get_embedding_dimensions(self, model: str) -> int:
        """Get the dimensions of embeddings for a specific model."""
        
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "all-MiniLM-L6-v2": 384,  # Local model
        }
        
        return model_dimensions.get(model, 1536)  # Default to OpenAI small
    
    def validate_embedding(self, embedding: List[float], expected_dimensions: Optional[int] = None) -> bool:
        """
        Validate an embedding vector.
        
        Args:
            embedding: Embedding vector to validate
            expected_dimensions: Expected number of dimensions
            
        Returns:
            True if embedding is valid
        """
        try:
            if not isinstance(embedding, list):
                return False
            
            if not all(isinstance(x, (int, float)) for x in embedding):
                return False
            
            if expected_dimensions and len(embedding) != expected_dimensions:
                return False
            
            # Check for NaN or infinite values
            if any(not np.isfinite(x) for x in embedding):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating embedding: {e}")
            return False
    
    def get_available_models(self) -> Dict:
        """Get available embedding models."""
        return {
            "api_models": [
                "text-embedding-3-small",
                "text-embedding-3-large"
            ],
            "local_models": [
                "all-MiniLM-L6-v2"
            ] if self.local_embedder else [],
            "default_model": self.default_model
        }


def get_embedding_service() -> EmbeddingService:
    """Get an EmbeddingService instance."""
    return EmbeddingService()
