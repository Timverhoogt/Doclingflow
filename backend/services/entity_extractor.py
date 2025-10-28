"""
Entity extraction service for petrochemical industry documents.

This service extracts specific entities from petrochemical documents including
equipment IDs, chemical names, locations, personnel, and measurements.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from backend.core.config import get_settings
from backend.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Service for extracting entities from petrochemical documents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm_client = get_llm_client()
        
        # Petrochemical-specific entity types
        self.entity_types = {
            "equipment_id": {
                "name": "Equipment ID",
                "description": "Equipment identifiers, tank numbers, pump IDs, valve tags",
                "patterns": [
                    r'\bT-\d{3,4}\b',  # Tank numbers like T-001, T-1234
                    r'\bP-\d{3,4}\b',  # Pump numbers like P-001
                    r'\bV-\d{3,4}\b',  # Valve numbers like V-001
                    r'\bTK-\d{3,4}\b', # Tank codes
                    r'\bPUMP-\d{3,4}\b', # Pump codes
                    r'\bVALVE-\d{3,4}\b', # Valve codes
                    r'\b[A-Z]{2,3}-\d{3,4}\b', # General equipment codes
                ]
            },
            "chemical_name": {
                "name": "Chemical Name",
                "description": "Chemical compounds, product names, material names",
                "patterns": [
                    r'\b[A-Z][a-z]+\s+(?:Acid|Chloride|Sulfate|Nitrate|Oxide)\b',
                    r'\b(?:Benzene|Toluene|Xylene|Ethylene|Propylene|Butane|Propane)\b',
                    r'\b[A-Z][a-z]+\s+(?:Oil|Fuel|Gas|Liquid|Solution)\b',
                ]
            },
            "location": {
                "name": "Location",
                "description": "Facility names, terminal locations, storage areas",
                "patterns": [
                    r'\b(?:Terminal|Facility|Plant|Station|Depot)\s+[A-Z][a-z]+\b',
                    r'\b(?:Tank|Storage|Loading|Unloading)\s+(?:Area|Zone|Section)\b',
                    r'\b[A-Z][a-z]+\s+(?:Terminal|Facility|Plant)\b',
                ]
            },
            "personnel": {
                "name": "Personnel",
                "description": "Names of personnel, operators, supervisors",
                "patterns": [
                    r'\b(?:Mr\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
                    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:Operator|Supervisor|Manager|Engineer)\b',
                ]
            },
            "measurement": {
                "name": "Measurement",
                "description": "Quantities, volumes, pressures, temperatures",
                "patterns": [
                    r'\b\d+(?:\.\d+)?\s*(?:m³|L|gal|barrel|ton|kg|lb|psi|bar|°C|°F)\b',
                    r'\b(?:Volume|Capacity|Pressure|Temperature):\s*\d+(?:\.\d+)?\s*\w+\b',
                ]
            },
            "date_time": {
                "name": "Date/Time",
                "description": "Dates, timestamps, schedules",
                "patterns": [
                    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
                    r'\b\d{4}-\d{2}-\d{2}\b',
                ]
            },
            "safety_info": {
                "name": "Safety Information",
                "description": "Safety classifications, hazard levels, emergency contacts",
                "patterns": [
                    r'\b(?:NFPA|OSHA|DOT)\s+\d+\b',
                    r'\b(?:Flammable|Toxic|Corrosive|Reactive)\s+(?:Class|Category)\s+\d+\b',
                    r'\bEmergency\s+(?:Contact|Phone|Number):\s*\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                ]
            },
            "certificate_number": {
                "name": "Certificate Number",
                "description": "Certificate IDs, permit numbers, inspection codes",
                "patterns": [
                    r'\b(?:Cert|Certificate|Permit|License)\s*#?\s*[A-Z0-9-]{5,20}\b',
                    r'\b[A-Z]{2,4}\d{6,12}\b',  # General certificate format
                ]
            }
        }
    
    async def extract_entities(self, text_content: str, filename: Optional[str] = None) -> Dict:
        """
        Extract entities from document text using both pattern matching and LLM.
        
        Args:
            text_content: Document text content
            filename: Optional filename for additional context
            
        Returns:
            Dictionary with extracted entities organized by type
        """
        try:
            logger.info(f"Extracting entities from document: {filename or 'unknown'}")
            
            # First, use pattern matching for known entity types
            pattern_entities = self._extract_with_patterns(text_content)
            
            # Then, use LLM for more complex entity extraction
            llm_entities = await self._extract_with_llm(text_content, filename)
            
            # Combine and deduplicate results
            combined_entities = self._combine_entities(pattern_entities, llm_entities)
            
            # Add metadata and context
            result = {
                "entities": combined_entities,
                "entity_counts": {entity_type: len(entities) for entity_type, entities in combined_entities.items()},
                "total_entities": sum(len(entities) for entities in combined_entities.values()),
                "extraction_methods": {
                    "pattern_matching": len(pattern_entities),
                    "llm_extraction": len(llm_entities)
                },
                "filename": filename,
                "success": True
            }
            
            logger.info(f"Extracted {result['total_entities']} entities across {len(combined_entities)} types")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {
                "entities": {},
                "entity_counts": {},
                "total_entities": 0,
                "error": str(e),
                "success": False
            }
    
    def _extract_with_patterns(self, text_content: str) -> Dict[str, List[Dict]]:
        """Extract entities using regex patterns."""
        entities = {entity_type: [] for entity_type in self.entity_types.keys()}
        
        for entity_type, entity_info in self.entity_types.items():
            for pattern in entity_info["patterns"]:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                
                for match in matches:
                    entity = {
                        "text": match.group(),
                        "type": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "context": self._get_context(text_content, match.start(), match.end()),
                        "method": "pattern_matching",
                        "confidence": 0.9  # High confidence for pattern matches
                    }
                    entities[entity_type].append(entity)
        
        return entities
    
    async def _extract_with_llm(self, text_content: str, filename: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Extract entities using LLM."""
        try:
            # Truncate text if too long
            max_length = 6000
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "..."
            
            # Create entity extraction prompt
            entity_types_str = ", ".join([f"{et}: {info['description']}" for et, info in self.entity_types.items()])
            
            prompt = f"""
Extract the following types of entities from this petrochemical industry document:

Entity types to extract:
{entity_types_str}

Document content:
{text_content}

For each entity found, provide:
- The exact text
- The entity type
- Character position (start and end)
- Surrounding context (50 characters before and after)
- Confidence level (0.0 to 1.0)

Format your response as JSON:
{{
    "entities": [
        {{
            "text": "exact_entity_text",
            "type": "entity_type",
            "start": 123,
            "end": 135,
            "context": "surrounding context text",
            "confidence": 0.95
        }}
    ]
}}
"""
            
            system_prompt = """You are an expert entity extraction system for petrochemical industry documents. 
            Extract entities accurately and provide precise character positions and context."""
            
            result = await self.llm_client.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            if not result["success"]:
                logger.warning(f"LLM entity extraction failed: {result.get('error', 'Unknown error')}")
                return {}
            
            # Parse JSON response
            try:
                import json
                llm_result = json.loads(result["text"])
                
                # Organize by entity type
                entities = {entity_type: [] for entity_type in self.entity_types.keys()}
                
                for entity in llm_result.get("entities", []):
                    entity_type = entity.get("type")
                    if entity_type in self.entity_types:
                        entity["method"] = "llm_extraction"
                        entities[entity_type].append(entity)
                
                return entities
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Error parsing LLM entity extraction response: {e}")
                return {}
            
        except Exception as e:
            logger.error(f"Error in LLM entity extraction: {e}")
            return {}
    
    def _combine_entities(
        self, 
        pattern_entities: Dict[str, List[Dict]], 
        llm_entities: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """Combine and deduplicate entities from different extraction methods."""
        
        combined = {entity_type: [] for entity_type in self.entity_types.keys()}
        
        for entity_type in self.entity_types.keys():
            # Start with pattern-matched entities
            combined[entity_type] = pattern_entities.get(entity_type, []).copy()
            
            # Add LLM entities, avoiding duplicates
            llm_entities_for_type = llm_entities.get(entity_type, [])
            
            for llm_entity in llm_entities_for_type:
                # Check for duplicates based on text and position
                is_duplicate = False
                for existing_entity in combined[entity_type]:
                    if (existing_entity["text"].lower() == llm_entity["text"].lower() and
                        abs(existing_entity["start"] - llm_entity["start"]) < 10):
                        is_duplicate = True
                        # Update confidence if LLM has higher confidence
                        if llm_entity["confidence"] > existing_entity["confidence"]:
                            existing_entity["confidence"] = llm_entity["confidence"]
                            existing_entity["method"] = "combined"
                        break
                
                if not is_duplicate:
                    combined[entity_type].append(llm_entity)
        
        # Sort entities by position in document
        for entity_type in combined:
            combined[entity_type].sort(key=lambda x: x["start"])
        
        return combined
    
    def _get_context(self, text: str, start: int, end: int, context_length: int = 50) -> str:
        """Get surrounding context for an entity."""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        context = text[context_start:context_end]
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
        
        return context
    
    def get_entity_types(self) -> Dict:
        """Get available entity types."""
        return {
            "entity_types": self.entity_types,
            "entity_type_list": list(self.entity_types.keys())
        }
    
    def get_entity_type_info(self, entity_type: str) -> Optional[Dict]:
        """Get information about a specific entity type."""
        return self.entity_types.get(entity_type)
    
    def validate_entity(self, entity: Dict) -> bool:
        """Validate an extracted entity."""
        required_fields = ["text", "type", "start", "end", "confidence"]
        
        for field in required_fields:
            if field not in entity:
                return False
        
        if entity["type"] not in self.entity_types:
            return False
        
        if not isinstance(entity["confidence"], (int, float)) or not (0 <= entity["confidence"] <= 1):
            return False
        
        if entity["start"] < 0 or entity["end"] <= entity["start"]:
            return False
        
        return True


def get_entity_extractor() -> EntityExtractor:
    """Get an EntityExtractor instance."""
    return EntityExtractor()
