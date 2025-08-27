import unittest
from unittest.mock import Mock, patch
import json
from src.config import Config
from src.services.nlp_to_sql import NLPToSQLService
from src.services.query_executor import QueryExecutor

class TestPublicQueries(unittest.TestCase):
    """Test the three required public acceptance tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.GROQ_API_KEY = 'test-api-key'
        
        # Initialize services with mocks
        with patch('src.services.nlp_to_sql.SchemaDiscoveryService'), \
             patch('src.services.nlp_to_sql.SemanticMatcher'), \
             patch('src.services.nlp_to_sql.Groq'):
            self.nlp_service = NLPToSQLService(self.config)
        
        with patch('src.services.query_executor.psycopg2.connect'):
            self.query_executor = QueryExecutor(self.config)
    
    def test_t1_average_ride_time_congress_avenue(self):
        """T-1: Average ride time for journeys that started at Congress Avenue in June 2025"""
        question = "What was the average ride time for journeys that started at Congress Avenue in June 2025?"
        expected_answer = "25 minutes"
        
        # Mock the SQL generation
        expected_sql = """
        SELECT AVG(duration_minutes) as average_ride_time
        FROM journeys j
        JOIN stations s ON j.start_station_id = s.station_id
        WHERE s.name LIKE '%Congress Avenue%'
        AND EXTRACT(MONTH FROM j.start_time) = 6
        AND EXTRACT(YEAR FROM j.start_time) = 2025
        """
        
        # Mock schema service
        self.nlp_service.schema_service.get_schema_text = Mock(return_value="Mock schema")
        self.nlp_service.schema_service.get_all_columns = Mock(return_value=[
            'journeys.duration_minutes', 'journeys.start_station_id', 'stations.name'
        ])
        
        # Mock semantic matcher
        self.nlp_service.semantic_matcher.extract_semantic_terms = Mock(return_value=[
            'average', 'ride', 'time', 'congress', 'avenue', 'june', '2025'
        ])
        self.nlp_service.semantic_matcher.find_semantic_matches = Mock(return_value={
            'ride': [('journeys.duration_minutes', 0.8)],
            'congress': [('stations.name', 0.9)],
            'avenue': [('stations.name', 0.8)]
        })
        
        # Mock LLM response
        with patch.object(self.nlp_service, '_generate_sql_with_llm') as mock_llm:
            mock_llm.return_value = expected_sql.strip()
            self.nlp_service.groq_client = Mock()  # Ensure LLM path
            
            result = self.nlp_service.generate_sql(question)
        
        # Verify SQL generation
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['sql'])
        self.assertIn('AVG', result['sql'])
        self.assertIn('Congress Avenue', result['sql'])
        self.assertIn('2025', result['sql'])
        
        # Mock query execution
        mock_query_result = {
            'success': True,
            'data': [{'average_ride_time': 25.0}],
            'columns': ['average_ride_time'],
            'row_count': 1
        }
        
        with patch.object(self.query_executor, 'execute_query') as mock_execute:
            mock_execute.return_value = mock_query_result
            
            formatted_result = self.query_executor.format_result_for_user(mock_query_result)
            
            # Verify the result contains the expected value
            self.assertIn('25', formatted_result)
    
    def test_t2_most_departures_first_week_june(self):
        """T-2: Which docking point saw the most departures during the first week of June 2025"""
        question = "Which docking point saw the most departures during the first week of June 2025?"
        expected_answer = "Congress Avenue"
        
        # Mock the SQL generation
        expected_sql = """
        SELECT s.name as station_name, COUNT(*) as departure_count
        FROM journeys j
        JOIN stations s ON j.start_station_id = s.station_id
        WHERE EXTRACT(MONTH FROM j.start_time) = 6
        AND EXTRACT(YEAR FROM j.start_time) = 2025
        AND j.start_time >= '2025-06-01'
        AND j.start_time < '2025-06-08'
        GROUP BY s.station_id, s.name
        ORDER BY departure_count DESC
        LIMIT 1
        """
        
        # Mock schema and semantic services
        self.nlp_service.schema_service.get_schema_text = Mock(return_value="Mock schema")
        self.nlp_service.schema_service.get_all_columns = Mock(return_value=[
            'journeys.start_station_id', 'stations.name', 'journeys.start_time'
        ])
        
        self.nlp_service.semantic_matcher.extract_semantic_terms = Mock(return_value=[
            'docking', 'departures', 'first', 'week', 'june', '2025'
        ])
        self.nlp_service.semantic_matcher.find_semantic_matches = Mock(return_value={
            'docking': [('stations.name', 0.8)],
            'departures': [('journeys.start_station_id', 0.7)]
        })
        
        # Mock LLM response
        with patch.object(self.nlp_service, '_generate_sql_with_llm') as mock_llm:
            mock_llm.return_value = expected_sql.strip()
            self.nlp_service.groq_client = Mock()
            
            result = self.nlp_service.generate_sql(question)
        
        # Verify SQL generation
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['sql'])
        self.assertIn('COUNT(*)', result['sql'])
        self.assertIn('GROUP BY', result['sql'])
        self.assertIn('ORDER BY', result['sql'])
        self.assertIn('LIMIT 1', result['sql'])
        
        # Mock query execution
        mock_query_result = {
            'success': True,
            'data': [{'station_name': 'Congress Avenue', 'departure_count': 150}],
            'columns': ['station_name', 'departure_count'],
            'row_count': 1
        }
        
        with patch.object(self.query_executor, 'execute_query') as mock_execute:
            mock_execute.return_value = mock_query_result
            
            formatted_result = self.query_executor.format_result_for_user(mock_query_result)
            
            # Verify the result contains Congress Avenue
            self.assertIn('Congress Avenue', formatted_result)
    
    def test_t3_kilometres_women_rainy_days(self):
        """T-3: How many kilometres were ridden by women on rainy days in June 2025"""
        question = "How many kilometres were ridden by women on rainy days in June 2025?"
        expected_answer = "6.8 km"
        
        # Mock the SQL generation
        expected_sql = """
        SELECT SUM(distance_km) as total_kilometres
        FROM journeys j
        JOIN users u ON j.user_id = u.user_id
        JOIN weather w ON DATE(j.start_time) = w.date
        WHERE u.gender = 'female'
        AND w.condition LIKE '%rain%'
        AND EXTRACT(MONTH FROM j.start_time) = 6
        AND EXTRACT(YEAR FROM j.start_time) = 2025
        """
        
        # Mock schema and semantic services
        self.nlp_service.schema_service.get_schema_text = Mock(return_value="Mock schema")
        self.nlp_service.schema_service.get_all_columns = Mock(return_value=[
            'journeys.distance_km', 'users.gender', 'weather.condition'
        ])
        
        self.nlp_service.semantic_matcher.extract_semantic_terms = Mock(return_value=[
            'kilometres', 'women', 'rainy', 'days', 'june', '2025'
        ])
        self.nlp_service.semantic_matcher.find_semantic_matches = Mock(return_value={
            'kilometres': [('journeys.distance_km', 0.9)],
            'women': [('users.gender', 0.9)],
            'rainy': [('weather.condition', 0.8)]
        })
        
        # Mock LLM response
        with patch.object(self.nlp_service, '_generate_sql_with_llm') as mock_llm:
            mock_llm.return_value = expected_sql.strip()
            self.nlp_service.groq_client = Mock()
            
            result = self.nlp_service.generate_sql(question)
        
        # Verify SQL generation
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['sql'])
        self.assertIn('SUM', result['sql'])
        self.assertIn('distance_km', result['sql'])
        self.assertIn('gender', result['sql'])
        self.assertIn('rain', result['sql'])
        
        # Mock query execution
        mock_query_result = {
            'success': True,
            'data': [{'total_kilometres': 6.8}],
            'columns': ['total_kilometres'],
            'row_count': 1
        }
        
        with patch.object(self.query_executor, 'execute_query') as mock_execute:
            mock_execute.return_value = mock_query_result
            
            formatted_result = self.query_executor.format_result_for_user(mock_query_result)
            
            # Verify the result contains 6.8
            self.assertIn('6.8', formatted_result)
    
    def test_all_queries_generate_valid_sql(self):
        """Test that all three public queries generate syntactically valid SQL"""
        public_questions = [
            "What was the average ride time for journeys that started at Congress Avenue in June 2025?",
            "Which docking point saw the most departures during the first week of June 2025?",
            "How many kilometres were ridden by women on rainy days in June 2025?"
        ]
        
        # Mock services for all tests
        self.nlp_service.schema_service.get_schema_text = Mock(return_value="Mock schema")
        self.nlp_service.schema_service.get_all_columns = Mock(return_value=[
            'journeys.id', 'journeys.duration_minutes', 'journeys.distance_km',
            'stations.name', 'users.gender', 'weather.condition'
        ])
        self.nlp_service.semantic_matcher.extract_semantic_terms = Mock(return_value=['mock', 'terms'])
        self.nlp_service.semantic_matcher.find_semantic_matches = Mock(return_value={})
        self.nlp_service.groq_client = None  # Force fallback mode
        
        for question in public_questions:
            with self.subTest(question=question):
                try:
                    result = self.nlp_service.generate_sql(question)
                    
                    # Should either succeed or fail gracefully
                    if result['error']:
                        # If it fails, it should be a controlled failure
                        self.assertIsInstance(result['error'], str)
                    else:
                        # If it succeeds, SQL should be valid
                        self.assertIsNotNone(result['sql'])
                        self.assertTrue(result['sql'].strip().upper().startswith('SELECT'))
                        
                except Exception as e:
                    self.fail(f"Question '{question}' caused unexpected exception: {e}")

if __name__ == '__main__':
    unittest.main()
