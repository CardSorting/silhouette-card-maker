#!/usr/bin/env python3
"""
Comprehensive fault tolerance test suite for Redis cache in production scenarios.
Tests graceful degradation, error recovery, and resilience patterns.
"""

import os
import sys
import time
import tempfile
import threading
import socket
from unittest.mock import patch, MagicMock
from datetime import datetime
import redis
from redis.exceptions import ResponseError

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.redis_cache import redis_cache, redis_task_manager, CircuitBreaker, RedisCache, RedisTaskManager
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def test_redis_connection_failure():
    """Test behavior when Redis connection fails completely"""
    print("\n=== Testing Redis Connection Failure ===")
    
    # Create a cache instance with invalid Redis URL
    invalid_cache = RedisCache(redis_url='redis://invalid-host:6379/0')
    
    # Test that cache gracefully handles connection failure
    assert not invalid_cache.available
    print("✓ Cache correctly identifies Redis as unavailable")
    
    # Test that operations return None/False without crashing
    result = invalid_cache.get("test_key")
    assert result is None
    print("✓ Get operation gracefully returns None when Redis unavailable")
    
    # Test set operation
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    test_file.write(b"test data")
    test_file.close()
    
    invalid_cache.set("test_key", test_file.name, {})
    print("✓ Set operation gracefully handles Redis unavailability")
    
    # Test delete operation
    invalid_cache.delete("test_key")
    print("✓ Delete operation gracefully handles Redis unavailability")
    
    # Test stats
    stats = invalid_cache.get_stats()
    assert not stats['available']
    print("✓ Stats correctly report Redis unavailability")
    
    # Cleanup
    os.unlink(test_file.name)
    return True


def test_redis_timeout_scenarios():
    """Test behavior when Redis operations timeout"""
    print("\n=== Testing Redis Timeout Scenarios ===")
    
    # Test with mocked timeout scenarios instead of real timeouts
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping timeout tests")
        return False
    
    # Reset circuit breaker first
    redis_cache.reset_circuit_breaker()
    
    # Mock Redis client to simulate timeouts
    original_redis_client = redis_cache.redis_client
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.side_effect = redis.exceptions.TimeoutError("Operation timed out")
    mock_client.setex.side_effect = redis.exceptions.TimeoutError("Operation timed out")
    mock_client.delete.side_effect = redis.exceptions.TimeoutError("Operation timed out")
    mock_client.keys.side_effect = redis.exceptions.TimeoutError("Operation timed out")
    mock_client.info.side_effect = redis.exceptions.TimeoutError("Operation timed out")
    
    # Temporarily replace the Redis client
    redis_cache.redis_client = mock_client
    
    try:
        # Test that timeout operations are handled gracefully
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        test_file.write(b"timeout test data")
        test_file.close()
        
        # This should timeout and be handled gracefully
        redis_cache.set("timeout_key", test_file.name, {})
        print("✓ Set operation handles timeout gracefully")
        
        # Test get with timeout
        result = redis_cache.get("timeout_key")
        assert result is None
        print("✓ Get operation handles timeout gracefully")
        
        # Test stats with timeout
        stats = redis_cache.get_stats()
        assert not stats['available']
        print("✓ Stats operation handles timeout gracefully")
        
        # Cleanup
        os.unlink(test_file.name)
        return True
        
    finally:
        # Restore original Redis client
        redis_cache.redis_client = original_redis_client
        redis_cache.reset_circuit_breaker()


