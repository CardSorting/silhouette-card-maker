#!/usr/bin/env python3
"""
Comprehensive Celery application configuration and worker management for Silhouette Card Maker.
"""

import os
import sys
import logging
import threading
import time
import signal
from datetime import timedelta
from dotenv import load_dotenv
from celery import Celery
from celery.signals import worker_ready, worker_shutdown, worker_process_init
from celery.events.state import State
from celery.events import EventReceiver
import redis

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

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
REDIS_HOST = os.getenv('REDIS_HOST', '108.175.14.173')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'MyStrongPassword123!')
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Create Celery app
celery_app = Celery('silhouette_card_maker')

# Comprehensive Celery configuration
celery_app.conf.update(
    # Broker and result backend
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_accept_content=['json'],
    
    # Timezone and UTC
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_disable_rate_limits=True,
    
    # Task routing
    task_routes={
        'pdf_generation_task': {'queue': 'pdf_generation'},
        'pdf_offset_task': {'queue': 'pdf_offset'},
        'health_check_task': {'queue': 'default'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'pdf_generation': {
            'exchange': 'pdf_generation',
            'routing_key': 'pdf_generation',
        },
        'pdf_offset': {
            'exchange': 'pdf_offset',
            'routing_key': 'pdf_offset',
        },
    },
    
    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=200000,  # 200MB
    worker_direct=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Result backend configuration
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Monitoring and events
    worker_send_task_events=True,
    task_send_sent_event=True,
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Performance
    task_compression='gzip',
    result_compression='gzip',
    task_ignore_result=False,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'health-check': {
            'task': 'health_check_task',
            'schedule': 60.0,  # Every minute
        },
    },
)

# Signal handlers for comprehensive worker management
@worker_process_init.connect
def worker_process_init_handler(sender=None, **kwargs):
    """Called when a worker process is initialized"""
    logger.info("🔧 Worker process initialized")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Worker received signal {signum}, initiating graceful shutdown...")
        # The worker will handle graceful shutdown automatically
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Called when a worker is ready to accept tasks"""
    logger.info("🎉 Celery worker is ready to accept tasks")
    logger.info(f"   Worker: {sender}")
    logger.info(f"   Queues: {celery_app.conf.task_queues}")
    logger.info(f"   Concurrency: {kwargs.get('concurrency', 'unknown')}")

@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Called when a worker is shutting down"""
    logger.info("👋 Celery worker is shutting down")
    logger.info(f"   Worker: {sender}")

# Task definitions with comprehensive error handling
@celery_app.task(bind=True, name='health_check_task')
def health_check_task(self):
    """Periodic health check task"""
    try:
        # Test Redis connection
        r = redis.Redis.from_url(REDIS_URL)
        r.ping()
        
        # Test database connection
        from app.database import get_database_uri
        from sqlalchemy import create_engine, text
        
        engine = create_engine(get_database_uri())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("✅ Health check passed")
        return {'status': 'healthy', 'timestamp': time.time()}
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(bind=True, name='pdf_generation_task')
def pdf_generation_task(self, task_id: str, request_data: dict):
    """Enhanced PDF generation task with comprehensive error handling"""
    try:
        logger.info(f"🔄 Starting PDF generation task {task_id}")
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Initializing'})
        
        # Import task manager
        from app.async_tasks import task_manager
        
        # Update task status in Redis
        task_manager.update_task_progress(task_id, 0.0, task_manager.TaskStatus.RUNNING)
        
        # Run the actual PDF generation
        task_manager._run_pdf_generation_task(task_id)
        
        logger.info(f"✅ PDF generation task {task_id} completed successfully")
        return {'status': 'completed', 'task_id': task_id, 'timestamp': time.time()}
        
    except Exception as e:
        logger.error(f"❌ PDF generation task {task_id} failed: {e}")
        
        # Update task status in Redis
        try:
            from app.async_tasks import task_manager
            task_manager.complete_task(task_id, error=str(e))
        except:
            pass
        
        # Retry logic for transient failures
        if self.request.retries < 2:
            logger.info(f"🔄 Retrying PDF generation task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30, max_retries=2)
        else:
            raise

@celery_app.task(bind=True, name='pdf_offset_task')
def pdf_offset_task(self, task_id: str, request_data: dict):
    """Enhanced PDF offset task with comprehensive error handling"""
    try:
        logger.info(f"🔄 Starting PDF offset task {task_id}")
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Initializing'})
        
        # Import task manager
        from app.async_tasks import task_manager
        
        # Update task status in Redis
        task_manager.update_task_progress(task_id, 0.0, task_manager.TaskStatus.RUNNING)
        
        # Run the actual PDF offset task
        task_manager._run_pdf_offset_task(task_id)
        
        logger.info(f"✅ PDF offset task {task_id} completed successfully")
        return {'status': 'completed', 'task_id': task_id, 'timestamp': time.time()}
        
    except Exception as e:
        logger.error(f"❌ PDF offset task {task_id} failed: {e}")
        
        # Update task status in Redis
        try:
            from app.async_tasks import task_manager
            task_manager.complete_task(task_id, error=str(e))
        except:
            pass
        
        # Retry logic for transient failures
        if self.request.retries < 2:
            logger.info(f"🔄 Retrying PDF offset task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30, max_retries=2)
        else:
            raise

# Import original task definitions for compatibility
try:
    from app.async_tasks import pdf_generation_task as original_pdf_generation_task
    from app.async_tasks import pdf_offset_task as original_pdf_offset_task
except ImportError:
    logger.warning("Could not import original task definitions from app.async_tasks")

# Import the comprehensive worker manager
from app.celery_manager import worker_manager

def start_celery_worker_standalone():
    """Start Celery worker as a standalone process"""
    try:
        logger.info("🚀 Starting standalone Celery worker...")
        logger.info(f"✅ Redis URL: {REDIS_URL}")
        logger.info("✅ Celery worker will process PDF generation and offset tasks")
        logger.info("   Press Ctrl+C to stop the worker")
        logger.info("")
        
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',
            '--queues=pdf_generation,pdf_offset,default',
            '--hostname=worker@%h'
        ])
        
    except KeyboardInterrupt:
        logger.info("👋 Celery worker stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Failed to start Celery worker: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(start_celery_worker_standalone())
