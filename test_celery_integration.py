#!/usr/bin/env python3
"""
Test script for Celery integration.
This script tests the Celery worker startup and basic functionality.
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_celery_worker_manager():
    """Test the Celery worker manager"""
    try:
        logger.info("🧪 Testing Celery worker manager...")
        
        from app.celery_manager import CeleryWorkerManager
        
        # Create worker manager
        manager = CeleryWorkerManager(auto_start=False)
        
        # Test worker startup
        logger.info("Starting worker...")
        success = manager.start_worker(concurrency=1, loglevel='info')
        
        if success:
            logger.info("✅ Worker started successfully")
            
            # Wait a moment
            time.sleep(3)
            
            # Test worker health
            is_healthy = manager.is_worker_healthy()
            logger.info(f"Worker healthy: {is_healthy}")
            
            # Get worker status
            status = manager.get_worker_status()
            logger.info(f"Worker status: {status['status']}")
            logger.info(f"Worker PID: {status['pid']}")
            
            # Stop worker
            logger.info("Stopping worker...")
            manager.stop_worker()
            
            logger.info("✅ Celery worker manager test passed")
            return True
        else:
            logger.error("❌ Failed to start worker")
            return False
            
    except Exception as e:
        logger.error(f"❌ Celery worker manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_celery_app():
    """Test the Celery application configuration"""
    try:
        logger.info("🧪 Testing Celery application...")
        
        from celery_app import celery_app
        
        # Test Celery app configuration
        logger.info(f"Celery app name: {celery_app.main}")
        logger.info(f"Broker URL: {celery_app.conf.broker_url}")
        logger.info(f"Result backend: {celery_app.conf.result_backend}")
        
        # Test task registration
        registered_tasks = list(celery_app.tasks.keys())
        logger.info(f"Registered tasks: {registered_tasks}")
        
        # Check if our tasks are registered
        expected_tasks = ['health_check_task', 'pdf_generation_task', 'pdf_offset_task']
        for task in expected_tasks:
            if task in registered_tasks:
                logger.info(f"✅ Task '{task}' is registered")
            else:
                logger.warning(f"⚠️ Task '{task}' is not registered")
        
        logger.info("✅ Celery application test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Celery application test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_connection():
    """Test Redis connection"""
    try:
        logger.info("🧪 Testing Redis connection...")
        
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
        r = redis.Redis.from_url(redis_url)
        
        # Test connection
        r.ping()
        logger.info("✅ Redis connection successful")
        
        # Test basic operations
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        assert value == b'test_value'
        r.delete('test_key')
        
        logger.info("✅ Redis operations test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {e}")
        return False


def test_flask_integration():
    """Test Flask app integration with Celery"""
    try:
        logger.info("🧪 Testing Flask integration...")
        
        # Set environment for testing
        os.environ['START_CELERY_WORKER'] = 'false'  # Don't start worker during test
        
        from app import create_app
        
        # Create Flask app
        app = create_app()
        
        # Test app creation
        logger.info(f"Flask app created: {app.name}")
        
        # Test Celery routes registration
        with app.app_context():
            from app.api.celery_routes import celery_bp
            logger.info("✅ Celery routes blueprint loaded")
        
        logger.info("✅ Flask integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Flask integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("🎉 Starting Celery integration tests...")
    logger.info("")
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Celery Application", test_celery_app),
        ("Flask Integration", test_flask_integration),
        ("Celery Worker Manager", test_celery_worker_manager),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            logger.info("")
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
            logger.info("")
    
    # Summary
    logger.info("📊 Test Results Summary:")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info("=" * 50)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Celery integration is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
