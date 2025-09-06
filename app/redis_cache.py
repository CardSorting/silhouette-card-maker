"""
Redis-based caching implementation for PDF generation optimization.
"""

import os
import json
import hashlib
import pickle
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import redis
from flask import current_app


class RedisCache:
    """Redis-based cache for generated PDFs and other data"""
    
    def __init__(self, redis_url: str = None, key_prefix: str = "pdf_cache"):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
        self.key_prefix = key_prefix
        self.lock = threading.Lock()
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            # Test connection
            self.redis_client.ping()
            self.available = True
            try:
                current_app.logger.info("Redis cache initialized successfully")
            except RuntimeError:
                print("Redis cache initialized successfully")
        except Exception as e:
            try:
                current_app.logger.warning(f"Redis not available, cache disabled: {e}")
            except RuntimeError:
                print(f"Redis not available, cache disabled: {e}")
            self.redis_client = None
            self.available = False
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate a cache key from request data"""
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
            'file_hashes': self._get_file_hashes(request_data.get('files', {}))
        }
        
        # Create hash from sorted key data
        key_string = str(sorted(key_data.items()))
        hash_key = hashlib.md5(key_string.encode()).hexdigest()
        return f"{self.key_prefix}:{hash_key}"
    
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
        """Get cached result from Redis"""
        if not self.available:
            return None
        
        try:
            with self.lock:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    # Deserialize the cached data
                    cache_entry = pickle.loads(cached_data)
                    
                    # Check if the file still exists
                    if os.path.exists(cache_entry['file_path']):
                        # Update last accessed time
                        cache_entry['last_accessed'] = datetime.utcnow().isoformat()
                        self.redis_client.setex(
                            cache_key, 
                            timedelta(hours=24),  # Refresh TTL
                            pickle.dumps(cache_entry)
                        )
                        return cache_entry
                    else:
                        # File no longer exists, remove from cache
                        self.redis_client.delete(cache_key)
        except Exception as e:
            try:
                current_app.logger.error(f"Redis cache get error: {e}")
            except RuntimeError:
                print(f"Redis cache get error: {e}")
        
        return None
    
    def set(self, cache_key: str, file_path: str, metadata: Dict[str, Any], ttl_hours: int = 24):
        """Cache a result in Redis"""
        if not self.available:
            return
        
        try:
            with self.lock:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                cache_entry = {
                    'file_path': file_path,
                    'file_size': file_size,
                    'created_at': datetime.utcnow().isoformat(),
                    'last_accessed': datetime.utcnow().isoformat(),
                    'metadata': metadata
                }
                
                # Store in Redis with TTL
                self.redis_client.setex(
                    cache_key,
                    timedelta(hours=ttl_hours),
                    pickle.dumps(cache_entry)
                )
                
                try:
                    current_app.logger.info(f"Cached result with key: {cache_key}")
                except RuntimeError:
                    print(f"Cached result with key: {cache_key}")
                
        except Exception as e:
            try:
                current_app.logger.error(f"Redis cache set error: {e}")
            except RuntimeError:
                print(f"Redis cache set error: {e}")
    
    def delete(self, cache_key: str):
        """Delete a cache entry"""
        if not self.available:
            return
        
        try:
            with self.lock:
                self.redis_client.delete(cache_key)
        except Exception as e:
            try:
                current_app.logger.error(f"Redis cache delete error: {e}")
            except RuntimeError:
                print(f"Redis cache delete error: {e}")
    
    def clear(self):
        """Clear all cache entries with the prefix"""
        if not self.available:
            return
        
        try:
            with self.lock:
                # Get all keys with the prefix
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    try:
                        current_app.logger.info(f"Cleared {len(keys)} cache entries")
                    except RuntimeError:
                        print(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            try:
                current_app.logger.error(f"Redis cache clear error: {e}")
            except RuntimeError:
                print(f"Redis cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.available:
            return {
                'available': False,
                'entry_count': 0,
                'total_size_mb': 0
            }
        
        try:
            with self.lock:
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                total_size = 0
                for key in keys:
                    try:
                        cached_data = self.redis_client.get(key)
                        if cached_data:
                            cache_entry = pickle.loads(cached_data)
                            total_size += cache_entry.get('file_size', 0)
                    except Exception:
                        continue
                
                return {
                    'available': True,
                    'entry_count': len(keys),
                    'total_size_mb': total_size / (1024 * 1024),
                    'redis_info': self.redis_client.info('memory')
                }
        except Exception as e:
            try:
                current_app.logger.error(f"Redis cache stats error: {e}")
            except RuntimeError:
                print(f"Redis cache stats error: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def cleanup_expired(self):
        """Clean up expired entries (Redis handles TTL automatically)"""
        # Redis automatically handles TTL, but we can clean up orphaned files
        if not self.available:
            return
        
        try:
            with self.lock:
                pattern = f"{self.key_prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                for key in keys:
                    try:
                        cached_data = self.redis_client.get(key)
                        if cached_data:
                            cache_entry = pickle.loads(cached_data)
                            if not os.path.exists(cache_entry['file_path']):
                                self.redis_client.delete(key)
                    except Exception:
                        continue
                        
        except Exception as e:
            try:
                current_app.logger.error(f"Redis cache cleanup error: {e}")
            except RuntimeError:
                print(f"Redis cache cleanup error: {e}")


class RedisTaskManager:
    """Redis-based task management for async operations"""
    
    def __init__(self, redis_url: str = None, key_prefix: str = "tasks"):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
        self.key_prefix = key_prefix
        self.lock = threading.Lock()
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            # Test connection
            self.redis_client.ping()
            self.available = True
            try:
                current_app.logger.info("Redis task manager initialized successfully")
            except RuntimeError:
                print("Redis task manager initialized successfully")
        except Exception as e:
            try:
                current_app.logger.warning(f"Redis not available for task management: {e}")
            except RuntimeError:
                print(f"Redis not available for task management: {e}")
            self.redis_client = None
            self.available = False
    
    def create_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Create a new task in Redis"""
        if not self.available:
            return False
        
        try:
            with self.lock:
                task_info = {
                    'task_id': task_id,
                    'status': 'pending',
                    'created_at': datetime.utcnow().isoformat(),
                    'progress': 0.0,
                    'data': task_data
                }
                
                key = f"{self.key_prefix}:{task_id}"
                self.redis_client.setex(
                    key,
                    timedelta(hours=24),  # Task expires in 24 hours
                    pickle.dumps(task_info)
                )
                return True
        except Exception as e:
            try:
                current_app.logger.error(f"Redis task create error: {e}")
            except RuntimeError:
                print(f"Redis task create error: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information from Redis"""
        if not self.available:
            return None
        
        try:
            with self.lock:
                key = f"{self.key_prefix}:{task_id}"
                task_data = self.redis_client.get(key)
                if task_data:
                    return pickle.loads(task_data)
        except Exception as e:
            try:
                current_app.logger.error(f"Redis task get error: {e}")
            except RuntimeError:
                print(f"Redis task get error: {e}")
        
        return None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update task information in Redis"""
        if not self.available:
            return False
        
        try:
            with self.lock:
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
                    
                    self.redis_client.setex(
                        key,
                        timedelta(hours=24),
                        pickle.dumps(task_info)
                    )
                    return True
        except Exception as e:
            try:
                current_app.logger.error(f"Redis task update error: {e}")
            except RuntimeError:
                print(f"Redis task update error: {e}")
        
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from Redis"""
        if not self.available:
            return False
        
        try:
            with self.lock:
                key = f"{self.key_prefix}:{task_id}"
                return bool(self.redis_client.delete(key))
        except Exception as e:
            try:
                current_app.logger.error(f"Redis task delete error: {e}")
            except RuntimeError:
                print(f"Redis task delete error: {e}")
            return False
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old tasks (Redis TTL handles this automatically)"""
        # Redis automatically handles TTL, but we can add additional cleanup logic here
        pass


# Global instances
redis_cache = RedisCache()
redis_task_manager = RedisTaskManager()
