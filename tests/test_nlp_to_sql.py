import unittest
from unittest.mock import Mock, patch, MagicMock
from src.config import Config
from src.services.nlp_to_sql import NLPToSQLService

class TestNLPToSQLService(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.GROQ_API_KEY = 'test-api-key'
        
        with patch('src.services.nlp_to_sql.SchemaDiscoveryService'), \
             patch('src.services.nlp_to_sql.SemanticMatcher'), \
             patch('src.services.nlp_to_sql.Groq'):
            self.service = NLPToSQLService(self.config)
    
    def test_validate_and_clean_sql_valid_select(self):
        """Test SQL validation with valid SELECT query"""
        valid_sql = "SELECT AVG(duration) FROM journeys WHERE start_time > '2025-01-01';"
        
        cleaned_sql = self.service._validate_and_clean_sql(valid_sql)
        
        self.assertEqual(cleaned_sql, "SELECT AVG(duration) FROM journeys WHERE start_time > '2025-01-01'")
    
    def test_validate_and_clean_sql_dangerous_keywords(self):
        """Test SQL validation rejects dangerous keywords"""
        dangerous_queries = [
            "DROP TABLE journeys;",
            "DELETE FROM journeys;",
            "INSERT INTO journeys VALUES (1, 2, 3);",
            "UPDATE journeys SET duration = 0;",
            "SELECT * FROM journeys; DROP TABLE stations;--"
        ]
        
        for query in dangerous_queries:
            with self.assertRaises(ValueError):
                self.service._validate_and_clean_sql(query)
    
    def test_validate_and_clean_sql_non_select(self):
        """Test SQL validation rejects non-SELECT queries"""
        non_select_query = "CREATE TABLE test (id INT);"
        
        with self.assertRaises(ValueError):
            self.service._validate_and_clean_sql(non_select_query)
    
    def test_validate_and_clean_sql_empty(self):
        """Test SQL validation rejects empty queries"""
        with self.assertRaises(ValueError):
            self.service._validate_and_clean_sql("")
        
        with self.assertRaises(ValueError):
            self.service._validate_and_clean_sql(None)
    
    @patch('src.services.nlp_to_sql.NLPToSQLService._generate_sql_with_llm')
    def test_generate_sql_success(self, mock_llm):
        """Test successful SQL generation"""
        # Mock dependencies
        self.service.schema_service.get_schema_text = Mock(return_value="Mock schema")
        self.service.semantic_matcher.extract_semantic_terms = Mock(return_value=['women', 'rainy'])
        self.service.schema_service.get_all_columns = Mock(return_value=['journeys.id', 'users.gender'])
        self.service.semantic_matcher.find_semantic_matches = Mock(return_value={
            'women': [('users.gender', 0.9)],
            'rainy': [('weather.condition', 0.8)]
        })
        
        mock_llm.return_value = "SELECT COUNT(*) FROM journeys j JOIN users u ON j.user_id = u.id WHERE u.gender = 'female'"
        self.service.groq_client = Mock()  # Ensure LLM path is taken
        
        result = self.service.generate_sql("How many women rode bikes?")
        
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['sql'])
        self.assertIn('SELECT', result['sql'])
    
    def test_build_semantic_context(self):
        """Test building semantic context from matches"""
        semantic_matches = {
            'women': [('users.gender', 0.9), ('riders.gender', 0.7)],
            'distance': [('journeys.distance_km', 0.95)],
            'empty': []
        }
        
        context = self.service._build_semantic_context(semantic_matches)
        
        self.assertIn("'women' ->", context)
        self.assertIn("users.gender (score: 0.90)", context)
        self.assertIn("'distance' ->", context)
        self.assertNotIn("'empty'", context)
    
    def test_generate_sql_fallback_average_ride_time(self):
        """Test fallback SQL generation for average ride time query"""
        self.service.groq_client = None  # Force fallback
        
        question = "What was the average ride time for journeys that started at Congress Avenue?"
        
        result = self.service._generate_sql_fallback(question, {})
        
        self.assertIn('AVG(duration', result)
        self.assertIn('Congress Avenue', result)
    
    def test_generate_sql_fallback_most_departures(self):
        """Test fallback SQL generation for most departures query"""
        self.service.groq_client = None  # Force fallback
        
        question = "Which station saw the most departures during the first week?"
        
        result = self.service._generate_sql_fallback(question, {})
        
        self.assertIn('COUNT(*)', result)
        self.assertIn('GROUP BY', result)
        self.assertIn('ORDER BY', result)
    
    def test_generate_sql_fallback_kilometres_women(self):
        """Test fallback SQL generation for kilometres by women query"""
        self.service.groq_client = None  # Force fallback
        
        question = "How many kilometres were ridden by women on rainy days?"
        
        result = self.service._generate_sql_fallback(question, {})
        
        self.assertIn('SUM(distance_km)', result)
        self.assertIn("gender = 'female'", result)
        self.assertIn('rain', result)
    
    def test_generate_sql_fallback_unknown_question(self):
        """Test fallback SQL generation for unknown question type"""
        self.service.groq_client = None  # Force fallback
        
        question = "What is the meaning of life?"
        
        with self.assertRaises(ValueError):
            self.service._generate_sql_fallback(question, {})

if __name__ == '__main__':
    unittest.main()
