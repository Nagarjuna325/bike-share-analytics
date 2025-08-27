import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database configuration
    PGHOST = os.getenv('PGHOST', 'localhost')
    PGUSER = os.getenv('PGUSER', 'postgres')
    PGPASSWORD = os.getenv('PGPASSWORD', '')
    PGDATABASE = os.getenv('PGDATABASE', 'bike_share')
    PGPORT = os.getenv('PGPORT', '5432')
    
    # Groq API configuration
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', 'default-groq-key')
    
    # Application settings
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    @property
    def database_url(self):
        """Construct PostgreSQL connection URL"""
        return f"postgresql://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        required_vars = ['PGHOST', 'PGUSER', 'PGPASSWORD', 'PGDATABASE', 'GROQ_API_KEY']
        missing = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
