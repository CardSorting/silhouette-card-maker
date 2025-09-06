"""
PostgreSQL-specific configuration that handles the @ symbol in password correctly.
"""

import os
from app.config import Config


class PostgreSQLConfig(Config):
    """Configuration class specifically for PostgreSQL with @ symbol in password"""
    
    # Override database configuration to use direct connection parameters
    def __init__(self):
        super().__init__()
        
        # Use direct connection parameters instead of URL to avoid @ symbol issues
        self.SQLALCHEMY_DATABASE_URI = self._build_postgresql_uri()
    
    def _build_postgresql_uri(self):
        """Build PostgreSQL URI using direct parameters"""
        # Check if we have individual connection parameters
        if os.environ.get('DB_HOST'):
            host = os.environ.get('DB_HOST', '108.175.14.173')
            port = os.environ.get('DB_PORT', '5432')
            database = os.environ.get('DB_NAME', 'dream_')
            user = os.environ.get('DB_USER', 'dreambees')
            password = os.environ.get('DB_PASSWORD', 'Zy2H%@sg0Ykl6ngf')
            
            # Build URI with proper encoding (manually encode @ to %40)
            password_encoded = password.replace('@', '%40')
            return f'postgresql://{user}:{password_encoded}@{host}:{port}/{database}'
        
        # Fall back to environment variable or default
        return os.environ.get('DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_'


class DevelopmentPostgreSQLConfig(PostgreSQLConfig):
    """Development configuration with PostgreSQL"""
    DEBUG = True
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:3001']


class ProductionPostgreSQLConfig(PostgreSQLConfig):
    """Production configuration with PostgreSQL"""
    DEBUG = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []


class TestingPostgreSQLConfig(PostgreSQLConfig):
    """Testing configuration with PostgreSQL"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    CORS_ORIGINS = ['http://localhost:3000']
    
    def _build_postgresql_uri(self):
        """Use test database for testing"""
        if os.environ.get('DB_HOST'):
            host = os.environ.get('DB_HOST', '108.175.14.173')
            port = os.environ.get('DB_PORT', '5432')
            database = os.environ.get('TEST_DB_NAME', 'dream_test')
            user = os.environ.get('DB_USER', 'dreambees')
            password = os.environ.get('DB_PASSWORD', 'Zy2H%@sg0Ykl6ngf')
            
            password_encoded = password.replace('@', '%40')
            return f'postgresql://{user}:{password_encoded}@{host}:{port}/{database}'
        
        return os.environ.get('TEST_DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_test'


# Configuration mapping
postgresql_config = {
    'development': DevelopmentPostgreSQLConfig,
    'production': ProductionPostgreSQLConfig,
    'testing': TestingPostgreSQLConfig,
    'default': PostgreSQLConfig
}
