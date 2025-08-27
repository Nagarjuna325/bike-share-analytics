import logging
from typing import List, Tuple, Dict, Any
import re

logger = logging.getLogger(__name__)

class SemanticMatcher:
    """Service for semantic matching between user terms and database schema"""
    
    def __init__(self):
        # Using keyword matching only for better compatibility
        logger.info("Using keyword-based semantic matching")
        self.model = None
    
    def find_semantic_matches(self, user_terms: List[str], schema_elements: List[str], 
                             threshold: float = 0.3, top_k: int = 3) -> Dict[str, List[Tuple[str, float]]]:
        """Find semantic matches between user terms and schema elements"""
        # Always use keyword fallback since we don't have the ML model
        return self._keyword_fallback(user_terms, schema_elements)
    
    def _keyword_fallback(self, user_terms: List[str], schema_elements: List[str]) -> Dict[str, List[Tuple[str, float]]]:
        """Fallback keyword-based matching when semantic model fails"""
        matches = {}
        
        for term in user_terms:
            term_lower = term.lower()
            term_matches = []
            
            for element in schema_elements:
                element_lower = element.lower()
                
                # Exact match
                if term_lower == element_lower:
                    term_matches.append((element, 1.0))
                # Substring match
                elif term_lower in element_lower or element_lower in term_lower:
                    score = min(len(term_lower), len(element_lower)) / max(len(term_lower), len(element_lower))
                    term_matches.append((element, score))
                # Word boundary match
                elif re.search(rf'\b{re.escape(term_lower)}\b', element_lower):
                    term_matches.append((element, 0.8))
            
            # Sort by score and take top 3
            term_matches.sort(key=lambda x: x[1], reverse=True)
            matches[term] = term_matches[:3]
        
        return matches
    
    def extract_semantic_terms(self, question: str) -> List[str]:
        """Extract meaningful terms from user question for semantic matching"""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            'what', 'was', 'the', 'how', 'many', 'which', 'where', 'when', 'who',
            'is', 'are', 'were', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'across'
        }
        
        # Extract words and phrases
        words = re.findall(r'\b\w+\b', question.lower())
        
        # Filter out stop words and short words
        meaningful_terms = []
        for word in words:
            if word not in stop_words and len(word) > 2:
                meaningful_terms.append(word)
        
        # Also extract common multi-word patterns
        question_lower = question.lower()
        
        # Time-related phrases
        time_phrases = [
            'last month', 'this month', 'last year', 'this year',
            'last week', 'this week', 'june 2025', 'rainy days',
            'first week', 'second week', 'third week', 'fourth week'
        ]
        
        for phrase in time_phrases:
            if phrase in question_lower:
                meaningful_terms.append(phrase)
        
        # Location/station related
        if 'congress avenue' in question_lower:
            meaningful_terms.append('congress avenue')
        
        # Gender related
        if 'women' in question_lower or 'female' in question_lower:
            meaningful_terms.append('women')
        if 'men' in question_lower or 'male' in question_lower:
            meaningful_terms.append('men')
        
        # Weather related
        weather_terms = ['rainy', 'sunny', 'cloudy', 'weather']
        for term in weather_terms:
            if term in question_lower:
                meaningful_terms.append(term)
        
        return list(set(meaningful_terms))  # Remove duplicates
