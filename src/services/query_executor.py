import logging
import psycopg2
from typing import Dict, Any, List, Optional, Tuple
from src.config import Config

logger = logging.getLogger(__name__)

class QueryExecutor:
    """Service for safely executing SQL queries against the database"""
    
    def __init__(self, config: Config):
        self.config = config
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
                logger.info("Query executor database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self._connection
    
    def execute_query(self, sql_query: str, parameters: Optional[Tuple] = None) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            logger.info(f"Executing query: {sql_query}")
            if parameters:
                logger.info(f"With parameters: {parameters}")
            
            # Execute query with parameters for safety
            cursor.execute(sql_query, parameters or ())
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch results
            results = cursor.fetchall()
            
            # Format results
            if not results:
                return {
                    'success': True,
                    'data': [],
                    'columns': columns,
                    'row_count': 0,
                    'message': 'No data found matching your criteria'
                }
            
            # Convert to list of dictionaries
            formatted_results = []
            for row in results:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[columns[i]] = value
                formatted_results.append(row_dict)
            
            logger.info(f"Query executed successfully. Returned {len(results)} rows")
            
            return {
                'success': True,
                'data': formatted_results,
                'columns': columns,
                'row_count': len(results),
                'message': f'Query executed successfully. Found {len(results)} result(s)'
            }
            
        except psycopg2.Error as e:
            error_msg = f"Database error: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'data': [],
                'columns': [],
                'row_count': 0,
                'error': error_msg
            }
        
        except Exception as e:
            error_msg = f"Query execution error: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'data': [],
                'columns': [],
                'row_count': 0,
                'error': error_msg
            }
        
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
    
    def format_result_for_user(self, query_result: Dict[str, Any]) -> str:
        """Format query result into human-readable text"""
        if not query_result['success']:
            return f"Error: {query_result.get('error', 'Unknown error occurred')}"
        
        if query_result['row_count'] == 0:
            return "No data available for your query."
        
        data = query_result['data']
        
        # Handle single value results (aggregations)
        if len(data) == 1 and len(data[0]) == 1:
            value = list(data[0].values())[0]
            if isinstance(value, (int, float)):
                return f"Result: {value}"
            else:
                return f"Result: {value}"
        
        # Handle single row with multiple columns
        if len(data) == 1:
            row = data[0]
            parts = []
            for key, value in row.items():
                parts.append(f"{key}: {value}")
            return ", ".join(parts)
        
        # Handle multiple rows - return formatted table
        if len(data) <= 10:  # Show all rows if <= 10
            formatted_rows = []
            for row in data:
                row_parts = []
                for key, value in row.items():
                    row_parts.append(f"{key}: {value}")
                formatted_rows.append(" | ".join(row_parts))
            return "\n".join(formatted_rows)
        else:
            # Show first 10 rows + summary
            formatted_rows = []
            for i, row in enumerate(data[:10]):
                row_parts = []
                for key, value in row.items():
                    row_parts.append(f"{key}: {value}")
                formatted_rows.append(" | ".join(row_parts))
            
            formatted_rows.append(f"... and {len(data) - 10} more rows")
            return "\n".join(formatted_rows)
    
    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Query executor database connection closed")
