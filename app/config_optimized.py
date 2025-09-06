"""
Optimized configuration for the PDF generation API.
"""

import os
from datetime import timedelta


class OptimizedConfig:
    """Configuration class for optimized PDF generation"""
    
    # Basic Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # 100MB
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
    
    # Performance settings
    PDF_CACHE_SIZE_MB = int(os.environ.get('PDF_CACHE_SIZE_MB', 100))
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', 4))
    TASK_TIMEOUT_SECONDS = int(os.environ.get('TASK_TIMEOUT_SECONDS', 300))
    
    # Memory management
    MEMORY_WARNING_THRESHOLD = float(os.environ.get('MEMORY_WARNING_THRESHOLD', 80.0))
    MEMORY_CRITICAL_THRESHOLD = float(os.environ.get('MEMORY_CRITICAL_THRESHOLD', 90.0))
    
    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_HOUR = int(os.environ.get('RATE_LIMIT_REQUESTS_PER_HOUR', 1000))
    RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.environ.get('RATE_LIMIT_REQUESTS_PER_MINUTE', 100))
    RATE_LIMIT_PDF_GENERATION_PER_HOUR = int(os.environ.get('RATE_LIMIT_PDF_GENERATION_PER_HOUR', 50))
    
    # Redis settings for async tasks
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app_optimized.log')
    
    # API settings
    API_VERSION = '2.1.0'
    API_TITLE = 'Silhouette Card Maker API (Optimized)'
    API_DESCRIPTION = 'Optimized API for PDF generation with enhanced performance features'
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']
    
    # Security settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Plugin settings
    PLUGIN_GAMES = {
        'mtg': ['simple', 'mtga', 'mtgo', 'archidekt', 'deckstats', 'moxfield', 'scryfall_json'],
        'yugioh': ['ydke', 'ydk'],
        'lorcana': ['dreamborn'],
        'digimon': ['simple'],
        'flesh_and_blood': ['simple'],
        'grand_archive': ['simple'],
        'gundam': ['simple'],
        'netrunner': ['simple'],
        'one_piece': ['simple'],
        'riftbound': ['simple'],
        'altered': ['simple']
    }
    
    # Optimization settings
    ENABLE_CACHING = os.environ.get('ENABLE_CACHING', 'true').lower() == 'true'
    ENABLE_STREAMING = os.environ.get('ENABLE_STREAMING', 'true').lower() == 'true'
    ENABLE_ASYNC_GENERATION = os.environ.get('ENABLE_ASYNC_GENERATION', 'true').lower() == 'true'
    ENABLE_PARALLEL_PROCESSING = os.environ.get('ENABLE_PARALLEL_PROCESSING', 'true').lower() == 'true'
    
    # File processing settings
    TEMP_DIR_CLEANUP_DELAY = int(os.environ.get('TEMP_DIR_CLEANUP_DELAY', 30))  # seconds
    MAX_TEMP_FILES = int(os.environ.get('MAX_TEMP_FILES', 1000))
    
    # Monitoring settings
    ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
    METRICS_RETENTION_HOURS = int(os.environ.get('METRICS_RETENTION_HOURS', 24))
    
    # Development settings
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    TESTING = os.environ.get('TESTING', 'false').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        pass


class DevelopmentConfig(OptimizedConfig):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # More lenient limits for development
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    RATE_LIMIT_REQUESTS_PER_HOUR = 10000
    RATE_LIMIT_REQUESTS_PER_MINUTE = 1000


class ProductionConfig(OptimizedConfig):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    
    # Stricter limits for production
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    RATE_LIMIT_REQUESTS_PER_HOUR = 500
    RATE_LIMIT_REQUESTS_PER_MINUTE = 50
    
    # Enhanced security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(OptimizedConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use test PostgreSQL database for testing
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_test'
    
    # Disable caching and async for testing
    ENABLE_CACHING = False
    ENABLE_ASYNC_GENERATION = False
    
    # Fast cleanup for testing
    TEMP_DIR_CLEANUP_DELAY = 1


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': OptimizedConfig
}
