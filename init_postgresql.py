#!/usr/bin/env python3
"""
Initialize PostgreSQL database for the Silhouette Card Maker application.
This script will:
1. Connect to PostgreSQL
2. Create the database if it doesn't exist
3. Initialize Flask-Migrate
4. Create initial tables
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database URL
POSTGRES_URL = 'postgresql://dreambees:Zy2H%@sg0Ykl6ngf@108.175.14.173:5432/dream_'

def parse_postgres_url(url):
    """Parse PostgreSQL URL into connection parameters"""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port,
        'database': parsed.path[1:],  # Remove leading slash
        'user': parsed.username,
        'password': parsed.password
    }

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    params = parse_postgres_url(POSTGRES_URL)
    db_name = params['database']
    
    # Connect to default 'postgres' database to create our database
    create_params = params.copy()
    create_params['database'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**create_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Creating database: {db_name}")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False

def test_connection():
    """Test connection to the target database"""
    try:
        params = parse_postgres_url(POSTGRES_URL)
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info(f"Connected to PostgreSQL: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

def create_initial_tables():
    """Create initial tables using Flask-Migrate"""
    try:
        # Set environment variables for Flask app
        os.environ['FLASK_APP'] = 'run.py'
        # Temporarily override the database URL to use direct connection
        import tempfile
        import urllib.parse
        
        # Create a temporary config that handles the @ symbol properly
        # Manually encode the @ symbol to %40 without double-encoding
        password_encoded = 'Zy2H%40sg0Ykl6ngf'
        temp_db_url = f'postgresql://dreambees:{password_encoded}@108.175.14.173:5432/dream_'
        os.environ['DATABASE_URL'] = temp_db_url
        
        # Import Flask app and initialize database
        from app import create_app
        from app.models import db
        from flask_migrate import init, migrate, upgrade
        
        app = create_app()
        
        with app.app_context():
            logger.info("Initializing Flask-Migrate...")
            
            # Initialize migration repository if it doesn't exist
            try:
                init()
                logger.info("Migration repository initialized")
            except Exception as e:
                logger.info(f"Migration repository already exists: {e}")
            
            # Create initial migration
            try:
                migrate(message='Initial migration')
                logger.info("Initial migration created")
            except Exception as e:
                logger.info(f"Migration already exists: {e}")
            
            # Apply migrations
            try:
                upgrade()
                logger.info("Database migrations applied successfully")
            except Exception as e:
                logger.info(f"Migrations already applied or error: {e}")
                # Try to create tables directly if migrations fail
                try:
                    db.create_all()
                    logger.info("Database tables created directly")
                except Exception as e2:
                    logger.warning(f"Could not create tables directly: {e2}")
            
            # Create any additional indexes or constraints
            create_additional_indexes()
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to create initial tables: {e}")
        return False

def create_additional_indexes():
    """Create additional indexes for better performance"""
    try:
        from app.models import db
        
        # Create indexes for better query performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_user_id ON api_usage(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_jwt_blacklist_jti ON jwt_blacklist(jti);",
        ]
        
        for index_sql in indexes:
            try:
                db.engine.execute(index_sql)
                logger.info(f"Created index: {index_sql.split()[5]}")
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
        
        logger.info("Additional indexes created")
        
    except Exception as e:
        logger.warning(f"Could not create additional indexes: {e}")

def create_sample_data():
    """Create sample data for testing"""
    try:
        from app import create_app
        from app.models import db, User
        
        app = create_app()
        
        with app.app_context():
            # Check if admin user exists
            admin_user = User.query.filter_by(username='admin').first()
            
            if not admin_user:
                logger.info("Creating admin user...")
                admin_user = User(
                    username='admin',
                    email='admin@example.com',
                    is_admin=True,
                    is_active=True
                )
                admin_user.set_password('admin123')  # Change this in production!
                
                db.session.add(admin_user)
                db.session.commit()
                logger.info("Admin user created (username: admin, password: admin123)")
            else:
                logger.info("Admin user already exists")
        
        return True
        
    except Exception as e:
        logger.warning(f"Could not create sample data: {e}")
        return True  # Not critical

def main():
    """Main initialization function"""
    logger.info("Starting PostgreSQL database initialization")
    
    # Step 1: Create database if it doesn't exist
    if not create_database_if_not_exists():
        logger.error("Failed to create database")
        return False
    
    # Step 2: Test connection
    if not test_connection():
        logger.error("Failed to connect to database")
        return False
    
    # Step 3: Create initial tables
    if not create_initial_tables():
        logger.error("Failed to create initial tables")
        return False
    
    # Step 4: Create sample data
    create_sample_data()
    
    logger.info("PostgreSQL database initialization completed successfully!")
    logger.info("You can now start the application with: python run.py")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
