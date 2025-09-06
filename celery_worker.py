#!/usr/bin/env python3
"""
Celery worker startup script for the Silhouette Card Maker application.
This script starts Celery workers that can process background tasks.
"""

import os
import sys
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

def start_celery_worker():
    """Start Celery worker with proper configuration"""
    try:
        # Import Celery app from async_tasks
        from app.async_tasks import task_manager
        
        if not task_manager.celery_available:
            logger.error("❌ Celery is not available. Redis connection may be down.")
            return 1
        
        logger.info("🚀 Starting Celery worker for Silhouette Card Maker...")
        logger.info(f"✅ Redis URL: {task_manager.redis_url}")
        logger.info("✅ Celery worker will process PDF generation and offset tasks")
        logger.info("   Press Ctrl+C to stop the worker")
        logger.info("")
        
        # Start the Celery worker
        from celery import current_app
        current_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',  # Adjust based on your server capacity
            '--queues=pdf_generation,default',
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
    sys.exit(start_celery_worker())
