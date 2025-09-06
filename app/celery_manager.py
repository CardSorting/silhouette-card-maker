"""
Comprehensive Celery worker management system for Silhouette Card Maker.
Handles worker lifecycle, health monitoring, and graceful shutdown.
"""

import os
import sys
import time
import signal
import logging
import threading
import subprocess
import psutil
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class WorkerInfo:
    """Information about a worker process"""
    pid: Optional[int] = None
    status: WorkerStatus = WorkerStatus.STOPPED
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    restart_count: int = 0
    last_error: Optional[str] = None
    concurrency: int = 2
    queues: List[str] = None
    hostname: str = "worker@%h"
    
    def __post_init__(self):
        if self.queues is None:
            self.queues = ['pdf_generation', 'pdf_offset', 'default']


class CeleryWorkerManager:
    """
    Comprehensive Celery worker manager with lifecycle management,
    health monitoring, and graceful shutdown capabilities.
    """
    
    def __init__(self, redis_url: str = None, auto_start: bool = False):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://:MyStrongPassword123!@108.175.14.173:6379/0')
        self.auto_start = auto_start
        self.worker_info = WorkerInfo()
        self.worker_process: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.lock = threading.Lock()
        
        # Configuration
        self.max_restarts = int(os.getenv('CELERY_MAX_RESTARTS', 5))
        self.restart_delay = int(os.getenv('CELERY_RESTART_DELAY', 5))
        self.health_check_interval = int(os.getenv('CELERY_HEALTH_CHECK_INTERVAL', 30))
        self.worker_timeout = int(os.getenv('CELERY_WORKER_TIMEOUT', 300))
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Start monitoring if auto_start is enabled
        if self.auto_start:
            self.start_worker()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.stop_worker()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start_worker(self, concurrency: int = 2, queues: List[str] = None, 
                    hostname: str = "worker@%h", loglevel: str = "info") -> bool:
        """
        Start Celery worker with comprehensive configuration
        """
        with self.lock:
            if self.worker_info.status in [WorkerStatus.RUNNING, WorkerStatus.STARTING]:
                logger.warning("Worker is already running or starting")
                return False
            
            try:
                logger.info("🚀 Starting Celery worker...")
                self.worker_info.status = WorkerStatus.STARTING
                self.worker_info.concurrency = concurrency
                self.worker_info.queues = queues or ['pdf_generation', 'pdf_offset', 'default']
                self.worker_info.hostname = hostname
                
                # Build Celery worker command
                cmd = [
                    sys.executable, '-m', 'celery',
                    'worker',
                    '--app=celery_app:celery_app',
                    f'--loglevel={loglevel}',
                    f'--concurrency={concurrency}',
                    f'--hostname={hostname}',
                    '--queues=' + ','.join(self.worker_info.queues),
                    '--without-gossip',
                    '--without-mingle',
                    '--without-heartbeat',
                    '--time-limit=300',
                    '--soft-time-limit=240',
                    '--max-tasks-per-child=1000',
                    '--prefetch-multiplier=1',
                    '--task-acks-late',
                    '--worker-disable-rate-limits'
                ]
                
                # Start worker process
                self.worker_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
                
                self.worker_info.pid = self.worker_process.pid
                self.worker_info.started_at = datetime.utcnow()
                self.worker_info.last_heartbeat = datetime.utcnow()
                
                # Start monitoring thread
                if not self.monitor_thread or not self.monitor_thread.is_alive():
                    self.monitor_thread = threading.Thread(
                        target=self._monitor_worker,
                        daemon=True
                    )
                    self.monitor_thread.start()
                
                # Wait a moment to check if worker started successfully
                time.sleep(2)
                
                if self.worker_process.poll() is None:
                    self.worker_info.status = WorkerStatus.RUNNING
                    logger.info(f"✅ Celery worker started successfully (PID: {self.worker_info.pid})")
                    return True
                else:
                    self.worker_info.status = WorkerStatus.FAILED
                    logger.error("❌ Celery worker failed to start")
                    return False
                    
            except Exception as e:
                self.worker_info.status = WorkerStatus.FAILED
                self.worker_info.last_error = str(e)
                logger.error(f"❌ Failed to start Celery worker: {e}")
                return False
    
    def stop_worker(self, timeout: int = 30) -> bool:
        """
        Stop Celery worker gracefully with timeout
        """
        with self.lock:
            if self.worker_info.status not in [WorkerStatus.RUNNING, WorkerStatus.STARTING]:
                logger.info("Worker is not running")
                return True
            
            try:
                logger.info("🛑 Stopping Celery worker...")
                self.worker_info.status = WorkerStatus.STOPPING
                self.shutdown_event.set()
                
                if self.worker_process:
                    # Send SIGTERM for graceful shutdown
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self.worker_process.pid), signal.SIGTERM)
                    else:
                        self.worker_process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        self.worker_process.wait(timeout=timeout)
                        logger.info("✅ Celery worker stopped gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning("⚠️ Worker didn't stop gracefully, forcing shutdown...")
                        if os.name != 'nt':
                            os.killpg(os.getpgid(self.worker_process.pid), signal.SIGKILL)
                        else:
                            self.worker_process.kill()
                        self.worker_process.wait()
                        logger.info("✅ Celery worker force-stopped")
                
                self.worker_info.status = WorkerStatus.STOPPED
                self.worker_info.pid = None
                self.worker_process = None
                return True
                
            except Exception as e:
                logger.error(f"❌ Error stopping Celery worker: {e}")
                self.worker_info.status = WorkerStatus.FAILED
                return False
    
    def restart_worker(self) -> bool:
        """Restart the Celery worker"""
        logger.info("🔄 Restarting Celery worker...")
        
        if self.worker_info.restart_count >= self.max_restarts:
            logger.error(f"❌ Maximum restart attempts ({self.max_restarts}) exceeded")
            self.worker_info.status = WorkerStatus.FAILED
            return False
        
        # Stop current worker
        if not self.stop_worker():
            logger.warning("⚠️ Failed to stop worker before restart")
        
        # Wait before restarting
        time.sleep(self.restart_delay)
        
        # Start new worker
        success = self.start_worker(
            concurrency=self.worker_info.concurrency,
            queues=self.worker_info.queues,
            hostname=self.worker_info.hostname
        )
        
        if success:
            self.worker_info.restart_count += 1
            logger.info(f"✅ Worker restarted successfully (restart #{self.worker_info.restart_count})")
        else:
            logger.error("❌ Failed to restart worker")
        
        return success
    
    def _monitor_worker(self):
        """Monitor worker health and restart if needed"""
        logger.info("🔍 Starting worker health monitoring...")
        
        while not self.shutdown_event.is_set():
            try:
                with self.lock:
                    if self.worker_info.status == WorkerStatus.RUNNING and self.worker_process:
                        # Check if process is still alive
                        if self.worker_process.poll() is not None:
                            logger.warning("⚠️ Worker process died unexpectedly")
                            self.worker_info.status = WorkerStatus.FAILED
                            
                            # Attempt restart
                            if self.worker_info.restart_count < self.max_restarts:
                                logger.info("🔄 Attempting to restart worker...")
                                threading.Thread(target=self.restart_worker, daemon=True).start()
                            else:
                                logger.error("❌ Maximum restart attempts exceeded, worker will not restart")
                                break
                        
                        # Update heartbeat
                        self.worker_info.last_heartbeat = datetime.utcnow()
                        
                        # Check for worker timeout
                        if (self.worker_info.started_at and 
                            datetime.utcnow() - self.worker_info.started_at > timedelta(seconds=self.worker_timeout)):
                            logger.warning("⚠️ Worker has been running for too long, restarting...")
                            threading.Thread(target=self.restart_worker, daemon=True).start()
                
                # Sleep until next health check
                self.shutdown_event.wait(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in worker monitoring: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info("🔍 Worker monitoring stopped")
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get comprehensive worker status information"""
        with self.lock:
            status = asdict(self.worker_info)
            status['status'] = self.worker_info.status.value
            
            # Add process information if running
            if self.worker_process and self.worker_info.pid:
                try:
                    process = psutil.Process(self.worker_info.pid)
                    status['process_info'] = {
                        'cpu_percent': process.cpu_percent(),
                        'memory_info': process.memory_info()._asdict(),
                        'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                        'status': process.status()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    status['process_info'] = None
            
            # Add uptime
            if self.worker_info.started_at:
                uptime = datetime.utcnow() - self.worker_info.started_at
                status['uptime_seconds'] = uptime.total_seconds()
            
            return status
    
    def is_worker_healthy(self) -> bool:
        """Check if worker is healthy and responsive"""
        with self.lock:
            if self.worker_info.status != WorkerStatus.RUNNING:
                return False
            
            if not self.worker_process or self.worker_process.poll() is not None:
                return False
            
            # Check if heartbeat is recent
            if (self.worker_info.last_heartbeat and 
                datetime.utcnow() - self.worker_info.last_heartbeat > timedelta(seconds=60)):
                return False
            
            return True
    
    def cleanup(self):
        """Cleanup resources and stop worker"""
        logger.info("🧹 Cleaning up Celery worker manager...")
        self.shutdown_event.set()
        self.stop_worker()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)


# Global worker manager instance
worker_manager = CeleryWorkerManager(
    auto_start=os.getenv('START_CELERY_WORKER', 'false').lower() == 'true'
)
