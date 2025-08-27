import unittest
from unittest.mock import Mock, patch, MagicMock
from src.config import Config
from src.services.schema_discovery import SchemaDiscoveryService

class TestSchemaDiscoveryService(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.PGHOST = 'test-host'
        self.config.PGUSER = 'test-user'
        self.config.PGPASSWORD = 'test-pass'
        self.config.PGDATABASE = 'test-db'
        self.config.PGPORT = '5432'
        
        self.service = SchemaDiscoveryService(self.config)
    
    @patch('src.services.schema_discovery.psycopg2.connect')
    def test_get_connection_success(self, mock_connect):
        """Test successful database connection"""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connection = self.service.get_connection()
        
        self.assertEqual(connection, mock_connection)
        mock_connect.assert_called_once_with(
            host='test-host',
            user='test-user',
            password='test-pass',
            database='test-db',
            port='5432'
        )
    
    @patch('src.services.schema_discovery.psycopg2.connect')
    def test_discover_schema_basic(self, mock_connect):
        """Test basic schema discovery"""
        # Mock database responses
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock table query response
        mock_cursor.fetchall.side_effect = [
            [('journeys', 'BASE TABLE'), ('stations', 'BASE TABLE')],  # tables
            [('id', 'integer', 'NO', None, None, None, 1), 
             ('start_time', 'timestamp', 'YES', None, None, None, 2)],  # journeys columns
            [('id', 'integer', 'NO', None, None, None, 1),
             ('name', 'character varying', 'YES', None, 50, None, 2)],  # stations columns
            []  # foreign keys
        ]
        
        schema = self.service.discover_schema()
        
        self.assertIn('tables', schema)
        self.assertIn('relationships', schema)
        self.assertIn('journeys', schema['tables'])
        self.assertIn('stations', schema['tables'])
        self.assertEqual(len(schema['tables']['journeys']['columns']), 2)
        self.assertEqual(len(schema['tables']['stations']['columns']), 2)
    
    def test_get_schema_text_format(self):
        """Test schema text formatting"""
        # Mock cached schema
        self.service._schema_cache = {
            'tables': {
                'journeys': {
                    'type': 'BASE TABLE',
                    'columns': [
                        {'name': 'id', 'data_type': 'integer', 'nullable': False},
                        {'name': 'start_time', 'data_type': 'timestamp', 'nullable': True}
                    ]
                }
            },
            'relationships': [
                {
                    'source_table': 'journeys',
                    'source_column': 'station_id',
                    'target_table': 'stations',
                    'target_column': 'id'
                }
            ]
        }
        
        schema_text = self.service.get_schema_text()
        
        self.assertIn('DATABASE SCHEMA:', schema_text)
        self.assertIn('Table: journeys', schema_text)
        self.assertIn('id (integer, NOT NULL)', schema_text)
        self.assertIn('start_time (timestamp, NULL)', schema_text)
        self.assertIn('FOREIGN KEY RELATIONSHIPS:', schema_text)
    
    def test_get_all_columns_from_cache(self):
        """Test getting all columns from cached schema"""
        self.service._schema_cache = {
            'all_columns': ['journeys.id', 'journeys.start_time', 'stations.id', 'stations.name']
        }
        
        columns = self.service.get_all_columns()
        
        self.assertEqual(len(columns), 4)
        self.assertIn('journeys.id', columns)
        self.assertIn('stations.name', columns)
    
    def test_get_table_columns(self):
        """Test getting columns for specific table"""
        self.service._schema_cache = {
            'columns_by_table': {
                'journeys': ['id', 'start_time', 'end_time'],
                'stations': ['id', 'name', 'latitude']
            }
        }
        
        journeys_columns = self.service.get_table_columns('journeys')
        stations_columns = self.service.get_table_columns('stations')
        missing_columns = self.service.get_table_columns('nonexistent')
        
        self.assertEqual(journeys_columns, ['id', 'start_time', 'end_time'])
        self.assertEqual(stations_columns, ['id', 'name', 'latitude'])
        self.assertIsNone(missing_columns)

if __name__ == '__main__':
    unittest.main()
