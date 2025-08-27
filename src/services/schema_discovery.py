import logging
import psycopg2
from typing import Dict, List, Any, Optional
from src.config import Config

logger = logging.getLogger(__name__)

class SchemaDiscoveryService:
    """Service for discovering and caching database schema information"""
    
    def __init__(self, config: Config):
        self.config = config
        self._schema_cache = None
        self._connection = None
    
    def get_connection(self):
        """Get database connection"""
        if not self._connection or self._connection.closed:
            try:
                self._connection = psycopg2.connect(
                    host=self.config.PGHOST,
                    user=self.config.PGUSER,
                    password=self.config.PGPASSWORD,
                    database=self.config.PGDATABASE,
                    port=self.config.PGPORT
                )
                # Set autocommit to avoid transaction issues
                self._connection.autocommit = True
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self._connection
    
    def discover_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Discover complete database schema"""
        if self._schema_cache and not force_refresh:
            return self._schema_cache
        
        logger.info("Discovering database schema...")
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            schema = {
                'tables': {},
                'relationships': [],
                'columns_by_table': {},
                'all_columns': []
            }
            
            # Get all tables
            cursor.execute("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            logger.info(f"Found {len(tables)} tables")
            
            for table_name, table_type in tables:
                schema['tables'][table_name] = {
                    'type': table_type,
                    'columns': []
                }
                
                # Get columns for each table
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        ordinal_position
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cursor.fetchall()
                column_list = []
                
                for col in columns:
                    column_info = {
                        'name': col[0],
                        'data_type': col[1],
                        'nullable': col[2] == 'YES',
                        'default': col[3],
                        'max_length': col[4],
                        'precision': col[5],
                        'position': col[6]
                    }
                    column_list.append(column_info)
                    schema['all_columns'].append(f"{table_name}.{col[0]}")
                
                schema['tables'][table_name]['columns'] = column_list
                schema['columns_by_table'][table_name] = [col['name'] for col in column_list]
            
            # Get foreign key relationships
            cursor.execute("""
                SELECT
                    tc.table_name as source_table,
                    kcu.column_name as source_column,
                    ccu.table_name as target_table,
                    ccu.column_name as target_column,
                    tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
            """)
            
            relationships = cursor.fetchall()
            for rel in relationships:
                schema['relationships'].append({
                    'source_table': rel[0],
                    'source_column': rel[1],
                    'target_table': rel[2],
                    'target_column': rel[3],
                    'constraint_name': rel[4]
                })
            
            cursor.close()
            self._schema_cache = schema
            logger.info(f"Schema discovery complete. Found {len(schema['tables'])} tables, {len(schema['relationships'])} relationships")
            
            return schema
            
        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            raise
    
    def get_schema_text(self) -> str:
        """Get schema as formatted text for LLM prompts"""
        schema = self.discover_schema()
        
        text_parts = ["DATABASE SCHEMA:\n"]
        
        for table_name, table_info in schema['tables'].items():
            text_parts.append(f"\nTable: {table_name}")
            text_parts.append("Columns:")
            
            for col in table_info['columns']:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                text_parts.append(f"  - {col['name']} ({col['data_type']}, {nullable})")
        
        if schema['relationships']:
            text_parts.append("\nFOREIGN KEY RELATIONSHIPS:")
            for rel in schema['relationships']:
                text_parts.append(f"  {rel['source_table']}.{rel['source_column']} references {rel['target_table']}.{rel['target_column']}")
        
        return "\n".join(text_parts)
    
    def get_all_columns(self) -> List[str]:
        """Get list of all columns across all tables"""
        schema = self.discover_schema()
        return schema['all_columns']
    
    def get_table_columns(self, table_name: str) -> Optional[List[str]]:
        """Get columns for a specific table"""
        schema = self.discover_schema()
        return schema['columns_by_table'].get(table_name)
    
    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")
