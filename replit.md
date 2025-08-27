# Overview

This is a natural language bike-share analytics assistant that converts English questions into SQL queries using Groq LLM and dynamic semantic matching. The application provides a chat-style web interface where users can ask questions about bike share data in plain English, and the system automatically discovers the database schema, performs semantic matching between user terms and database columns, generates safe parameterized SQL queries, and returns formatted results.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Services Architecture

The application follows a modular service-oriented architecture with clear separation of concerns:

**Schema Discovery Service** (`src/services/schema_discovery.py`)
- Dynamically introspects PostgreSQL schema using `information_schema` queries
- Caches table structures, column types, and foreign key relationships to avoid repeated database calls
- Provides formatted schema context for LLM prompts
- Eliminates need for hardcoded schema definitions

**Semantic Matcher** (`src/services/semantic_matcher.py`) 
- Uses sentence-transformers (all-MiniLM-L6-v2 model) for embedding-based similarity matching
- Maps natural language terms to database columns without requiring hardcoded synonym lists
- Includes fallback keyword matching when embeddings are unavailable
- Configurable similarity thresholds and top-k matching

**NLP-to-SQL Service** (`src/services/nlp_to_sql.py`)
- Integrates with Groq LLM for natural language to SQL conversion
- Combines database schema context with semantic matches for accurate query generation
- Includes fallback rule-based generation for common bike share query patterns
- Validates generated SQL to prevent dangerous operations

**Query Executor** (`src/services/query_executor.py`)
- Executes parameterized SQL queries to prevent SQL injection
- Handles result formatting and error handling
- Provides user-friendly response generation

## Web Application Layer

**Flask Application** (`src/app.py`)
- Application factory pattern for clean configuration management
- Blueprint-based routing for API organization
- Centralized error handling for 404/500 errors

**REST API** (`src/routes/api.py`)
- Primary `/api/query` endpoint accepting JSON requests with natural language questions
- Returns structured responses with SQL query, results, and error information
- Comprehensive input validation and error handling

**Frontend Interface** (`src/templates/index.html`, `src/static/`)
- Chat-style UI built with Bootstrap 5 and custom CSS
- Real-time interaction with loading states and error handling
- Sample question examples for user guidance
- Responsive design for various screen sizes

## Configuration Management

**Environment-Based Configuration** (`src/config.py`)
- All database credentials and API keys loaded from environment variables
- Database URL construction and validation
- Support for development and production configurations
- Configuration validation to ensure required variables are present

## Testing Architecture

**Comprehensive Test Suite** (`tests/`)
- Unit tests for individual services with mocked dependencies
- Integration tests for the REST API endpoints
- Public acceptance tests for the three required query scenarios
- Pytest-compatible test structure with proper fixtures and mocking

# External Dependencies

## Database Integration
- **PostgreSQL**: Primary data store using psycopg2 driver for connection management
- **Database Schema**: Dynamic discovery through `information_schema` queries rather than static schema definitions

## AI/ML Services
- **Groq API**: Large Language Model integration for natural language to SQL conversion using the Groq Python SDK
- **Sentence Transformers**: Local embedding model (all-MiniLM-L6-v2) for semantic similarity matching between user terms and database columns

## Web Framework Stack
- **Flask**: Lightweight web framework for API endpoints and template rendering
- **Bootstrap 5**: Frontend CSS framework for responsive UI design
- **Font Awesome**: Icon library for enhanced user interface elements

## Development and Testing Tools
- **python-dotenv**: Environment variable management from .env files
- **unittest**: Python's built-in testing framework with mocking capabilities
- **pytest**: Alternative test runner support for more advanced testing features

## Optional Containerization
- **Docker**: Containerization support through included Dockerfile for deployment flexibility

The architecture prioritizes security through parameterized queries, maintainability through modular services, and flexibility through dynamic schema discovery and semantic matching without hardcoded mappings.