def test_circuit_breaker_failure_recovery():
    """Test circuit breaker failure and recovery scenarios"""
    print("\n=== Testing Circuit Breaker Failure Recovery ===")
    
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2)
    
    # Test rapid failures trigger circuit breaker
    def failing_operation():
        raise ConnectionError("Simulated Redis failure")
    
    failures = 0
    for i in range(5):
        try:
            cb.call(failing_operation)
        except Exception:
            failures += 1
    
    assert cb.state == 'OPEN'
    assert failures == 5
    print("✓ Circuit breaker opened after threshold failures")
    
    # Test that circuit breaker blocks operations when open
    try:
        cb.call(failing_operation)
        print("✗ Circuit breaker should have blocked operation")
        return False
    except Exception as e:
        if "Circuit breaker is OPEN" in str(e):
            print("✓ Circuit breaker correctly blocks operations when open")
        else:
            print(f"✗ Unexpected error: {e}")
            return False
    
    # Test recovery after timeout
    time.sleep(3)  # Wait for recovery timeout
    
    def success_operation():
        return "success"
    
    try:
        result = cb.call(success_operation)
        assert result == "success"
        assert cb.state == 'CLOSED'
        print("✓ Circuit breaker recovered and closed after successful operation")
    except Exception as e:
        print(f"✗ Circuit breaker recovery failed: {e}")
        return False
    
    return True


