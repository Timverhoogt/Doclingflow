"""
LLM client service for OpenRouter API integration.

This service provides a unified interface for interacting with various LLM providers
through the OpenRouter API, with support for Claude models and OpenAI embeddings.
"""

import logging
import time
from typing import Dict, List, Optional, Union

import httpx
from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM providers via OpenRouter API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.llm.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Default headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://doclingflow.local",  # Optional: for tracking
            "X-Title": "Doclingflow Document Processing"  # Optional: for tracking
        }
        
        # Model configurations
        self.models = {
            "claude-3.5-sonnet": {
                "provider": "anthropic/claude-3.5-sonnet",
                "max_tokens": 8192,
                "context_window": 200000
            },
            "claude-3-haiku": {
                "provider": "anthropic/claude-3-haiku",
                "max_tokens": 4096,
                "context_window": 200000
            },
            "gpt-4o": {
                "provider": "openai/gpt-4o",
                "max_tokens": 4096,
                "context_window": 128000
            },
            "gpt-4o-mini": {
                "provider": "openai/gpt-4o-mini",
                "max_tokens": 16384,
                "context_window": 128000
            }
        }
        
        # Embedding models
        self.embedding_models = {
            "text-embedding-3-small": {
                "provider": "openai/text-embedding-3-small",
                "dimensions": 1536
            },
            "text-embedding-3-large": {
                "provider": "openai/text-embedding-3-large",
                "dimensions": 3072
            }
        }
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "claude-3.5-sonnet",
        max_tokens: Optional[int] = None,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Generate text using the specified LLM model.
        
        Args:
            prompt: The input prompt
            model: Model to use (default: claude-3.5-sonnet)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with generated text and metadata
        """
        try:
            if model not in self.models:
                raise ValueError(f"Unsupported model: {model}")
            
            model_config = self.models[model]
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request payload
            payload = {
                "model": model_config["provider"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens or model_config["max_tokens"],
                **kwargs
            }
            
            logger.info(f"Generating text with {model} (prompt length: {len(prompt)})")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
            
            # Extract generated text
            generated_text = result["choices"][0]["message"]["content"]
            
            # Extract metadata
            usage = result.get("usage", {})
            metadata = {
                "model": model,
                "provider": model_config["provider"],
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "finish_reason": result["choices"][0].get("finish_reason", "unknown")
            }
            
            logger.info(f"Generated text successfully: {metadata['completion_tokens']} tokens")
            
            return {
                "text": generated_text,
                "metadata": metadata,
                "success": True
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error generating text: {e.response.status_code} - {e.response.text}")
            return {
                "text": "",
                "error": f"HTTP error: {e.response.status_code}",
                "success": False
            }
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return {
                "text": "",
                "error": str(e),
                "success": False
            }
    
    async def generate_embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "text-embedding-3-small",
        **kwargs
    ) -> Dict:
        """
        Generate embeddings for text(s) using the specified embedding model.
        
        Args:
            texts: Text or list of texts to embed
            model: Embedding model to use
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with embeddings and metadata
        """
        try:
            if model not in self.embedding_models:
                raise ValueError(f"Unsupported embedding model: {model}")
            
            model_config = self.embedding_models[model]
            
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            # Prepare request payload
            payload = {
                "model": model_config["provider"],
                "input": texts,
                **kwargs
            }
            
            logger.info(f"Generating embeddings with {model} for {len(texts)} texts")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
            
            # Extract embeddings
            embeddings = [item["embedding"] for item in result["data"]]
            
            # Extract metadata
            metadata = {
                "model": model,
                "provider": model_config["provider"],
                "dimensions": model_config["dimensions"],
                "text_count": len(texts),
                "usage": result.get("usage", {})
            }
            
            logger.info(f"Generated embeddings successfully: {len(embeddings)} vectors")
            
            return {
                "embeddings": embeddings,
                "metadata": metadata,
                "success": True
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error generating embeddings: {e.response.status_code} - {e.response.text}")
            return {
                "embeddings": [],
                "error": f"HTTP error: {e.response.status_code}",
                "success": False
            }
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return {
                "embeddings": [],
                "error": str(e),
                "success": False
            }
    
    async def classify_document(
        self,
        text_content: str,
        categories: List[str],
        model: str = "claude-3.5-sonnet"
    ) -> Dict:
        """
        Classify a document into predefined categories.
        
        Args:
            text_content: Document text content
            categories: List of possible categories
            model: Model to use for classification
            
        Returns:
            Dictionary with classification results
        """
        try:
            # Truncate text if too long
            max_length = 8000  # Leave room for prompt
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "..."
            
            # Create classification prompt
            categories_str = ", ".join(categories)
            prompt = f"""
