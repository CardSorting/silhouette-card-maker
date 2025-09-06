#!/usr/bin/env python3
"""
Production startup script with integrated Celery worker management.
This script starts both the Flask application and Celery workers with proper signal handling.
"""

import os
import sys
import signal
import logging
import threading
import time
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

# Global variables for graceful shutdown
flask_app = None
celery_worker_manager = None
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()
    
    # Stop Celery worker
    if celery_worker_manager:
        logger.info("Stopping Celery worker...")
        celery_worker_manager.stop_worker()
    
    # Stop Flask app
    if flask_app:
        logger.info("Stopping Flask application...")
        # Flask will handle its own shutdown
    
    logger.info("Graceful shutdown completed")
    sys.exit(0)


def start_celery_worker():
    """Start Celery worker in a separate thread"""
    global celery_worker_manager
    
    try:
        from app.celery_manager import CeleryWorkerManager
        
        # Create worker manager
        celery_worker_manager = CeleryWorkerManager(auto_start=False)
        
        # Configure worker
        concurrency = int(os.environ.get('CELERY_CONCURRENCY', 2))
        queues = os.environ.get('CELERY_QUEUES', 'pdf_generation,pdf_offset,default').split(',')
        hostname = f"worker@{os.uname().nodename if hasattr(os, 'uname') else 'localhost'}"
        
        logger.info("🚀 Starting Celery worker...")
        logger.info(f"   Concurrency: {concurrency}")
        logger.info(f"   Queues: {', '.join(queues)}")
        logger.info(f"   Hostname: {hostname}")
        
        success = celery_worker_manager.start_worker(
            concurrency=concurrency,
            queues=queues,
            hostname=hostname,
            loglevel='info'
        )
        
        if success:
            logger.info("✅ Celery worker started successfully")
            
            # Monitor worker health
            while not shutdown_event.is_set():
                if not celery_worker_manager.is_worker_healthy():
                    logger.warning("⚠️ Celery worker is not healthy, attempting restart...")
                    celery_worker_manager.restart_worker()
                
                shutdown_event.wait(30)  # Check every 30 seconds
            
        else:
            logger.error("❌ Failed to start Celery worker")
            
    except Exception as e:
        logger.error(f"❌ Error in Celery worker thread: {e}")
        import traceback
        traceback.print_exc()


def start_flask_app():
    """Start Flask application"""
    global flask_app
    
    try:
        from app import create_app
        
        # Set environment for production
        os.environ['FLASK_ENV'] = 'production'
        os.environ['START_CELERY_WORKER'] = 'false'  # We're managing it separately
        
        logger.info("🚀 Starting Flask application...")
        
        # Create Flask app
        flask_app = create_app()
        
        # Get configuration
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_ENV', 'production') == 'development'
        
        logger.info(f"✅ Flask application starting on {host}:{port}")
        logger.info(f"   Debug mode: {debug}")
        
        # Start Flask app
        flask_app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except Exception as e:
        logger.error(f"❌ Error starting Flask application: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main startup function"""
    try:
        logger.info("🎉 Starting Silhouette Card Maker with integrated Celery worker...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start Celery worker in a separate thread
        celery_thread = threading.Thread(target=start_celery_worker, daemon=True)
        celery_thread.start()
        
        # Wait a moment for Celery worker to start
        time.sleep(3)
        
        # Start Flask application (this will block)
        start_flask_app()
        
    except KeyboardInterrupt:
        logger.info("👋 Application stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
