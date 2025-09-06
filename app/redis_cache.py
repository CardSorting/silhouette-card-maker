"""
Production-ready Redis-based caching implementation for PDF generation optimization.
"""

import os
import json
import hashlib
import pickle
import threading
import time
import gzip
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
import redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from flask import current_app


class CircuitBreaker:
    """Circuit breaker pattern for Redis operations"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                else:
                    raise RedisError("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                if self.state == 'HALF_OPEN':
                    self.state = 'CLOSED'
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
                
                raise e


class RedisCache:
    """Production-ready Redis-based cache for generated PDFs and other data"""
    
    def __init__(self, redis_url: str = None, key_prefix: str = "pdf_cache", 
                 max_connections: int = 20, socket_timeout: int = 5, 
                 socket_connect_timeout: int = 5, retry_on_timeout: bool = True,
                 health_check_interval: int = 30, compression_threshold: int = 512):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
        self.key_prefix = key_prefix
        self.lock = threading.Lock()
        self.compression_threshold = compression_threshold
        self.health_check_interval = health_check_interval
        self.last_health_check = 0
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # Connection pool configuration
        self.pool_config = {
            'max_connections': max_connections,
            'socket_timeout': socket_timeout,
            'socket_connect_timeout': socket_connect_timeout,
            'retry_on_timeout': retry_on_timeout,
            'health_check_interval': health_check_interval,
            'decode_responses': False
        }
        
        # Initialize Redis connection pool
        try:
            self.connection_pool = ConnectionPool.from_url(
                self.redis_url, 
                **self.pool_config
            )
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection with circuit breaker
            self._test_connection()
            self.available = True
            self._log_info("Redis cache initialized successfully with connection pooling")
            
        except Exception as e:
            self.redis_client = None
            self.connection_pool = None
            self.available = False
            self._log_error(f"Redis not available, cache disabled: {e}")
    
    def _test_connection(self):
        """Test Redis connection with timeout"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            raise RedisError(f"Redis connection test failed: {e}")
    
    def _is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        if not self.available:
            return False
        
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return True
        
        try:
            self._test_connection()
            self.last_health_check = current_time
            # Reset circuit breaker on successful health check
            if self.circuit_breaker.state == 'OPEN':
                self.circuit_breaker.state = 'HALF_OPEN'
                self.circuit_breaker.failure_count = 0
            return True
        except Exception:
            self.available = False
            return False
    
    def _log_info(self, message: str):
        """Log info message with fallback"""
        try:
            current_app.logger.info(message)
        except RuntimeError:
            print(f"[INFO] {message}")
    
    def _log_error(self, message: str):
        """Log error message with fallback"""
        try:
            current_app.logger.error(message)
        except RuntimeError:
            print(f"[ERROR] {message}")
    
    def _log_warning(self, message: str):
        """Log warning message with fallback"""
        try:
            current_app.logger.warning(message)
        except RuntimeError:
            print(f"[WARNING] {message}")
    
    @contextmanager
    def _redis_operation(self, operation_name: str):
        """Context manager for Redis operations with error handling"""
        if not self._is_healthy():
            raise RedisError("Redis connection is not healthy")
        
        try:
            yield self.redis_client
        except (ConnectionError, TimeoutError) as e:
            self._log_error(f"Redis {operation_name} failed: {e}")
            # Don't raise RedisError for circuit breaker to handle
            raise e
        except Exception as e:
            self._log_error(f"Unexpected error during Redis {operation_name}: {e}")
            raise
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate a cache key from request data with versioning"""
        # Create a deterministic key from the request parameters
        key_data = {
            'card_size': request_data.get('card_size'),
            'paper_size': request_data.get('paper_size'),
            'only_fronts': request_data.get('only_fronts'),
            'crop': request_data.get('crop'),
            'extend_corners': request_data.get('extend_corners'),
            'ppi': request_data.get('ppi'),
            'quality': request_data.get('quality'),
            'skip_indices': sorted(request_data.get('skip_indices', [])),
            'load_offset': request_data.get('load_offset'),
            'name': request_data.get('name'),
            'file_hashes': self._get_file_hashes(request_data.get('files', {})),
            'cache_version': 'v2.0'  # Version for cache invalidation
        }
        
        # Create hash from sorted key data
        key_string = str(sorted(key_data.items()))
        hash_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]  # Use SHA256 for better distribution
        return f"{self.key_prefix}:{hash_key}"
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data if it exceeds threshold"""
        if len(data) > self.compression_threshold:
            return gzip.compress(data)
        return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data if it's compressed"""
        try:
            return gzip.decompress(data)
        except (OSError, EOFError):
            # Data is not compressed
            return data
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data with compression"""
        serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        return self._compress_data(serialized)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data with decompression"""
        decompressed = self._decompress_data(data)
        return pickle.loads(decompressed)
    
    def _get_file_hashes(self, files: Dict[str, Any]) -> Dict[str, str]:
        """Generate hashes for uploaded files"""
        hashes = {}
        for file_type, file_list in files.items():
            if file_list:
                file_hashes = []
                for file in file_list:
                    if hasattr(file, 'read'):
                        file.seek(0)
                        content = file.read()
                        file_hashes.append(hashlib.md5(content).hexdigest())
                        file.seek(0)  # Reset file pointer
                hashes[file_type] = sorted(file_hashes)
        return hashes
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result from Redis with circuit breaker protection"""
        if not self.available:
            return None
        
        def _get_operation():
            with self._redis_operation("get"):
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    # Deserialize the cached data with compression support
                    cache_entry = self._deserialize_data(cached_data)
                    
                    # Validate cache entry structure
                    if not isinstance(cache_entry, dict) or 'file_path' not in cache_entry:
                        self._log_warning(f"Invalid cache entry structure for key: {cache_key}")
                        return None
                    
                    # Check if file still exists (production safety check)
                    if not os.path.exists(cache_entry['file_path']):
                        self._log_warning(f"Cached file no longer exists: {cache_entry['file_path']}")
                        self.delete(cache_key)
                        return None
                    
                    # Update last accessed time and refresh TTL
                    cache_entry['last_accessed'] = datetime.utcnow().isoformat()
                    cache_entry['access_count'] = cache_entry.get('access_count', 0) + 1
                    
                    # Refresh TTL
                    self.redis_client.setex(
                        cache_key, 
                        timedelta(hours=24),  # Refresh TTL
                        self._serialize_data(cache_entry)
                    )
                    
                    return cache_entry
                return None
        
        try:
            return self.circuit_breaker.call(_get_operation)
        except RedisError as e:
            self._log_error(f"Redis cache get failed: {e}")
            return None
    
    def set(self, cache_key: str, file_path: str, metadata: Dict[str, Any], ttl_hours: int = 24):
        """Cache a result in Redis with compression and validation"""
        if not self.available:
            return
        
        def _set_operation():
            with self._redis_operation("set"):
                # Validate file exists and get size
                if not os.path.exists(file_path):
                    raise ValueError(f"File does not exist: {file_path}")
                
                file_size = os.path.getsize(file_path)
                file_mtime = os.path.getmtime(file_path)
                
                # Create comprehensive cache entry
                cache_entry = {
                    'file_path': file_path,
                    'file_size': file_size,
                    'file_mtime': file_mtime,
                    'created_at': datetime.utcnow().isoformat(),
                    'last_accessed': datetime.utcnow().isoformat(),
                    'access_count': 0,
                    'metadata': metadata,
                    'compression_used': False,
                    'cache_version': 'v2.0'
                }
                
                # Store in Redis with TTL and compression
                serialized_data = self._serialize_data(cache_entry)
                cache_entry['compression_used'] = len(serialized_data) < len(pickle.dumps(cache_entry))
                
                self.redis_client.setex(
                    cache_key,
                    timedelta(hours=ttl_hours),
                    serialized_data
                )
                
                self._log_info(f"Cached result with key: {cache_key} (size: {file_size} bytes, compressed: {cache_entry['compression_used']})")
                return True
        
        try:
            self.circuit_breaker.call(_set_operation)
        except RedisError as e:
            self._log_error(f"Redis cache set failed: {e}")
        except ValueError as e:
            self._log_error(f"Cache set validation failed: {e}")
    
    def delete(self, cache_key: str):
        """Delete a cache entry with circuit breaker protection"""
        if not self.available:
            return
        
        def _delete_operation():
            with self._redis_operation("delete"):
                return self.redis_client.delete(cache_key)
        
        try:
            self.circuit_breaker.call(_delete_operation)
        except RedisError as e:
            self._log_error(f"Redis cache delete failed: {e}")
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all cache entries matching a pattern"""
        if not self.available:
            return 0
        
        def _delete_pattern_operation():
            with self._redis_operation("delete_pattern"):
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
        
        try:
            return self.circuit_breaker.call(_delete_pattern_operation)
        except RedisError as e:
            self._log_error(f"Redis cache delete pattern failed: {e}")
            return 0
    
    def clear(self):
        """Clear all cache entries with the prefix"""
        if not self.available:
            return
        
        pattern = f"{self.key_prefix}:*"
        deleted_count = self.delete_pattern(pattern)
        if deleted_count > 0:
            self._log_info(f"Cleared {deleted_count} cache entries")
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries by pattern (e.g., by user, by card size)"""
        return self.delete_pattern(f"{self.key_prefix}:*{pattern}*")
    
    def warm_cache(self, cache_entries: List[Dict[str, Any]]):
        """Pre-warm cache with frequently used entries"""
        if not self.available:
            return
        
        warmed_count = 0
        for entry in cache_entries:
            try:
                cache_key = entry.get('key')
                file_path = entry.get('file_path')
                metadata = entry.get('metadata', {})
                ttl_hours = entry.get('ttl_hours', 24)
                
                if cache_key and file_path:
                    self.set(cache_key, file_path, metadata, ttl_hours)
                    warmed_count += 1
            except Exception as e:
                self._log_error(f"Cache warming failed for entry: {e}")
        
        self._log_info(f"Cache warmed with {warmed_count} entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        if not self.available:
            return {
                'available': False,
                'entry_count': 0,
                'total_size_mb': 0,
                'circuit_breaker_state': self.circuit_breaker.state
            }
        
        def _stats_operation():
            with self._redis_operation("stats"):
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                total_size = 0
                compressed_count = 0
                access_counts = []
                creation_times = []
                
                for key in keys:
                    try:
                        cached_data = self.redis_client.get(key)
                        if cached_data:
                            cache_entry = self._deserialize_data(cached_data)
                            total_size += cache_entry.get('file_size', 0)
                            
                            if cache_entry.get('compression_used', False):
                                compressed_count += 1
                            
                            access_counts.append(cache_entry.get('access_count', 0))
                            
                            # Parse creation time
                            created_at = cache_entry.get('created_at')
                            if created_at:
                                try:
                                    creation_times.append(datetime.fromisoformat(created_at.replace('Z', '+00:00')))
                                except:
                                    pass
                    except Exception:
                        continue
                
                # Calculate additional metrics
                avg_access_count = sum(access_counts) / len(access_counts) if access_counts else 0
                oldest_entry = min(creation_times) if creation_times else None
                newest_entry = max(creation_times) if creation_times else None
                
                # Get Redis memory info
                redis_info = self.redis_client.info('memory')
                
                return {
                    'available': True,
                    'entry_count': len(keys),
                    'total_size_mb': total_size / (1024 * 1024),
                    'compressed_entries': compressed_count,
                    'compression_ratio': compressed_count / len(keys) if keys else 0,
                    'avg_access_count': avg_access_count,
                    'oldest_entry': oldest_entry.isoformat() if oldest_entry else None,
                    'newest_entry': newest_entry.isoformat() if newest_entry else None,
                    'circuit_breaker_state': self.circuit_breaker.state,
                    'circuit_breaker_failures': self.circuit_breaker.failure_count,
                    'redis_info': redis_info,
                    'connection_pool_stats': {
                        'max_connections': self.pool_config['max_connections'],
                        'created_connections': getattr(self.connection_pool, 'created_connections', 0),
                        'available_connections': getattr(self.connection_pool, 'available_connections', 0)
                    }
                }
        
        try:
            return self.circuit_breaker.call(_stats_operation)
        except RedisError as e:
            self._log_error(f"Redis cache stats failed: {e}")
            return {
                'available': False,
                'error': str(e),
                'circuit_breaker_state': self.circuit_breaker.state
            }
    
    def cleanup_expired(self):
        """Clean up expired entries and orphaned files"""
        if not self.available:
            return
        
        def _cleanup_operation():
            with self._redis_operation("cleanup"):
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                cleaned_count = 0
                for key in keys:
                    try:
                        cached_data = self.redis_client.get(key)
                        if cached_data:
                            cache_entry = self._deserialize_data(cached_data)
                            
                            # Check if file still exists
                            if not os.path.exists(cache_entry.get('file_path', '')):
                                self.redis_client.delete(key)
                                cleaned_count += 1
                                continue
                            
                            # Check if file was modified after caching
                            file_mtime = os.path.getmtime(cache_entry['file_path'])
                            if file_mtime > cache_entry.get('file_mtime', 0):
                                self.redis_client.delete(key)
                                cleaned_count += 1
                                
                    except Exception:
                        continue
                
                if cleaned_count > 0:
                    self._log_info(f"Cleaned up {cleaned_count} expired/orphaned cache entries")
                
                return cleaned_count
        
        try:
            self.circuit_breaker.call(_cleanup_operation)
        except RedisError as e:
            self._log_error(f"Redis cache cleanup failed: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the cache"""
        return {
            'available': self.available,
            'healthy': self._is_healthy(),
            'circuit_breaker_state': self.circuit_breaker.state,
            'circuit_breaker_failures': self.circuit_breaker.failure_count,
            'last_health_check': self.last_health_check,
            'connection_pool_created': getattr(self.connection_pool, 'created_connections', 0) if self.connection_pool else 0,
            'connection_pool_available': getattr(self.connection_pool, 'available_connections', 0) if self.connection_pool else 0
        }
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker state (for manual recovery)"""
        with self.circuit_breaker.lock:
            self.circuit_breaker.state = 'CLOSED'
            self.circuit_breaker.failure_count = 0
            self.circuit_breaker.last_failure_time = None
        self._log_info("Circuit breaker reset manually")
    
    def _force_health_check(self):
        """Force a health check and reset circuit breaker if Redis is available"""
        try:
            self._test_connection()
            self.available = True
            self.last_health_check = time.time()
            # Reset circuit breaker on successful connection
            with self.circuit_breaker.lock:
                if self.circuit_breaker.state == 'OPEN':
                    self.circuit_breaker.state = 'HALF_OPEN'
                    self.circuit_breaker.failure_count = 0
            return True
        except Exception as e:
            self.available = False
            return False


class RedisTaskManager:
    """Production-ready Redis-based task management for async operations"""
    
    def __init__(self, redis_url: str = None, key_prefix: str = "tasks", 
                 max_connections: int = 10, socket_timeout: int = 5):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
        self.key_prefix = key_prefix
        self.lock = threading.Lock()
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        
        # Connection pool configuration
        self.pool_config = {
            'max_connections': max_connections,
            'socket_timeout': socket_timeout,
            'socket_connect_timeout': socket_timeout,
            'retry_on_timeout': True,
            'decode_responses': False
        }
        
        # Initialize Redis connection pool
        try:
            self.connection_pool = ConnectionPool.from_url(
                self.redis_url, 
                **self.pool_config
            )
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            self.redis_client.ping()
            self.available = True
            self._log_info("Redis task manager initialized successfully with connection pooling")
            
        except Exception as e:
            self.redis_client = None
            self.connection_pool = None
            self.available = False
            self._log_error(f"Redis not available for task management: {e}")
    
    def _log_info(self, message: str):
        """Log info message with fallback"""
        try:
            current_app.logger.info(message)
        except RuntimeError:
            print(f"[INFO] {message}")
    
    def _log_error(self, message: str):
        """Log error message with fallback"""
        try:
            current_app.logger.error(message)
        except RuntimeError:
            print(f"[ERROR] {message}")
    
    @contextmanager
    def _redis_operation(self, operation_name: str):
        """Context manager for Redis operations with error handling"""
        if not self.available:
            raise RedisError("Redis task manager is not available")
        
        try:
            yield self.redis_client
        except (ConnectionError, TimeoutError) as e:
            self._log_error(f"Redis task {operation_name} failed: {e}")
            raise RedisError(f"Redis task {operation_name} failed: {e}")
        except Exception as e:
            self._log_error(f"Unexpected error during Redis task {operation_name}: {e}")
            raise
    
    def create_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Create a new task in Redis with circuit breaker protection"""
        if not self.available:
            return False
        
        def _create_operation():
            with self._redis_operation("create"):
                task_info = {
                    'task_id': task_id,
                    'status': 'pending',
                    'created_at': datetime.utcnow().isoformat(),
                    'progress': 0.0,
                    'data': task_data,
                    'retry_count': 0,
                    'max_retries': task_data.get('max_retries', 3),
                    'priority': task_data.get('priority', 'normal'),
                    'created_by': task_data.get('user_id', 'system')
                }
                
                key = f"{self.key_prefix}:{task_id}"
                self.redis_client.setex(
                    key,
                    timedelta(hours=24),  # Task expires in 24 hours
                    pickle.dumps(task_info)
                )
                return True
        
        try:
            return self.circuit_breaker.call(_create_operation)
        except RedisError as e:
            self._log_error(f"Redis task create failed: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information from Redis with circuit breaker protection"""
        if not self.available:
            return None
        
        def _get_operation():
            with self._redis_operation("get"):
                key = f"{self.key_prefix}:{task_id}"
                task_data = self.redis_client.get(key)
                if task_data:
                    return pickle.loads(task_data)
                return None
        
        try:
            return self.circuit_breaker.call(_get_operation)
        except RedisError as e:
            self._log_error(f"Redis task get failed: {e}")
            return None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update task information in Redis with circuit breaker protection"""
        if not self.available:
            return False
        
        def _update_operation():
            with self._redis_operation("update"):
                key = f"{self.key_prefix}:{task_id}"
                task_data = self.redis_client.get(key)
                if task_data:
                    task_info = pickle.loads(task_data)
                    task_info.update(updates)
                    
                    # Update timestamps based on status
                    if 'status' in updates:
                        if updates['status'] == 'running' and task_info.get('status') == 'pending':
                            task_info['started_at'] = datetime.utcnow().isoformat()
                        elif updates['status'] in ['success', 'failure', 'cancelled']:
                            task_info['completed_at'] = datetime.utcnow().isoformat()
                    
                    # Track retry attempts
                    if updates.get('status') == 'failure':
                        task_info['retry_count'] = task_info.get('retry_count', 0) + 1
                    
                    self.redis_client.setex(
                        key,
                        timedelta(hours=24),
                        pickle.dumps(task_info)
                    )
                    return True
                return False
        
        try:
            return self.circuit_breaker.call(_update_operation)
        except RedisError as e:
            self._log_error(f"Redis task update failed: {e}")
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from Redis with circuit breaker protection"""
        if not self.available:
            return False
        
        def _delete_operation():
            with self._redis_operation("delete"):
                key = f"{self.key_prefix}:{task_id}"
                return bool(self.redis_client.delete(key))
        
        try:
            return self.circuit_breaker.call(_delete_operation)
        except RedisError as e:
            self._log_error(f"Redis task delete failed: {e}")
            return False
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all tasks with a specific status"""
        if not self.available:
            return []
        
        def _get_tasks_operation():
            with self._redis_operation("get_tasks_by_status"):
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                tasks = []
                for key in keys:
                    try:
                        task_data = self.redis_client.get(key)
                        if task_data:
                            task_info = pickle.loads(task_data)
                            if task_info.get('status') == status:
                                tasks.append(task_info)
                    except Exception:
                        continue
                
                return tasks
        
        try:
            return self.circuit_breaker.call(_get_tasks_operation)
        except RedisError as e:
            self._log_error(f"Redis get tasks by status failed: {e}")
            return []
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get comprehensive task statistics"""
        if not self.available:
            return {'available': False}
        
        def _stats_operation():
            with self._redis_operation("task_stats"):
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                status_counts = {}
                priority_counts = {}
                total_tasks = len(keys)
                
                for key in keys:
                    try:
                        task_data = self.redis_client.get(key)
                        if task_data:
                            task_info = pickle.loads(task_data)
                            status = task_info.get('status', 'unknown')
                            priority = task_info.get('priority', 'normal')
                            
                            status_counts[status] = status_counts.get(status, 0) + 1
                            priority_counts[priority] = priority_counts.get(priority, 0) + 1
                    except Exception:
                        continue
                
                return {
                    'available': True,
                    'total_tasks': total_tasks,
                    'status_counts': status_counts,
                    'priority_counts': priority_counts,
                    'circuit_breaker_state': self.circuit_breaker.state,
                    'circuit_breaker_failures': self.circuit_breaker.failure_count
                }
        
        try:
            return self.circuit_breaker.call(_stats_operation)
        except RedisError as e:
            self._log_error(f"Redis task stats failed: {e}")
            return {'available': False, 'error': str(e)}
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        if not self.available:
            return
        
        def _cleanup_operation():
            with self._redis_operation("cleanup"):
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
                cleaned_count = 0
                
                for key in keys:
                    try:
                        task_data = self.redis_client.get(key)
                        if task_data:
                            task_info = pickle.loads(task_data)
                            
                            # Clean up completed tasks older than max_age_hours
                            if (task_info.get('status') in ['success', 'failure', 'cancelled'] and
                                task_info.get('completed_at')):
                                completed_at = datetime.fromisoformat(task_info['completed_at'].replace('Z', '+00:00'))
                                if completed_at < cutoff_time:
                                    self.redis_client.delete(key)
                                    cleaned_count += 1
                    except Exception:
                        continue
                
                if cleaned_count > 0:
                    self._log_info(f"Cleaned up {cleaned_count} old completed tasks")
                
                return cleaned_count
        
        try:
            self.circuit_breaker.call(_cleanup_operation)
        except RedisError as e:
            self._log_error(f"Redis task cleanup failed: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the task manager"""
        return {
            'available': self.available,
            'circuit_breaker_state': self.circuit_breaker.state,
            'circuit_breaker_failures': self.circuit_breaker.failure_count,
            'connection_pool_created': getattr(self.connection_pool, 'created_connections', 0) if self.connection_pool else 0,
            'connection_pool_available': getattr(self.connection_pool, 'available_connections', 0) if self.connection_pool else 0
        }


# Global instances
redis_cache = RedisCache()
redis_task_manager = RedisTaskManager()