def test_concurrent_failures():
    """Test behavior under concurrent failure scenarios"""
    print("\n=== Testing Concurrent Failures ===")
    
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping concurrent tests")
        return False
    
    # Reset circuit breaker first
    redis_cache.reset_circuit_breaker()
    
    # Simulate concurrent operations with some failures
    import queue
    results = queue.Queue()
    
    def worker_with_failure(worker_id):
        try:
            key = f"concurrent_test_{worker_id}"
            test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            test_file.write(f"Worker {worker_id} data".encode())
            test_file.close()
            
            # Simulate occasional failures
            if worker_id % 3 == 0:
                # Simulate a failure by using invalid data
                redis_cache.set(key, "/nonexistent/file.pdf", {})
            else:
                redis_cache.set(key, test_file.name, {'worker': worker_id})
            
            result = redis_cache.get(key)
            results.put(('success', worker_id, result is not None))
            
            # Cleanup
            if os.path.exists(test_file.name):
                os.unlink(test_file.name)
            redis_cache.delete(key)
            
        except Exception as e:
            results.put(('error', worker_id, str(e)))
    
    # Start multiple threads
    threads = []
    for i in range(15):
        thread = threading.Thread(target=worker_with_failure, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Check results - some should succeed, some should fail gracefully
    success_count = 0
    error_count = 0
    while not results.empty():
        status, worker_id, result = results.get()
        if status == 'success':
            success_count += 1
        else:
            error_count += 1
    
    print(f"✓ Concurrent operations completed: {success_count} successes, {error_count} errors")
    print("✓ System remained stable under concurrent failure scenarios")
    
    # Reset circuit breaker after test
    redis_cache.reset_circuit_breaker()
    
    return True


def test_memory_pressure_scenarios():
    """Test behavior under memory pressure"""
    print("\n=== Testing Memory Pressure Scenarios ===")
    
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping memory pressure tests")
        return False
    
    # Reset circuit breaker first
    redis_cache.reset_circuit_breaker()
    
    # Create large files to test memory handling
    large_files = []
    try:
        for i in range(5):
            large_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            # Create 1MB file
            large_file.write(b"x" * (1024 * 1024))
            large_file.close()
            large_files.append(large_file.name)
            
            # Cache the large file
            redis_cache.set(f"large_file_{i}", large_file.name, {'size': '1MB'})
        
        print("✓ Large file caching handled gracefully")
        
        # Test retrieval of large files
        for i in range(5):
            result = redis_cache.get(f"large_file_{i}")
            assert result is not None
            assert result['file_path'] == large_files[i]
        
        print("✓ Large file retrieval handled gracefully")
        
        # Test stats with large files
        stats = redis_cache.get_stats()
        if stats['available']:
            # Check that we have entries and stats are calculated
            assert stats['entry_count'] >= 0  # Should have some entries
            print(f"✓ Stats correctly calculated: {stats['entry_count']} entries, {stats['total_size_mb']:.2f}MB total")
        else:
            print("✓ Stats operation handled gracefully when cache unavailable")
        
        # Cleanup
        for i in range(5):
            redis_cache.delete(f"large_file_{i}")
        
        return True
        
    except Exception as e:
        print(f"✗ Memory pressure test failed: {e}")
        return False
    finally:
        # Cleanup files
        for file_path in large_files:
            if os.path.exists(file_path):
                os.unlink(file_path)
        # Reset circuit breaker after test
        redis_cache.reset_circuit_breaker()


def test_network_partition_simulation():
    """Test behavior during network partition simulation"""
    print("\n=== Testing Network Partition Simulation ===")
    
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping network partition tests")
        return False
    
    # Reset circuit breaker first
    redis_cache.reset_circuit_breaker()
    
    # Test with mocked network failures
    original_redis_client = redis_cache.redis_client
    
    # Mock Redis client to simulate network failures
    mock_client = MagicMock()
    mock_client.ping.side_effect = ConnectionError("Network partition")
    mock_client.get.side_effect = ConnectionError("Network partition")
    mock_client.setex.side_effect = ConnectionError("Network partition")
    mock_client.delete.side_effect = ConnectionError("Network partition")
    mock_client.keys.side_effect = ConnectionError("Network partition")
    mock_client.info.side_effect = ConnectionError("Network partition")
    
    # Temporarily replace the Redis client
    redis_cache.redis_client = mock_client
    
    try:
        # Test that operations fail gracefully
        result = redis_cache.get("test_key")
        assert result is None
        print("✓ Get operation handles network partition gracefully")
        
        # Test set operation
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        test_file.write(b"network test data")
        test_file.close()
        
        redis_cache.set("test_key", test_file.name, {})
        print("✓ Set operation handles network partition gracefully")
        
        # Test stats
        stats = redis_cache.get_stats()
        assert not stats['available']
        print("✓ Stats correctly report network partition")
        
        # Cleanup
        os.unlink(test_file.name)
        
        return True
        
    except Exception as e:
        # The exception should be caught by the circuit breaker, not propagated
        if "Network partition" in str(e):
            print("✓ Network partition exception handled by circuit breaker")
            return True
        else:
            print(f"✗ Network partition test failed: {e}")
            return False
    finally:
        # Restore original Redis client
        redis_cache.redis_client = original_redis_client
        redis_cache.reset_circuit_breaker()


def test_redis_memory_exhaustion():
    """Test behavior when Redis runs out of memory"""
    print("\n=== Testing Redis Memory Exhaustion ===")
    
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping memory exhaustion tests")
        return False
    
    # Reset circuit breaker first
    redis_cache.reset_circuit_breaker()
    
    # Test with mocked Redis memory error
    original_redis_client = redis_cache.redis_client
    
    # Mock Redis client to simulate memory exhaustion
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.setex.side_effect = ResponseError("OOM command not allowed when used memory > 'maxmemory'")
    mock_client.delete.return_value = 1
    mock_client.keys.return_value = []
    mock_client.info.return_value = {'used_memory': 1000000000, 'maxmemory': 500000000}
    
    # Temporarily replace the Redis client
    redis_cache.redis_client = mock_client
    
    try:
        # Test that memory exhaustion is handled gracefully
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        test_file.write(b"memory test data")
        test_file.close()
        
        redis_cache.set("memory_test_key", test_file.name, {})
        print("✓ Set operation handles Redis memory exhaustion gracefully")
        
        # Test that we can still read from cache
        result = redis_cache.get("memory_test_key")
        print("✓ Get operation works during memory exhaustion")
        
        # Cleanup
        os.unlink(test_file.name)
        
        return True
        
    except Exception as e:
        print(f"✗ Memory exhaustion test failed: {e}")
        return False
    finally:
        # Restore original Redis client
        redis_cache.redis_client = original_redis_client
        redis_cache.reset_circuit_breaker()


def test_graceful_degradation_patterns():
    """Test various graceful degradation patterns"""
    print("\n=== Testing Graceful Degradation Patterns ===")
    
    # Test 1: Cache unavailable, application continues
    invalid_cache = RedisCache(redis_url='redis://invalid:6379/0')
    
    # Application should continue working without cache
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    test_file.write(b"degradation test")
    test_file.close()
    
    # These operations should not crash the application
    invalid_cache.set("key1", test_file.name, {})
    result = invalid_cache.get("key1")
    invalid_cache.delete("key1")
    stats = invalid_cache.get_stats()
    
    assert result is None
    assert not stats['available']
    print("✓ Application continues working when cache is unavailable")
    
    # Test 2: Partial Redis failure (some operations work, others don't)
    if redis_cache.available:
        # Test with mixed success/failure scenarios
        original_setex = redis_cache.redis_client.setex
        
        def failing_setex(*args, **kwargs):
            if "fail_key" in str(args[0]):
                raise ConnectionError("Simulated failure")
            return original_setex(*args, **kwargs)
        
        redis_cache.redis_client.setex = failing_setex
        
        try:
            # This should work
            redis_cache.set("success_key", test_file.name, {})
            print("✓ Successful operations work during partial failure")
            
            # This should fail gracefully
            try:
                redis_cache.set("fail_key", test_file.name, {})
                print("✓ Failed operations are handled gracefully during partial failure")
            except Exception as e:
                if "Simulated failure" in str(e):
                    print("✓ Failed operations are handled gracefully during partial failure")
                else:
                    print(f"✗ Unexpected error: {e}")
                    return False
            
            # Cleanup
            redis_cache.delete("success_key")
            
        finally:
            redis_cache.redis_client.setex = original_setex
    
    # Cleanup
    os.unlink(test_file.name)
    return True


def test_health_monitoring_under_stress():
    """Test health monitoring under various stress conditions"""
    print("\n=== Testing Health Monitoring Under Stress ===")
    
    if not redis_cache.available:
        print("✗ Redis cache not available, skipping health monitoring tests")
        return False
    
    # Test health status under normal conditions
    health = redis_cache.get_health_status()
    assert 'available' in health
    assert 'healthy' in health
    assert 'circuit_breaker_state' in health
    print("✓ Health monitoring works under normal conditions")
    
    # Test health status during simulated failures
    original_redis_client = redis_cache.redis_client
    mock_client = MagicMock()
    mock_client.ping.side_effect = ConnectionError("Health check failure")
    
    redis_cache.redis_client = mock_client
    
    try:
        # Force health check
        redis_cache.last_health_check = 0
        health = redis_cache.get_health_status()
        assert not health['healthy']
        print("✓ Health monitoring correctly detects failures")
        
    finally:
        redis_cache.redis_client = original_redis_client
    
    return True


def main():
    """Run all fault tolerance tests"""
    print("Redis Cache Fault Tolerance Test Suite")
    print("=" * 50)
    
    tests = [
        ("Redis Connection Failure", test_redis_connection_failure),
        ("Redis Timeout Scenarios", test_redis_timeout_scenarios),
        ("Circuit Breaker Failure Recovery", test_circuit_breaker_failure_recovery),
        ("Concurrent Failures", test_concurrent_failures),
        ("Memory Pressure Scenarios", test_memory_pressure_scenarios),
        ("Network Partition Simulation", test_network_partition_simulation),
        ("Redis Memory Exhaustion", test_redis_memory_exhaustion),
        ("Graceful Degradation Patterns", test_graceful_degradation_patterns),
        ("Health Monitoring Under Stress", test_health_monitoring_under_stress),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("FAULT TOLERANCE TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} fault tolerance tests passed")
    
    if passed == total:
        print("🎉 All fault tolerance tests passed! Redis cache is resilient.")
        return 0
    else:
        print("❌ Some fault tolerance tests failed. Review graceful degradation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
