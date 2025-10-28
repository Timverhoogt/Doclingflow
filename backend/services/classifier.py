"""
Document classification service for petrochemical industry documents.

This service provides specialized classification for petrochemical storage terminal
documents using LLM-based classification with industry-specific categories and prompts.
"""

import logging
from typing import Dict, List, Optional

from backend.core.config import get_settings
from backend.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Service for classifying petrochemical industry documents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm_client = get_llm_client()
        
        # Petrochemical-specific document categories
        self.categories = {
            "safety": {
                "name": "Safety Documents",
                "description": "Safety data sheets, MSDS, hazard sheets, safety procedures",
                "keywords": ["safety", "hazard", "msds", "sds", "emergency", "risk", "danger", "toxic", "flammable"]
            },
            "technical": {
                "name": "Technical Specifications",
                "description": "Equipment specs, datasheets, technical drawings, engineering documents",
                "keywords": ["specification", "datasheet", "technical", "engineering", "drawing", "design", "capacity"]
            },
            "business": {
                "name": "Business Documents",
                "description": "Invoices, contracts, purchase orders, financial reports",
                "keywords": ["invoice", "contract", "purchase", "order", "financial", "payment", "cost", "price"]
            },
            "equipment": {
                "name": "Equipment Manuals",
                "description": "Maintenance manuals, operation procedures, equipment documentation",
                "keywords": ["manual", "maintenance", "operation", "procedure", "equipment", "tank", "pump", "valve"]
            },
            "regulatory": {
                "name": "Regulatory Compliance",
                "description": "Permits, certificates, compliance reports, regulatory documentation",
                "keywords": ["permit", "certificate", "compliance", "regulatory", "inspection", "audit", "license"]
            },
            "operational": {
                "name": "Operational Procedures",
                "description": "SOPs, work instructions, operational guidelines, process documentation",
                "keywords": ["sop", "procedure", "instruction", "guideline", "process", "operation", "work"]
            },
            "environmental": {
                "name": "Environmental Documents",
                "description": "Environmental impact assessments, waste management, emissions reports",
                "keywords": ["environmental", "emission", "waste", "pollution", "impact", "assessment", "sustainability"]
            },
            "quality": {
                "name": "Quality Control",
                "description": "Quality assurance, testing reports, inspection records, certifications",
                "keywords": ["quality", "testing", "inspection", "assurance", "certification", "standard", "control"]
            }
        }
        
        # Category mapping for API responses
        self.category_list = list(self.categories.keys())
    
    async def classify_document(self, text_content: str, filename: Optional[str] = None) -> Dict:
        """
        Classify a document into petrochemical industry categories.
        
        Args:
            text_content: Document text content
            filename: Optional filename for additional context
            
        Returns:
            Dictionary with classification results
        """
        try:
            logger.info(f"Classifying document: {filename or 'unknown'}")
            
            # Create specialized petrochemical classification prompt
            prompt = self._create_classification_prompt(text_content, filename)
            
            # Use LLM for classification
            result = await self.llm_client.classify_document(
                text_content=text_content,
                categories=self.category_list,
                model=self.settings.llm.default_model
            )
            
            if not result["success"]:
                logger.error(f"Classification failed: {result.get('error', 'Unknown error')}")
                return self._create_fallback_classification(text_content, filename)
            
            # Enhance classification with additional analysis
            enhanced_result = await self._enhance_classification(
                text_content, result, filename
            )
            
            logger.info(f"Document classified as: {enhanced_result['category']} "
                       f"(confidence: {enhanced_result['confidence']:.2f})")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            return self._create_fallback_classification(text_content, filename)
    
    def _create_classification_prompt(self, text_content: str, filename: Optional[str] = None) -> str:
        """Create a specialized prompt for petrochemical document classification."""
        
        # Build category descriptions
        category_descriptions = []
        for cat_id, cat_info in self.categories.items():
            desc = f"- {cat_id}: {cat_info['description']}"
            category_descriptions.append(desc)
        
        categories_text = "\n".join(category_descriptions)
        
        # Add filename context if available
        filename_context = ""
        if filename:
            filename_context = f"\nFilename: {filename}"
        
        prompt = f"""
You are an expert document classifier for petrochemical storage terminals. 
Analyze the following document and classify it into the most appropriate category.

Available categories:
{categories_text}

Document content{filename_context}:
{text_content[:4000]}...

Consider the following factors:
1. Document purpose and content type
2. Industry-specific terminology and context
3. Regulatory requirements and compliance aspects
4. Safety implications and hazard information
5. Technical specifications and equipment details
6. Business operations and financial aspects

Respond with JSON format:
{{
    "category": "selected_category",
    "confidence": 0.95,
    "reasoning": "detailed explanation of classification decision",
    "keywords_found": ["keyword1", "keyword2"],
    "subcategory": "optional_more_specific_type"
}}
"""
        
        return prompt
    
    async def _enhance_classification(
        self, 
        text_content: str, 
        initial_result: Dict, 
        filename: Optional[str] = None
    ) -> Dict:
        """Enhance classification with additional analysis."""
        
        try:
            # Extract additional metadata
            category_info = self.categories.get(initial_result["category"], {})
            
            # Check for keyword matches
            keywords_found = []
            for keyword in category_info.get("keywords", []):
                if keyword.lower() in text_content.lower():
                    keywords_found.append(keyword)
            
            # Determine subcategory if applicable
            subcategory = self._determine_subcategory(
                text_content, 
                initial_result["category"], 
                filename
            )
            
            # Calculate enhanced confidence based on keyword matches
            keyword_boost = min(len(keywords_found) * 0.05, 0.2)  # Max 20% boost
            enhanced_confidence = min(initial_result["confidence"] + keyword_boost, 1.0)
            
            return {
                "category": initial_result["category"],
                "category_name": category_info.get("name", initial_result["category"]),
                "confidence": enhanced_confidence,
                "reasoning": initial_result.get("reasoning", ""),
                "keywords_found": keywords_found,
                "subcategory": subcategory,
                "filename_hint": filename,
                "metadata": initial_result.get("metadata", {}),
                "success": True
            }
            
        except Exception as e:
            logger.warning(f"Error enhancing classification: {e}")
            return initial_result
    
    def _determine_subcategory(
        self, 
        text_content: str, 
        category: str, 
        filename: Optional[str] = None
    ) -> Optional[str]:
        """Determine a more specific subcategory based on content analysis."""
        
        text_lower = text_content.lower()
        filename_lower = filename.lower() if filename else ""
        
        # Safety subcategories
        if category == "safety":
            if any(word in text_lower for word in ["msds", "sds", "safety data"]):
                return "safety_data_sheet"
            elif any(word in text_lower for word in ["emergency", "evacuation", "response"]):
                return "emergency_procedures"
            elif any(word in text_lower for word in ["hazard", "risk", "danger"]):
                return "hazard_assessment"
        
        # Technical subcategories
        elif category == "technical":
            if any(word in text_lower for word in ["datasheet", "specification", "spec"]):
                return "equipment_specification"
            elif any(word in text_lower for word in ["drawing", "blueprint", "diagram"]):
                return "technical_drawing"
            elif any(word in text_lower for word in ["engineering", "design", "calculation"]):
                return "engineering_document"
        
        # Equipment subcategories
        elif category == "equipment":
            if any(word in text_lower for word in ["maintenance", "repair", "service"]):
                return "maintenance_manual"
            elif any(word in text_lower for word in ["operation", "operating", "startup"]):
                return "operation_manual"
            elif any(word in text_lower for word in ["tank", "storage", "vessel"]):
                return "storage_equipment"
        
        # Business subcategories
        elif category == "business":
            if any(word in text_lower for word in ["invoice", "bill", "charge"]):
                return "invoice"
            elif any(word in text_lower for word in ["contract", "agreement", "terms"]):
                return "contract"
            elif any(word in text_lower for word in ["purchase", "order", "po"]):
                return "purchase_order"
        
        # Regulatory subcategories
        elif category == "regulatory":
            if any(word in text_lower for word in ["permit", "license", "authorization"]):
                return "permit"
            elif any(word in text_lower for word in ["certificate", "certification", "compliance"]):
                return "certificate"
            elif any(word in text_lower for word in ["inspection", "audit", "review"]):
                return "inspection_report"
        
        return None
    
    def _create_fallback_classification(
        self, 
        text_content: str, 
        filename: Optional[str] = None
    ) -> Dict:
        """Create a fallback classification when LLM classification fails."""
        
        try:
            # Simple keyword-based classification
            text_lower = text_content.lower()
            filename_lower = filename.lower() if filename else ""
            
            category_scores = {}
            
            for cat_id, cat_info in self.categories.items():
                score = 0
                for keyword in cat_info["keywords"]:
                    if keyword.lower() in text_lower:
                        score += 1
                    if filename and keyword.lower() in filename_lower:
                        score += 2  # Higher weight for filename matches
                
                category_scores[cat_id] = score
            
            # Find best category
            best_category = max(category_scores, key=category_scores.get)
            confidence = min(category_scores[best_category] * 0.1, 0.8)  # Max 80% confidence
            
            if confidence < 0.3:
                best_category = "business"  # Default fallback
                confidence = 0.3
            
            category_info = self.categories[best_category]
            
            return {
                "category": best_category,
                "category_name": category_info["name"],
                "confidence": confidence,
                "reasoning": f"Fallback classification based on keyword matching",
                "keywords_found": [kw for kw in category_info["keywords"] if kw.lower() in text_lower],
                "subcategory": None,
                "filename_hint": filename,
                "metadata": {"method": "fallback"},
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in fallback classification: {e}")
            return {
                "category": "business",
                "category_name": "Business Documents",
                "confidence": 0.1,
                "reasoning": "Classification failed, using default category",
                "keywords_found": [],
                "subcategory": None,
                "filename_hint": filename,
                "metadata": {"method": "default", "error": str(e)},
                "success": False
            }
    
    def get_categories(self) -> Dict:
        """Get available document categories."""
        return {
            "categories": self.categories,
            "category_list": self.category_list
        }
    
    def get_category_info(self, category: str) -> Optional[Dict]:
        """Get information about a specific category."""
        return self.categories.get(category)


def get_document_classifier() -> DocumentClassifier:
    """Get a DocumentClassifier instance."""
    return DocumentClassifier()
