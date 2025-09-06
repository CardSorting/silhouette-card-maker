#!/usr/bin/env python3
"""
Migration script to move from SQLite to PostgreSQL.
This script will:
1. Connect to the existing SQLite database
2. Extract all data
3. Create tables in PostgreSQL
4. Import all data to PostgreSQL
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database URLs
SQLITE_DB_PATH = 'instance/app.db'
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

def get_sqlite_connection():
    """Get SQLite database connection"""
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database not found at {SQLITE_DB_PATH}")
        return None
    
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        logger.info("Connected to SQLite database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite: {e}")
        return None

def get_postgres_connection():
    """Get PostgreSQL database connection"""
    try:
        params = parse_postgres_url(POSTGRES_URL)
        conn = psycopg2.connect(**params)
        logger.info("Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None

def get_table_schema_sqlite(cursor, table_name):
    """Get table schema from SQLite"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    schema = []
    for col in columns:
        col_info = {
            'name': col[1],
            'type': col[2],
            'notnull': bool(col[3]),
            'default': col[4],
            'pk': bool(col[5])
        }
        schema.append(col_info)
    
    return schema

def convert_sqlite_type_to_postgres(sqlite_type):
    """Convert SQLite data types to PostgreSQL equivalents"""
    sqlite_type = sqlite_type.upper()
    
    if 'INTEGER' in sqlite_type or 'INT' in sqlite_type:
        return 'INTEGER'
    elif 'TEXT' in sqlite_type or 'VARCHAR' in sqlite_type:
        return 'TEXT'
    elif 'REAL' in sqlite_type or 'FLOAT' in sqlite_type or 'DOUBLE' in sqlite_type:
        return 'REAL'
    elif 'BLOB' in sqlite_type:
        return 'BYTEA'
    elif 'BOOLEAN' in sqlite_type or 'BOOL' in sqlite_type:
        return 'BOOLEAN'
    elif 'DATETIME' in sqlite_type or 'TIMESTAMP' in sqlite_type:
        return 'TIMESTAMP'
    else:
        return 'TEXT'  # Default fallback

def create_postgres_table(cursor, table_name, schema):
    """Create table in PostgreSQL based on SQLite schema"""
    
    # Build CREATE TABLE statement
    columns = []
    primary_keys = []
    
    for col in schema:
        col_def = f'"{col["name"]}" {convert_sqlite_type_to_postgres(col["type"])}'
        
        if col['notnull'] and not col['pk']:
            col_def += ' NOT NULL'
        
        if col['default'] is not None:
            if col['default'] == 'CURRENT_TIMESTAMP':
                col_def += ' DEFAULT CURRENT_TIMESTAMP'
            else:
                col_def += f" DEFAULT '{col['default']}'"
        
        columns.append(col_def)
        
        if col['pk']:
            primary_keys.append(f'"{col["name"]}"')
    
    # Add primary key constraint if exists
    if primary_keys:
        columns.append(f'PRIMARY KEY ({", ".join(primary_keys)})')
    
    columns_str = ",\n  ".join(columns)
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  {columns_str}\n)'
    
    try:
        cursor.execute(create_sql)
        logger.info(f"Created table {table_name} in PostgreSQL")
        return True
    except Exception as e:
        logger.error(f"Failed to create table {table_name}: {e}")
        return False

def migrate_table_data(sqlite_cursor, postgres_cursor, table_name):
    """Migrate data from SQLite table to PostgreSQL"""
    
    # Get all data from SQLite
    sqlite_cursor.execute(f'SELECT * FROM {table_name}')
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        logger.info(f"No data to migrate for table {table_name}")
        return True
    
    # Get column names
    columns = [description[0] for description in sqlite_cursor.description]
    
    # Prepare INSERT statement for PostgreSQL
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join([f'"{col}"' for col in columns])
    insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
    
    try:
        # Convert rows to list of tuples for PostgreSQL
        data_rows = []
        for row in rows:
            # Convert SQLite row to tuple, handling None values
            row_data = []
            for i, value in enumerate(row):
                if value is None:
                    row_data.append(None)
                else:
                    row_data.append(value)
            data_rows.append(tuple(row_data))
        
        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(data_rows), batch_size):
            batch = data_rows[i:i + batch_size]
            postgres_cursor.executemany(insert_sql, batch)
        
        logger.info(f"Migrated {len(data_rows)} rows to table {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to migrate data for table {table_name}: {e}")
        return False

def get_sqlite_tables(cursor):
    """Get list of tables from SQLite database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    return tables

def create_postgres_sequences(postgres_cursor):
    """Create sequences for auto-incrementing columns"""
    try:
        # Create sequence for user IDs if users table exists
        postgres_cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS users_id_seq;
            ALTER TABLE "users" ALTER COLUMN "id" SET DEFAULT nextval('users_id_seq');
            SELECT setval('users_id_seq', COALESCE(MAX(id), 1)) FROM "users";
        """)
        
        # Create sequence for other tables that might have auto-increment
        postgres_cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS api_usage_id_seq;
            ALTER TABLE "api_usage" ALTER COLUMN "id" SET DEFAULT nextval('api_usage_id_seq');
            SELECT setval('api_usage_id_seq', COALESCE(MAX(id), 1)) FROM "api_usage";
        """)
        
        logger.info("Created PostgreSQL sequences")
        return True
    except Exception as e:
        logger.warning(f"Could not create sequences (this is normal if tables don't exist): {e}")
        return True

def main():
    """Main migration function"""
    logger.info("Starting migration from SQLite to PostgreSQL")
    
    # Connect to databases
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        logger.error("Cannot proceed without SQLite connection")
        return False
    
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        logger.error("Cannot proceed without PostgreSQL connection")
        sqlite_conn.close()
        return False
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Get list of tables to migrate
        tables = get_sqlite_tables(sqlite_cursor)
        logger.info(f"Found {len(tables)} tables to migrate: {tables}")
        
        # Migrate each table
        success_count = 0
        for table_name in tables:
            logger.info(f"Migrating table: {table_name}")
            
            # Get table schema
            schema = get_table_schema_sqlite(sqlite_cursor, table_name)
            
            # Create table in PostgreSQL
            if create_postgres_table(postgres_cursor, table_name, schema):
                # Migrate data
                if migrate_table_data(sqlite_cursor, postgres_cursor, table_name):
                    success_count += 1
                else:
                    logger.error(f"Failed to migrate data for table {table_name}")
            else:
                logger.error(f"Failed to create table {table_name}")
        
        # Create sequences for auto-incrementing columns
        create_postgres_sequences(postgres_cursor)
        
        # Commit all changes
        postgres_conn.commit()
        
        logger.info(f"Migration completed successfully. {success_count}/{len(tables)} tables migrated.")
        
        # Verify migration
        logger.info("Verifying migration...")
        for table_name in tables:
            sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            sqlite_count = sqlite_cursor.fetchone()[0]
            
            postgres_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            postgres_count = postgres_cursor.fetchone()[0]
            
            if sqlite_count == postgres_count:
                logger.info(f"✓ Table {table_name}: {postgres_count} rows migrated")
            else:
                logger.warning(f"⚠ Table {table_name}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        postgres_conn.rollback()
        return False
        
    finally:
        sqlite_conn.close()
        postgres_conn.close()
        logger.info("Database connections closed")

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
