"""
Custom database configuration that handles PostgreSQL connection with @ symbol in password.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def create_postgresql_engine() -> Engine:
    """
    Create a PostgreSQL engine that handles the @ symbol in password correctly.
    """
    # Get connection parameters
    host = os.environ.get('DB_HOST', '108.175.14.173')
    port = os.environ.get('DB_PORT', '5432')
    database = os.environ.get('DB_NAME', 'dream_')
    user = os.environ.get('DB_USER', 'dreambees')
    password = os.environ.get('DB_PASSWORD', 'Zy2H%@sg0Ykl6ngf')
    
    # Create connection string with proper encoding
    # We need to manually encode the @ symbol to %40
    password_encoded = password.replace('@', '%40')
    connection_string = f'postgresql://{user}:{password_encoded}@{host}:{port}/{database}'
    
    # Create engine with custom connection parameters
    # Use connect_args to bypass URL parsing issues
    engine = create_engine(
        'postgresql://',  # Empty connection string
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        # Custom connect_args to handle password correctly
        connect_args={
            'host': host,
            'port': int(port),
            'dbname': database,  # Use 'dbname' instead of 'database'
            'user': user,
            'password': password  # Use original password, not encoded
        }
    )
    
    return engine


def get_database_uri() -> str:
    """
    Get the database URI for Flask-SQLAlchemy configuration.
    """
    # Check if we have individual connection parameters
    if os.environ.get('DB_HOST'):
        host = os.environ.get('DB_HOST', '108.175.14.173')
        port = os.environ.get('DB_PORT', '5432')
        database = os.environ.get('DB_NAME', 'dream_')
        user = os.environ.get('DB_USER', 'dreambees')
        password = os.environ.get('DB_PASSWORD', 'Zy2H%@sg0Ykl6ngf')
        
        # Build URI with proper encoding
        password_encoded = password.replace('@', '%40')
        return f'postgresql://{user}:{password_encoded}@{host}:{port}/{database}'
    
    # Fall back to environment variable or default
    return os.environ.get('DATABASE_URL') or 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_'
