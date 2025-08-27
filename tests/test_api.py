import unittest
from unittest.mock import Mock, patch
import json
from src.app import create_app
from src.config import Config

class TestAPI(unittest.TestCase):
    """Test the REST API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Mock the services to avoid actual database connections
        self.patcher1 = patch('src.routes.api.nlp_service')
        self.patcher2 = patch('src.routes.api.query_executor')
        
        self.mock_nlp_service = self.patcher1.start()
        self.mock_query_executor = self.patcher2.start()
    
    def tearDown(self):
        """Clean up patches"""
        self.patcher1.stop()
        self.patcher2.stop()
    
    def test_query_endpoint_success(self):
        """Test successful query processing"""
        # Mock successful SQL generation
        self.mock_nlp_service.generate_sql.return_value = {
            'sql': 'SELECT COUNT(*) FROM journeys',
            'error': None,
            'semantic_matches': {'test': [('journeys.id', 0.9)]},
            'user_terms': ['test']
        }
        
        # Mock successful query execution
        self.mock_query_executor.execute_query.return_value = {
            'success': True,
            'data': [{'count': 100}],
            'columns': ['count'],
            'row_count': 1
        }
        
        self.mock_query_executor.format_result_for_user.return_value = "Result: 100"
        
        # Send request
        response = self.client.post('/api/query',
                                  data=json.dumps({'question': 'How many journeys?'}),
                                  content_type='application/json')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsNone(data['error'])
        self.assertEqual(data['sql'], 'SELECT COUNT(*) FROM journeys')
        self.assertEqual(data['result'], 'Result: 100')
        self.assertIn('metadata', data)
    
    def test_query_endpoint_missing_question(self):
        """Test query endpoint with missing question"""
        response = self.client.post('/api/query',
                                  data=json.dumps({}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIsNotNone(data['error'])
        self.assertIn('Question is required', data['error'])
    
    def test_query_endpoint_empty_question(self):
        """Test query endpoint with empty question"""
        response = self.client.post('/api/query',
                                  data=json.dumps({'question': '   '}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIsNotNone(data['error'])
    
    def test_query_endpoint_invalid_json(self):
        """Test query endpoint with invalid JSON"""
        response = self.client.post('/api/query',
                                  data='invalid json',
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIsNotNone(data['error'])
    
    def test_query_endpoint_sql_generation_error(self):
        """Test query endpoint when SQL generation fails"""
        # Mock SQL generation failure
        self.mock_nlp_service.generate_sql.return_value = {
            'sql': None,
            'error': 'Unable to understand the question',
            'semantic_matches': {},
            'user_terms': []
        }
        
        response = self.client.post('/api/query',
                                  data=json.dumps({'question': 'Invalid question'}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIsNotNone(data['error'])
        self.assertIn('SQL generation failed', data['error'])
    
    def test_query_endpoint_database_error(self):
        """Test query endpoint when database query fails"""
        # Mock successful SQL generation
        self.mock_nlp_service.generate_sql.return_value = {
            'sql': 'SELECT * FROM nonexistent_table',
            'error': None,
            'semantic_matches': {},
            'user_terms': []
        }
        
        # Mock database failure
        self.mock_query_executor.execute_query.return_value = {
            'success': False,
            'error': 'Table does not exist',
            'data': [],
            'columns': [],
            'row_count': 0
        }
        
        response = self.client.post('/api/query',
                                  data=json.dumps({'question': 'Select from bad table'}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertIsNotNone(data['error'])
        self.assertIn('Table does not exist', data['error'])
    
    def test_health_endpoint_success(self):
        """Test health check endpoint when healthy"""
        # Mock successful health check
        self.mock_query_executor.execute_query.return_value = {
            'success': True,
            'data': [{'health_check': 1}],
            'columns': ['health_check'],
            'row_count': 1
        }
        
        response = self.client.get('/api/health')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')
    
    def test_health_endpoint_database_failure(self):
        """Test health check endpoint when database is down"""
        # Mock database failure
        self.mock_query_executor.execute_query.return_value = {
            'success': False,
            'error': 'Connection refused',
            'data': [],
            'columns': [],
            'row_count': 0
        }
        
        response = self.client.get('/api/health')
        
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'unhealthy')
        self.assertEqual(data['database'], 'disconnected')
    
    def test_schema_endpoint_success(self):
        """Test schema endpoint returns schema information"""
        # Mock schema service responses
        mock_schema_service = Mock()
        mock_schema_service.get_schema_text.return_value = "Mock schema text"
        mock_schema_service.get_all_columns.return_value = ['table1.col1', 'table2.col2']
        mock_schema_service.discover_schema.return_value = {
            'tables': {
                'table1': {'columns': [{'name': 'col1', 'type': 'integer'}]}
            }
        }
        
        self.mock_nlp_service.schema_service = mock_schema_service
        
        response = self.client.get('/api/schema')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('schema_text', data)
        self.assertIn('all_columns', data)
        self.assertIn('tables', data)
    
    def test_query_endpoint_with_example_questions(self):
        """Test the three example questions through the API"""
        example_questions = [
            "What was the average ride time for journeys that started at Congress Avenue in June 2025?",
            "Which docking point saw the most departures during the first week of June 2025?",
            "How many kilometres were ridden by women on rainy days in June 2025?"
        ]
        
        for question in example_questions:
            with self.subTest(question=question):
                # Mock successful responses
                self.mock_nlp_service.generate_sql.return_value = {
                    'sql': 'SELECT mock_result FROM mock_table',
                    'error': None,
                    'semantic_matches': {},
                    'user_terms': []
                }
                
                self.mock_query_executor.execute_query.return_value = {
                    'success': True,
                    'data': [{'result': 'mock_value'}],
                    'columns': ['result'],
                    'row_count': 1
                }
                
                self.mock_query_executor.format_result_for_user.return_value = "Mock result"
                
                response = self.client.post('/api/query',
                                          data=json.dumps({'question': question}),
                                          content_type='application/json')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIsNone(data['error'])
                self.assertIsNotNone(data['sql'])
                self.assertIsNotNone(data['result'])

if __name__ == '__main__':
    unittest.main()
