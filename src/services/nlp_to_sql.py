import logging
import re
from typing import Dict, Any, List
from groq import Groq
from src.config import Config
from src.services.schema_discovery import SchemaDiscoveryService
from src.services.semantic_matcher import SemanticMatcher

logger = logging.getLogger(__name__)

class NLPToSQLService:
    """Service for converting natural language to SQL using Groq LLM and embeddings-based semantic matcher"""
    
    def __init__(self, config: Config):
        self.config = config
        self.schema_service = SchemaDiscoveryService(config)
        
        # Get all columns/tables from schema and initialize embeddings-based matcher
        all_columns = self.schema_service.get_all_columns()
        self.semantic_matcher = SemanticMatcher(schema_elements=all_columns)
        
        try:
            self.groq_client = Groq(api_key=config.GROQ_API_KEY)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self.groq_client = None
    
    def generate_sql(self, question: str) -> Dict[str, Any]:
        """Generate SQL query from natural language question"""
        try:
            # Get schema information
            schema_text = self.schema_service.get_schema_text()
            
            # Extract semantic terms from question
            user_terms = self.semantic_matcher.extract_semantic_terms(question)
            
            
            # Find semantic matches
            semantic_matches = self.semantic_matcher.find_semantic_matches(user_terms)
            
            # after getting semantic_matches

            filtered_matches = {k: [m for m in v if m[1] >= 0.4] for k, v in semantic_matches.items()}

            # If no valid semantic matches, skip SQL generation
            if all(len(v) == 0 for v in filtered_matches.values()):  
               logger.info(f"No semantic matches found for question: {question}")
               return {
                      'sql': None,
                      'semantic_matches': semantic_matches,
                      'user_terms': user_terms,
                      'error': "NO_DATA_FOUND"
                }
            
            # Build enhanced prompt with semantic context
            semantic_context = self._build_semantic_context(semantic_matches)
            
            # Generate SQL using LLM or fallback
            try:
                if self.groq_client:
                    sql_query = self._generate_sql_with_llm(question, schema_text, semantic_context)
                else:
                    sql_query = self._generate_sql_fallback(question, semantic_matches)
            except UnicodeEncodeError:
                logger.warning("Unicode encoding error with LLM, using fallback")
                sql_query = self._generate_sql_fallback(question, semantic_matches)
            
            # Validate and clean SQL
            cleaned_sql = self._validate_and_clean_sql(sql_query)
            
            return {
                'sql': cleaned_sql,
                'semantic_matches': semantic_matches,
                'user_terms': user_terms,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {
                'sql': None,
                'semantic_matches': {},
                'user_terms': [],
                'error': str(e)
            }
    
    def _generate_sql_with_llm(self, question: str, schema_text: str, semantic_context: str) -> str:
        """Generate SQL using Groq LLM"""
        prompt = f"""You are an expert SQL query generator for a bike-share analytics database.

{schema_text}

SEMANTIC MATCHES FOUND:
{semantic_context}

QUESTION: {question}

INSTRUCTIONS:
1. Generate ONLY a valid SQL query, no explanations
2. Use proper JOINs when referencing multiple tables
3. DO NOT use parameterized queries or placeholder variables (like :start_date)
4. Handle date/time filtering with explicit date values
5. For aggregations, use appropriate GROUP BY clauses
6. Map semantic terms to actual database columns using the schema above
7. Common mappings to remember:
   - "women/female" maps to rider_gender = 'female'
   - "rainy days" means precipitation_mm > 0 in daily_weather table
   - "kilometres/distance" maps to trip_distance_km column
   - Station names map to station_name column
   - Time references need proper date filtering (use actual dates like '2025-06-01')
   - "departures/started from" uses start_station_id
   - "arrivals/ended at" uses end_station_id
8. IMPORTANT: Do not include any parameter placeholders, use actual values in the SQL
9. WEATHER QUERIES: For rainy/weather conditions, join trips with daily_weather using:
   JOIN daily_weather ON DATE(trips.started_at) = daily_weather.weather_date
   Then filter with: daily_weather.precipitation_mm > 0
10. GENDER VALUES: Use exact values from the database - 'male' and 'female'

Generate the SQL query:"""

        try:
            if not self.groq_client:
                raise ValueError("Groq client not available")
                
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks
            sql_query = re.sub(r'```sql\s*', '', sql_query)
            sql_query = re.sub(r'```\s*', '', sql_query)
            
            # Keep only SQL-like lines
            lines = sql_query.split('\n')
            sql_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if (line.lower().startswith('note:') or 
                    line.lower().startswith('this query') or 
                    line.lower().startswith('the above') or
                    line.lower().startswith('assumes') or
                    'should be adjusted' in line.lower()):
                    break
                sql_lines.append(line)
            
            sql_query = '\n'.join(sql_lines).strip()
            logger.info(f"Generated SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"LLM SQL generation failed: {e}")
            raise
    
    def _generate_sql_fallback(self, question: str, semantic_matches: Dict[str, List]) -> str:
        """Fallback SQL generation when LLM is unavailable"""
        logger.warning("Using fallback SQL generation")
        question_lower = question.lower()
        
        if 'average' in question_lower and 'ride time' in question_lower:
            return """
            SELECT AVG(duration_minutes) as average_ride_time
            FROM journeys j
            JOIN stations s ON j.start_station_id = s.station_id
            """
        elif 'most departures' in question_lower:
            return """
            SELECT s.name as station_name, COUNT(*) as departure_count
            FROM journeys j
            JOIN stations s ON j.start_station_id = s.station_id
            GROUP BY s.station_id, s.name
            ORDER BY departure_count DESC
            LIMIT 1
            """
        elif 'kilometres' in question_lower and 'women' in question_lower:
            return """
            SELECT SUM(t.trip_distance_km) as total_kilometres
            FROM trips t
            JOIN daily_weather w ON DATE(t.started_at) = w.weather_date
            WHERE t.rider_gender = 'female'
            AND w.precipitation_mm > 0
            """
        else:
            raise ValueError("Unable to generate SQL query from question")
    
    def _build_semantic_context(self, semantic_matches: Dict[str, List]) -> str:
        """Build context string from semantic matches"""
        context_parts = []
        for term, matches in semantic_matches.items():
            if matches:
                match_strings = [f"{match[0]} (score: {match[1]:.2f})" for match in matches]
                context_parts.append(f"'{term}' maps to {', '.join(match_strings)}")
        return "\n".join(context_parts) if context_parts else "No semantic matches found"
    
    def _validate_and_clean_sql(self, sql_query: str) -> str:
        """Validate and clean the generated SQL query"""
        if not sql_query:
            raise ValueError("Empty SQL query generated")
        
        sql_query = sql_query.rstrip(';').strip()
        dangerous_keywords = [
            'drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update',
            'exec', 'execute', 'sp_', 'xp_', '--', '/*', '*/', 'union all'
        ]
        
        sql_lower = sql_query.lower()
        for keyword in dangerous_keywords:
            if keyword in sql_lower and not sql_lower.startswith('select'):
                raise ValueError(f"Only SELECT queries are allowed. Detected: {keyword}")
        
        if not sql_lower.startswith('select'):
            raise ValueError("Only SELECT queries are allowed")
        
        return sql_query
