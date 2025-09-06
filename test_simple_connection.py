#!/usr/bin/env python3
"""
Simple test to verify PostgreSQL connection works with the application.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_connection():
    """Test simple connection without SQLAlchemy"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host='108.175.14.173',
            port=5432,
            database='dream_',
            user='dreambees',
            password='Zy2H%@sg0Ykl6ngf'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info(f"✓ Connected to PostgreSQL: {version}")
        
        # Test basic operations
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        if result and result[0] == 1:
            logger.info("✓ Basic query works")
        
        # Check if tables exist
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"✓ Found {len(tables)} tables: {tables}")
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 PostgreSQL connection test successful!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_simple_connection()
    sys.exit(0 if success else 1)
