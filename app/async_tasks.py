"""
Async task management for PDF generation and other long-running operations.
"""

import os
import uuid
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from flask import current_app
import redis
from celery import Celery


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None


class TaskManager:
    """Manages background tasks for PDF generation"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.tasks: Dict[str, TaskInfo] = {}
        self.lock = threading.Lock()
        
        # Initialize Celery if Redis is available
        try:
            self.celery = Celery('pdf_generator', broker=self.redis_url)
            self.celery.conf.update(
                task_serializer='json',
                accept_content=['json'],
                result_serializer='json',
                timezone='UTC',
                enable_utc=True,
                task_track_started=True,
                task_time_limit=300,  # 5 minutes
                task_soft_time_limit=240,  # 4 minutes
            )
            self.redis_available = True
        except Exception as e:
            current_app.logger.warning(f"Redis not available, using in-memory task management: {e}")
            self.celery = None
            self.redis_available = False
    
    def create_task(self, task_type: str, request_data: Dict[str, Any]) -> str:
        """Create a new background task"""
        task_id = str(uuid.uuid4())
        
        with self.lock:
            self.tasks[task_id] = TaskInfo(
                task_id=task_id,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
                request_data=request_data
            )
        
        # Start the task
        if self.redis_available and self.celery:
            # Use Celery for distributed task processing
            if task_type == 'pdf_generation':
                self.celery.send_task('pdf_generation_task', args=[task_id, request_data])
            elif task_type == 'pdf_offset':
                self.celery.send_task('pdf_offset_task', args=[task_id, request_data])
        else:
            # Use threading for local processing
            thread = threading.Thread(target=self._run_task, args=(task_id, task_type))
            thread.daemon = True
            thread.start()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get the status of a task"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def update_task_progress(self, task_id: str, progress: float, status: TaskStatus = None):
        """Update task progress"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].progress = progress
                if status:
                    self.tasks[task_id].status = status
                    if status == TaskStatus.RUNNING and not self.tasks[task_id].started_at:
                        self.tasks[task_id].started_at = datetime.utcnow()
                    elif status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED]:
                        self.tasks[task_id].completed_at = datetime.utcnow()
    
    def complete_task(self, task_id: str, result: Dict[str, Any] = None, error: str = None):
        """Mark a task as completed"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].completed_at = datetime.utcnow()
                if error:
                    self.tasks[task_id].status = TaskStatus.FAILURE
                    self.tasks[task_id].error = error
                else:
                    self.tasks[task_id].status = TaskStatus.SUCCESS
                    self.tasks[task_id].result = result
                self.tasks[task_id].progress = 100.0
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id].status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                self.tasks[task_id].status = TaskStatus.CANCELLED
                self.tasks[task_id].completed_at = datetime.utcnow()
                return True
        return False
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self.lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED] 
                    and task.completed_at and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
    
    def _run_task(self, task_id: str, task_type: str):
        """Run a task in a separate thread"""
        try:
            self.update_task_progress(task_id, 0.0, TaskStatus.RUNNING)
            
            if task_type == 'pdf_generation':
                self._run_pdf_generation_task(task_id)
            elif task_type == 'pdf_offset':
                self._run_pdf_offset_task(task_id)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
                
        except Exception as e:
            current_app.logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
            self.complete_task(task_id, error=str(e))
    
    def _run_pdf_generation_task(self, task_id: str):
        """Run PDF generation task"""
        task_info = self.get_task_status(task_id)
        if not task_info:
            return
        
        request_data = task_info.request_data
        
        try:
            # Import here to avoid circular imports
            from app.utils import create_temp_directories, save_uploaded_files, cleanup_temp_directory
            from utilities import CardSize, PaperSize, generate_pdf
            
            self.update_task_progress(task_id, 10.0)
            
            # Create temporary directories
            temp_dir, front_dir, back_dir, double_sided_dir, output_dir, _ = create_temp_directories()
            
            self.update_task_progress(task_id, 20.0)
            
            # Process uploaded files (this would need to be adapted for async)
            # For now, we'll assume files are already saved
            
            self.update_task_progress(task_id, 30.0)
            
            # Generate PDF
            card_size = CardSize(request_data.get('card_size', CardSize.STANDARD.value))
            paper_size = PaperSize(request_data.get('paper_size', PaperSize.LETTER.value))
            
            output_path = os.path.join(output_dir, 'cards.pdf')
            
            generate_pdf(
                front_dir_path=front_dir,
                back_dir_path=back_dir,
                double_sided_dir_path=double_sided_dir,
                output_path=output_path,
                output_images=request_data.get('output_images', False),
                card_size=card_size,
                paper_size=paper_size,
                only_fronts=request_data.get('only_fronts', False),
                crop_string=request_data.get('crop'),
                extend_corners=request_data.get('extend_corners', 0),
                ppi=request_data.get('ppi', 300),
                quality=request_data.get('quality', 75),
                skip_indices=request_data.get('skip_indices', []),
                load_offset=request_data.get('load_offset', False),
                name=request_data.get('name')
            )
            
            self.update_task_progress(task_id, 90.0)
            
            # Store result
            result = {
                'output_path': output_path,
                'temp_dir': temp_dir,  # Keep temp dir for file serving
                'file_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0
            }
            
            self.complete_task(task_id, result=result)
            
        except Exception as e:
            self.complete_task(task_id, error=str(e))
    
    def _run_pdf_offset_task(self, task_id: str):
        """Run PDF offset task"""
        # Implementation for PDF offset task
        pass


# Global task manager instance
task_manager = TaskManager()


# Celery task definitions (if Redis is available)
if task_manager.redis_available:
    @task_manager.celery.task(bind=True)
    def pdf_generation_task(self, task_id: str, request_data: Dict[str, Any]):
        """Celery task for PDF generation"""
        try:
            # Update task progress
            self.update_state(state='PROGRESS', meta={'progress': 0})
            
            # Run the actual PDF generation
            task_manager._run_pdf_generation_task(task_id)
            
            return {'status': 'completed', 'task_id': task_id}
        except Exception as e:
            self.update_state(state='FAILURE', meta={'error': str(e)})
            raise
    
    @task_manager.celery.task(bind=True)
    def pdf_offset_task(self, task_id: str, request_data: Dict[str, Any]):
        """Celery task for PDF offset"""
        try:
            self.update_state(state='PROGRESS', meta={'progress': 0})
            task_manager._run_pdf_offset_task(task_id)
            return {'status': 'completed', 'task_id': task_id}
        except Exception as e:
            self.update_state(state='FAILURE', meta={'error': str(e)})
            raise
