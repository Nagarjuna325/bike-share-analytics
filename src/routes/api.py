import logging
from flask import Blueprint, request, jsonify
from src.config import Config
from src.services.nlp_to_sql import NLPToSQLService
from src.services.query_executor import QueryExecutor

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Initialize services
config = Config()
nlp_service = NLPToSQLService(config)
query_executor = QueryExecutor(config)

@api_bp.route('/query', methods=['POST'])
def handle_query():
    """Handle natural language query requests"""
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'sql': None,
                'result': None,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'sql': None,
                'result': None,
                'error': 'Question is required'
            }), 400
        
        logger.info(f"Processing question: {question}")
        
        # Generate SQL from natural language
        sql_result = nlp_service.generate_sql(question)
        
        if sql_result['error']:
            return jsonify({
                'sql': None,
                'result': None,
                'error': f"SQL generation failed: {sql_result['error']}"
            }), 400
        
        generated_sql = sql_result['sql']
        
        # Execute SQL query
        query_result = query_executor.execute_query(generated_sql)
        
        if not query_result['success']:
            return jsonify({
                'sql': generated_sql,
                'result': None,
                'error': query_result.get('error', 'Query execution failed')
            }), 500
        
        # Format result for user
        formatted_result = query_executor.format_result_for_user(query_result)
        
        # Return successful response
        response = {
            'sql': generated_sql,
            'result': formatted_result,
            'error': None,
            'metadata': {
                'row_count': query_result['row_count'],
                'columns': query_result['columns'],
                'semantic_matches': sql_result.get('semantic_matches', {}),
                'user_terms': sql_result.get('user_terms', [])
            }
        }
        
        logger.info(f"Query processed successfully. Returned {query_result['row_count']} rows")
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Internal server error: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            'sql': None,
            'result': None,
            'error': error_msg
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        query_result = query_executor.execute_query("SELECT 1 as health_check")
        
        if query_result['success']:
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'services': 'operational'
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': query_result.get('error')
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@api_bp.route('/schema', methods=['GET'])
def get_schema():
    """Get database schema information"""
    try:
        schema_text = nlp_service.schema_service.get_schema_text()
        all_columns = nlp_service.schema_service.get_all_columns()
        
        return jsonify({
            'schema_text': schema_text,
            'all_columns': all_columns,
            'tables': nlp_service.schema_service.discover_schema()['tables']
        })
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        return jsonify({
            'error': f"Failed to retrieve schema: {e}"
        }), 500
