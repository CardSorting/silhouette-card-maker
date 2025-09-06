#!/usr/bin/env python3
"""
Clear PostgreSQL database prior to migration.
This script will:
1. Connect to PostgreSQL
2. Drop all existing tables and data
3. Clean up sequences and indexes
4. Prepare for fresh migration
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

def get_database_connection():
    """Get PostgreSQL database connection"""
    try:
        params = parse_postgres_url(POSTGRES_URL)
        conn = psycopg2.connect(**params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None

def get_existing_tables(cursor):
    """Get list of existing tables in the database"""
    try:
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%'
            AND tablename NOT LIKE 'sql_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    except Exception as e:
        logger.error(f"Failed to get table list: {e}")
        return []

def get_existing_sequences(cursor):
    """Get list of existing sequences in the database"""
    try:
        cursor.execute("""
            SELECT sequencename 
            FROM pg_sequences 
            WHERE schemaname = 'public'
        """)
        sequences = [row[0] for row in cursor.fetchall()]
        return sequences
    except Exception as e:
        logger.error(f"Failed to get sequence list: {e}")
        return []

def clear_database(cursor):
    """Clear all tables and data from the database"""
    try:
        # Get existing tables
        tables = get_existing_tables(cursor)
        sequences = get_existing_sequences(cursor)
        
        if not tables and not sequences:
            logger.info("Database is already empty")
            return True
        
        logger.info(f"Found {len(tables)} tables and {len(sequences)} sequences to clear")
        
        # Drop all tables (CASCADE will handle foreign key constraints)
        if tables:
            logger.info("Dropping all tables...")
            for table in tables:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                    logger.info(f"Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"Could not drop table {table}: {e}")
        
        # Drop all sequences
        if sequences:
            logger.info("Dropping all sequences...")
            for sequence in sequences:
                try:
                    cursor.execute(f'DROP SEQUENCE IF EXISTS "{sequence}" CASCADE')
                    logger.info(f"Dropped sequence: {sequence}")
                except Exception as e:
                    logger.warning(f"Could not drop sequence {sequence}: {e}")
        
        # Clean up any remaining objects
        logger.info("Cleaning up remaining objects...")
        cleanup_queries = [
            "DROP SCHEMA IF EXISTS public CASCADE",
            "CREATE SCHEMA public",
            "GRANT ALL ON SCHEMA public TO postgres",
            "GRANT ALL ON SCHEMA public TO public"
        ]
        
        for query in cleanup_queries:
            try:
                cursor.execute(query)
                logger.info(f"Executed: {query}")
            except Exception as e:
                logger.warning(f"Could not execute '{query}': {e}")
        
        logger.info("Database cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        return False

def verify_database_empty(cursor):
    """Verify that the database is completely empty"""
    try:
        # Check for tables
        tables = get_existing_tables(cursor)
        sequences = get_existing_sequences(cursor)
        
        if tables:
            logger.warning(f"Warning: {len(tables)} tables still exist: {tables}")
            return False
        
        if sequences:
            logger.warning(f"Warning: {len(sequences)} sequences still exist: {sequences}")
            return False
        
        logger.info("✓ Database is completely empty")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify database state: {e}")
        return False

def main():
    """Main function to clear the database"""
    logger.info("Starting PostgreSQL database clearing process")
    logger.warning("⚠️  WARNING: This will delete ALL data in the database!")
    
    # Ask for confirmation
    if not os.environ.get('FORCE_CLEAR'):
        response = input("Are you sure you want to clear the database? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("Database clearing cancelled by user")
            return False
    
    # Connect to database
    conn = get_database_connection()
    if not conn:
        logger.error("Cannot proceed without database connection")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Clear the database
        if clear_database(cursor):
            # Verify it's empty
            if verify_database_empty(cursor):
                logger.info("🎉 Database cleared successfully!")
                logger.info("The database is now ready for fresh migration.")
                return True
            else:
                logger.error("Database clearing may not have completed successfully")
                return False
        else:
            logger.error("Failed to clear database")
            return False
            
    except Exception as e:
        logger.error(f"Database clearing failed: {e}")
        return False
        
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
