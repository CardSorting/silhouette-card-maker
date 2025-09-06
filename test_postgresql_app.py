#!/usr/bin/env python3
"""
Test the Flask application with PostgreSQL configuration.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_app_with_postgresql():
    """Test the Flask application with PostgreSQL"""
    try:
        # Set individual connection parameters
        os.environ['DB_HOST'] = '108.175.14.173'
        os.environ['DB_PORT'] = '5432'
        os.environ['DB_NAME'] = 'dream_'
        os.environ['DB_USER'] = 'dreambees'
        os.environ['DB_PASSWORD'] = 'Zy2H%@sg0Ykl6ngf'
        
        # Import and create app with PostgreSQL config
        from app.config_postgresql import PostgreSQLConfig
        from app import create_app
        from app.models import db
        
        # Create app with PostgreSQL config
        app = create_app()
        
        with app.app_context():
            logger.info("Testing database connection...")
            
            # Test basic connection
            result = db.engine.execute("SELECT 1 as test").fetchone()
            if result and result[0] == 1:
                logger.info("✓ Database connection successful")
            else:
                logger.error("✗ Database connection test failed")
                return False
            
            # Test table existence
            tables = db.engine.table_names()
            expected_tables = ['users', 'token_blacklist', 'api_logs']
            
            for table in expected_tables:
                if table in tables:
                    logger.info(f"✓ Table '{table}' exists")
                else:
                    logger.warning(f"⚠ Table '{table}' not found")
            
            # Test user operations
            from app.models import User
            
            # Count existing users
            user_count = User.query.count()
            logger.info(f"✓ Found {user_count} users in database")
            
            # Test creating a test user
            test_user = User(
                username='testuser_postgresql',
                email='test_postgresql@example.com',
                password='testpass123'
            )
            
            db.session.add(test_user)
            db.session.commit()
            logger.info("✓ Test user created successfully")
            
            # Clean up test user
            db.session.delete(test_user)
            db.session.commit()
            logger.info("✓ Test user cleaned up")
            
            logger.info("🎉 PostgreSQL application test successful!")
            return True
            
    except Exception as e:
        logger.error(f"✗ Application test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_app_with_postgresql()
    sys.exit(0 if success else 1)
