"""
Performance optimization utilities for the Silhouette Card Maker API.
"""

import os
import gc
import psutil
import threading
from functools import wraps
from flask import current_app


def monitor_memory_usage():
    """Monitor current memory usage"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        'rss': memory_info.rss,  # Resident Set Size
        'vms': memory_info.vms,  # Virtual Memory Size
        'percent': process.memory_percent()
    }


def cleanup_memory():
    """Force garbage collection to free up memory"""
    gc.collect()


def memory_aware(func):
    """Decorator to monitor and manage memory usage during PDF generation"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Log initial memory usage
        initial_memory = monitor_memory_usage()
        current_app.logger.info(f'Initial memory usage: {initial_memory["percent"]:.1f}%')
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Clean up memory after operation
            cleanup_memory()
            
            # Log final memory usage
            final_memory = monitor_memory_usage()
            current_app.logger.info(f'Final memory usage: {final_memory["percent"]:.1f}%')
            
            # Log memory difference
            memory_diff = final_memory['rss'] - initial_memory['rss']
            current_app.logger.info(f'Memory difference: {memory_diff / 1024 / 1024:.1f} MB')
    
    return wrapper


def optimize_image_processing():
    """Optimize image processing settings based on available memory"""
    memory = monitor_memory_usage()
    
    if memory['percent'] > 80:
        # High memory usage - use more conservative settings
        return {
            'quality': 75,
            'optimize': True,
            'progressive': True
        }
    elif memory['percent'] > 60:
        # Medium memory usage - balanced settings
        return {
            'quality': 85,
            'optimize': True,
            'progressive': False
        }
    else:
        # Low memory usage - high quality settings
        return {
            'quality': 95,
            'optimize': False,
            'progressive': False
        }


class PerformanceMonitor:
    """Monitor API performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'avg_response_time': 0,
            'memory_usage_history': []
        }
        self.lock = threading.Lock()
    
    def record_request(self, success=True, response_time=0):
        """Record a request metric"""
        with self.lock:
            self.metrics['requests_total'] += 1
            if success:
                self.metrics['requests_successful'] += 1
            else:
                self.metrics['requests_failed'] += 1
            
            # Update average response time
            total_requests = self.metrics['requests_total']
            current_avg = self.metrics['avg_response_time']
            self.metrics['avg_response_time'] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
    
    def record_memory_usage(self):
        """Record current memory usage"""
        memory = monitor_memory_usage()
        with self.lock:
            self.metrics['memory_usage_history'].append({
                'timestamp': memory,
                'usage': memory['percent']
            })
            # Keep only last 100 measurements
            if len(self.metrics['memory_usage_history']) > 100:
                self.metrics['memory_usage_history'] = self.metrics['memory_usage_history'][-100:]
    
    def get_metrics(self):
        """Get current performance metrics"""
        with self.lock:
            return self.metrics.copy()


# Global performance monitor
performance_monitor = PerformanceMonitor()


def track_performance(func):
    """Decorator to track API performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        success = True
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            response_time = time.time() - start_time
            performance_monitor.record_request(success=success, response_time=response_time)
            performance_monitor.record_memory_usage()
    
    return wrapper
