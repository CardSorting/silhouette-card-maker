import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    
    # CORS configuration for Next.js frontend
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'txt', 'json'}
    
    # API configuration
    API_TITLE = 'Silhouette Card Maker API'
    API_VERSION = '2.0.0'
    API_DESCRIPTION = 'REST API for generating card PDFs with registration marks for silhouette cutting machines'
    
    # Rate limiting (requests per minute)
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per minute"
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Database configuration (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days
    JWT_ALGORITHM = 'HS256'
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Authentication configuration
    REQUIRE_AUTH = os.environ.get('REQUIRE_AUTH', 'false').lower() == 'true'
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    
    # Plugin games configuration
    PLUGIN_GAMES = {
        'mtg': ['simple', 'mtga', 'mtgo', 'archidekt', 'deckstats', 'moxfield', 'scryfall_json'],
        'yugioh': ['ydke', 'ydk'],
        'lorcana': ['dreamborn'],
        'riftbound': ['tts', 'pixelborn', 'piltover_archive'],
        'altered': ['ajordat'],
        'netrunner': ['text', 'bbcode', 'markdown', 'plain_text', 'jinteki'],
        'gundam': ['deckplanet', 'limitless', 'egman', 'exburst'],
        'grand_archive': ['omnideck'],
        'digimon': ['tts', 'digimoncardio', 'digimoncarddev', 'digimoncardapp', 'digimonmeta', 'untap'],
        'one_piece': ['optcgsim', 'egman'],
        'flesh_and_blood': ['fabrary']
    }


class DevelopmentConfig(Config):
    DEBUG = True
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:3001']


class ProductionConfig(Config):
    DEBUG = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    CORS_ORIGINS = ['http://localhost:3000']
    # Use test PostgreSQL database for testing
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_test'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}