Analyze the following document and classify it into one of these categories: {categories_str}

Document content:
{text_content}

Please respond with:
1. The most appropriate category
2. A confidence score (0.0 to 1.0)
3. A brief explanation of your reasoning

Format your response as JSON:
{{
    "category": "selected_category",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}
"""
            
            system_prompt = """You are an expert document classifier specializing in petrochemical industry documents. 
            Analyze documents carefully and provide accurate classifications with confidence scores."""
            
            result = await self.generate_text(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            if not result["success"]:
                return result
            
            # Parse JSON response
            try:
                import json
                classification = json.loads(result["text"])
                
                # Validate response
                if "category" not in classification or "confidence" not in classification:
                    raise ValueError("Invalid classification response format")
                
                if classification["category"] not in categories:
                    logger.warning(f"Model returned unexpected category: {classification['category']}")
                    # Use the first category as fallback
                    classification["category"] = categories[0]
                    classification["confidence"] = 0.5
                
                return {
                    "category": classification["category"],
                    "confidence": float(classification["confidence"]),
                    "reasoning": classification.get("reasoning", ""),
                    "metadata": result["metadata"],
                    "success": True
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing classification response: {e}")
                return {
                    "category": categories[0],  # Fallback
                    "confidence": 0.5,
                    "reasoning": "Failed to parse model response",
                    "error": str(e),
                    "success": False
                }
            
        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            return {
                "category": categories[0],  # Fallback
                "confidence": 0.5,
                "reasoning": "Classification failed",
                "error": str(e),
                "success": False
            }
    
    async def extract_entities(
        self,
        text_content: str,
        entity_types: List[str],
        model: str = "claude-3.5-sonnet"
    ) -> Dict:
        """
        Extract entities from document text.
        
        Args:
            text_content: Document text content
            entity_types: List of entity types to extract
            model: Model to use for extraction
            
        Returns:
            Dictionary with extracted entities
        """
        try:
            # Truncate text if too long
            max_length = 8000
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "..."
            
            # Create entity extraction prompt
            entity_types_str = ", ".join(entity_types)
            prompt = f"""
Extract the following types of entities from the document: {entity_types_str}

Document content:
{text_content}

For each entity found, provide:
- The entity text
- The entity type
- The position in the document (character range)
- Any additional context or metadata

Format your response as JSON:
{{
    "entities": [
        {{
            "text": "entity_text",
            "type": "entity_type",
            "start": 123,
            "end": 135,
            "context": "surrounding text",
            "metadata": {{}}
        }}
    ]
}}
"""
            
            system_prompt = """You are an expert entity extraction system for petrochemical industry documents. 
            Extract entities accurately and provide precise character positions."""
            
            result = await self.generate_text(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            if not result["success"]:
                return result
            
            # Parse JSON response
            try:
                import json
                extraction = json.loads(result["text"])
                
                return {
                    "entities": extraction.get("entities", []),
                    "metadata": result["metadata"],
                    "success": True
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing entity extraction response: {e}")
                return {
                    "entities": [],
                    "error": str(e),
                    "success": False
                }
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {
                "entities": [],
                "error": str(e),
                "success": False
            }
    
    def get_available_models(self) -> Dict:
        """Get list of available models."""
        return {
            "text_models": list(self.models.keys()),
            "embedding_models": list(self.embedding_models.keys())
        }


def get_llm_client() -> LLMClient:
    """Get an LLMClient instance."""
    return LLMClient()
