import logging
from typing import List, Tuple, Dict, Optional
import re
import torch
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """Service for semantic matching between user terms and database schema using embeddings"""

    def __init__(self, schema_elements: List[str]):
        logger.info("Loading embedding model (all-MiniLM-L6-v2)")
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        self.schema_elements = schema_elements
        # Precompute schema embeddings once for efficiency
        self.schema_embeddings = self.model.encode(schema_elements, convert_to_tensor=True)

    def find_semantic_matches(
        self, 
        user_terms: List[str], 
        threshold: float = 0.4, 
        top_k: int = 5
    ) -> Dict[str, List[Tuple[str, float]]]:
        """Find semantic matches between user terms and schema elements"""
        matches = {}

        for term in user_terms:
            term_emb = self.model.encode(term, convert_to_tensor=True)
            # Compute cosine similarity with schema embeddings
            cos_scores = util.cos_sim(term_emb, self.schema_embeddings)[0]

            # Rank schema elements by similarity
            top_results = torch.topk(cos_scores, k=min(top_k, len(self.schema_elements)))
            
            term_matches = []
            for score, idx in zip(top_results[0], top_results[1]):
                if score.item() >= threshold:  # filter low scores
                    term_matches.append((self.schema_elements[idx], score.item()))
            
            # If no match passes threshold, mark as NO_DATA_FOUND
            if not term_matches:
                term_matches.append(("NO_DATA_FOUND", 0.0))

            matches[term] = term_matches

        return matches

    def extract_semantic_terms(
        self, 
        question: str,
        station_names: Optional[List[str]] = None,
        weather_values: Optional[List[str]] = None,
        gender_values: Optional[List[str]] = None,
        station_emb_threshold: float = 0.75,
        enum_emb_threshold: float = 0.6
    ) -> List[str]:
        """Extract meaningful terms from user question for semantic matching.
        
        - Detects time phrases deterministically
        - Normalizes gender terms
        - Matches station/weather values from DB (substring or embedding fallback)
        - Falls back to generic tokens
        """
        question_lower = question.lower()
        seen = set()
        terms = []

        def add_term(t: str):
            key = t.lower()
            if key in seen:
                return
            seen.add(key)
            terms.append(t)

        # 1) Time phrases
        time_phrases = [
            'last month', 'this month', 'last year', 'this year',
            'last week', 'this week', 'june 2025', 'first week', 'second week',
            'third week', 'fourth week'
        ]
        for phrase in time_phrases:
            if phrase in question_lower:
                add_term(phrase)

        # 2) Station names (from DB)
        if station_names:
            # Substring match
            for s in station_names:
                if s.lower() in question_lower:
                    add_term(s)
            # Embedding fallback if nothing found
            if not any(s.lower() in question_lower for s in station_names):
                q_emb = self.model.encode(question_lower, convert_to_tensor=True)
                station_embs = self.model.encode(station_names, convert_to_tensor=True)
                scores = util.cos_sim(q_emb, station_embs)[0]
                topk = torch.topk(scores, k=min(3, len(station_names)))
                for score, idx in zip(topk[0], topk[1]):
                    if score.item() >= station_emb_threshold:
                        add_term(station_names[idx])

        # 3) Gender normalization
        gender_map = {
            'female': 'women', 'woman': 'women', 'women': 'women',
            'male': 'men', 'man': 'men', 'men': 'men'
        }
        gender_found = False
        for word in gender_map.keys():
            if re.search(rf'\b{re.escape(word)}\b', question_lower):
                normalized = gender_map[word]
                # Optionally map to DB values if gender_values provided
                if gender_values and normalized in gender_values:
                    add_term(normalized)
                # else:
                #     add_term(normalized)
                gender_found = True
        
        # **Do not map unknown gender terms**
        if not gender_found:
            # Skip adding anything for unknown terms like 'gays'
            pass

        # 4) Weather values
        if weather_values:
            for w in weather_values:
                if w.lower() in question_lower:
                    add_term(w)
            # Embedding fallback
            if not any(w.lower() in question_lower for w in weather_values):
                q_emb = self.model.encode(question_lower, convert_to_tensor=True)
                weather_embs = self.model.encode(weather_values, convert_to_tensor=True)
                scores = util.cos_sim(q_emb, weather_embs)[0]
                topk = torch.topk(scores, k=min(3, len(weather_values)))
                for score, idx in zip(topk[0], topk[1]):
                    if score.item() >= enum_emb_threshold:
                        add_term(weather_values[idx])

        # 5) Generic tokens
        stop_words = {
            'what', 'was', 'the', 'how', 'many', 'which', 'where', 'when', 'who',
            'is', 'are', 'were', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'across'
        }
        words = re.findall(r'\b\w+\b', question_lower)
        for w in words:
            if w not in stop_words and len(w) > 2:
                # Skip if already part of captured multi-word term
                if any(w in t.lower().split() for t in terms):
                    continue
                add_term(w)

        # **If no meaningful terms found, add NO_DATA_FOUND**
        if not terms:
            terms.append("NO_DATA_FOUND")

        return terms
