#!/usr/bin/env python3
"""
Test script to verify Redis connection and functionality for the optimized API.
"""

import os
import sys
import time
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    import redis
    from app.redis_cache import redis_cache, redis_task_manager
    from app.async_tasks import task_manager
    from app.pdf_service import pdf_service
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def test_redis_connection():
    """Test basic Redis connection"""
    print("\n=== Testing Redis Connection ===")
    
    try:
        # Test direct Redis connection
        redis_url = 'redis://:MyStrongPassword123!@108.175.14.173:6379/0'
        client = redis.from_url(redis_url)
        client.ping()
        print("✓ Direct Redis connection successful")
        
        # Test Redis cache
        if redis_cache.available:
            print("✓ Redis cache initialized successfully")
        else:
            print("✗ Redis cache not available")
            return False
        
        # Test Redis task manager
        if redis_task_manager.available:
            print("✓ Redis task manager initialized successfully")
        else:
            print("✗ Redis task manager not available")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


def test_redis_cache():
    """Test Redis cache functionality"""
    print("\n=== Testing Redis Cache ===")
    
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping tests")
        return False
    
    try:
        # Test cache operations
        test_key = "test_cache_key"
        test_data = {
            'file_path': '/tmp/test.pdf',
            'file_size': 1024,
            'created_at': datetime.utcnow().isoformat(),
            'metadata': {'test': True}
        }
        
        # Test set
        redis_cache.set(test_key, '/tmp/test.pdf', test_data['metadata'])
        print("✓ Cache set operation successful")
        
        # Test get
        cached_result = redis_cache.get(test_key)
        if cached_result:
            print("✓ Cache get operation successful")
        else:
            print("✗ Cache get operation failed")
            return False
        
        # Test stats
        stats = redis_cache.get_stats()
        print(f"✓ Cache stats: {stats}")
        
        # Test delete
        redis_cache.delete(test_key)
        print("✓ Cache delete operation successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Redis cache test failed: {e}")
        return False


def test_redis_task_manager():
    """Test Redis task manager functionality"""
    print("\n=== Testing Redis Task Manager ===")
    
    if not redis_task_manager.available:
        print("✗ Redis task manager not available, skipping tests")
        return False
    
    try:
        # Test task creation
        task_id = "test_task_123"
        task_data = {
            'task_type': 'test',
            'status': 'pending',
            'progress': 0.0,
            'data': {'test': True}
        }
        
        success = redis_task_manager.create_task(task_id, task_data)
        if success:
            print("✓ Task creation successful")
        else:
            print("✗ Task creation failed")
            return False
        
        # Test task retrieval
        retrieved_task = redis_task_manager.get_task(task_id)
        if retrieved_task:
            print("✓ Task retrieval successful")
        else:
            print("✗ Task retrieval failed")
            return False
        
        # Test task update
        updates = {'status': 'running', 'progress': 50.0}
        success = redis_task_manager.update_task(task_id, updates)
        if success:
            print("✓ Task update successful")
        else:
            print("✗ Task update failed")
            return False
        
        # Test task deletion
        success = redis_task_manager.delete_task(task_id)
        if success:
            print("✓ Task deletion successful")
        else:
            print("✗ Task deletion failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Redis task manager test failed: {e}")
        return False


def test_integrated_task_manager():
    """Test the integrated task manager with Redis"""
    print("\n=== Testing Integrated Task Manager ===")
    
    try:
        # Test task creation
        request_data = {
            'card_size': 'standard',
            'paper_size': 'letter',
            'test': True
        }
        
        task_id = task_manager.create_task('pdf_generation', request_data)
        print(f"✓ Task created with ID: {task_id}")
        
        # Test task status retrieval
        task_status = task_manager.get_task_status(task_id)
        if task_status:
            print(f"✓ Task status retrieved: {task_status.status.value}")
        else:
            print("✗ Task status retrieval failed")
            return False
        
        # Test task progress update
        task_manager.update_task_progress(task_id, 25.0)
        print("✓ Task progress updated")
        
        # Test task completion
        result = {'file_path': '/tmp/test.pdf', 'file_size': 1024}
        task_manager.complete_task(task_id, result=result)
        print("✓ Task completed successfully")
        
        # Verify final status
        final_status = task_manager.get_task_status(task_id)
        if final_status and final_status.status.value == 'success':
            print("✓ Task completion verified")
        else:
            print("✗ Task completion verification failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Integrated task manager test failed: {e}")
        return False


def test_pdf_service_cache():
    """Test PDF service with Redis cache"""
    print("\n=== Testing PDF Service Cache ===")
    
    try:
        # Test cache availability
        if hasattr(pdf_service.cache, 'get_stats'):
            stats = pdf_service.cache.get_stats()
            print(f"✓ PDF service using Redis cache: {stats}")
        else:
            print("✓ PDF service using in-memory cache")
        
        return True
        
    except Exception as e:
        print(f"✗ PDF service cache test failed: {e}")
        return False


def main():
    """Run all Redis tests"""
    print("Redis Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Redis Cache", test_redis_cache),
        ("Redis Task Manager", test_redis_task_manager),
        ("Integrated Task Manager", test_integrated_task_manager),
        ("PDF Service Cache", test_pdf_service_cache),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Redis integration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the Redis configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
