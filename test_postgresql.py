#!/usr/bin/env python3
"""
Test script to verify PostgreSQL connection and basic functionality.
"""

import os
import sys
import logging
from app import create_app
from app.models import db, User, TokenBlacklist, APILog

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database_connection():
    """Setup database connection with proper URL encoding"""
    # Use environment variable if set, otherwise use manual encoding
    if not os.environ.get('DATABASE_URL'):
        # Manually encode the @ symbol to %40 without double-encoding
        password_encoded = 'Zy2H%40sg0Ykl6ngf'
        temp_db_url = f'postgresql://dreambees:{password_encoded}@108.175.14.173:5432/dream_'
        os.environ['DATABASE_URL'] = temp_db_url

def test_database_connection():
    """Test basic database connection"""
    try:
        setup_database_connection()
        app = create_app()
        
        with app.app_context():
            # Test basic connection
            result = db.engine.execute("SELECT 1 as test").fetchone()
            if result and result[0] == 1:
                logger.info("✓ Database connection successful")
                return True
            else:
                logger.error("✗ Database connection test failed")
                return False
                
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False

def test_table_creation():
    """Test that tables can be created"""
    try:
        setup_database_connection()
        app = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("✓ Tables created successfully")
            
            # Check if tables exist
            tables = db.engine.table_names()
            expected_tables = ['users', 'token_blacklist', 'api_logs']
            
            for table in expected_tables:
                if table in tables:
                    logger.info(f"✓ Table '{table}' exists")
                else:
                    logger.warning(f"⚠ Table '{table}' not found")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ Table creation failed: {e}")
        return False

def test_user_operations():
    """Test user model operations"""
    try:
        setup_database_connection()
        app = create_app()
        
        with app.app_context():
            # Test creating a user
            test_user = User(
                username='testuser',
                email='test@example.com',
                password='testpass123',
                is_admin=False
            )
            
            db.session.add(test_user)
            db.session.commit()
            logger.info("✓ User created successfully")
            
            # Test querying user
            found_user = User.query.filter_by(username='testuser').first()
            if found_user:
                logger.info(f"✓ User found: {found_user.username}")
            else:
                logger.error("✗ User not found after creation")
                return False
            
            # Test password verification
            if found_user.check_password('testpass123'):
                logger.info("✓ Password verification successful")
            else:
                logger.error("✗ Password verification failed")
                return False
            
            # Test user serialization
            user_dict = found_user.to_dict()
            if 'username' in user_dict and user_dict['username'] == 'testuser':
                logger.info("✓ User serialization successful")
            else:
                logger.error("✗ User serialization failed")
                return False
            
            # Clean up test user
            db.session.delete(found_user)
            db.session.commit()
            logger.info("✓ Test user cleaned up")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ User operations failed: {e}")
        return False

def test_api_log_operations():
    """Test API log model operations"""
    try:
        setup_database_connection()
        app = create_app()
        
        with app.app_context():
            # Create a test log entry
            log_entry = APILog(
                user_id=None,
                endpoint='/api/test',
                method='GET',
                ip_address='127.0.0.1',
                response_status=200,
                response_time=0.5,
                user_agent='Test Agent',
                request_size=1024,
                response_size=2048
            )
            
            db.session.add(log_entry)
            db.session.commit()
            logger.info("✓ API log created successfully")
            
            # Test querying log
            found_log = APILog.query.filter_by(endpoint='/api/test').first()
            if found_log:
                logger.info(f"✓ API log found: {found_log.endpoint}")
            else:
                logger.error("✗ API log not found after creation")
                return False
            
            # Test log serialization
            log_dict = found_log.to_dict()
            if 'endpoint' in log_dict and log_dict['endpoint'] == '/api/test':
                logger.info("✓ API log serialization successful")
            else:
                logger.error("✗ API log serialization failed")
                return False
            
            # Clean up test log
            db.session.delete(found_log)
            db.session.commit()
            logger.info("✓ Test API log cleaned up")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ API log operations failed: {e}")
        return False

def test_database_performance():
    """Test basic database performance"""
    try:
        setup_database_connection()
        app = create_app()
        
        with app.app_context():
            import time
            
            # Test insert performance
            start_time = time.time()
            
            users = []
            for i in range(100):
                user = User(
                    username=f'perftest{i}',
                    email=f'perftest{i}@example.com',
                    password='testpass123'
                )
                users.append(user)
            
            db.session.add_all(users)
            db.session.commit()
            
            insert_time = time.time() - start_time
            logger.info(f"✓ Inserted 100 users in {insert_time:.2f} seconds")
            
            # Test query performance
            start_time = time.time()
            
            found_users = User.query.filter(User.username.like('perftest%')).all()
            
            query_time = time.time() - start_time
            logger.info(f"✓ Queried {len(found_users)} users in {query_time:.2f} seconds")
            
            # Clean up performance test data
            for user in found_users:
                db.session.delete(user)
            db.session.commit()
            logger.info("✓ Performance test data cleaned up")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ Database performance test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting PostgreSQL database tests")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Table Creation", test_table_creation),
        ("User Operations", test_user_operations),
        ("API Log Operations", test_api_log_operations),
        ("Database Performance", test_database_performance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name} test PASSED")
            else:
                logger.error(f"✗ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} test FAILED with exception: {e}")
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! PostgreSQL is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the configuration.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
