#!/usr/bin/env python3
"""
Test the custom database engine with PostgreSQL.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_custom_database_engine():
    """Test the custom database engine"""
    try:
        # Set connection parameters
        os.environ['DB_HOST'] = '108.175.14.173'
        os.environ['DB_PORT'] = '5432'
        os.environ['DB_NAME'] = 'dream_'
        os.environ['DB_USER'] = 'dreambees'
        os.environ['DB_PASSWORD'] = 'Zy2H%@sg0Ykl6ngf'
        
        # Import and test the custom engine
        from app.database import create_postgresql_engine, get_database_uri
        
        logger.info("Testing custom database engine...")
        
        # Test URI generation
        uri = get_database_uri()
        logger.info(f"Generated URI: {uri}")
        
        # Test engine creation
        engine = create_postgresql_engine()
        logger.info("✓ Custom engine created successfully")
        
        # Test connection
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            if result and result[0] == 1:
                logger.info("✓ Database connection successful")
            else:
                logger.error("✗ Database connection test failed")
                return False
        
        # Test table operations
        with engine.connect() as conn:
            # Check if tables exist
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'pg_%'
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"✓ Found {len(tables)} tables: {tables}")
        
        logger.info("🎉 Custom database engine test successful!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Custom database engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_custom_database_engine()
    sys.exit(0 if success else 1)
