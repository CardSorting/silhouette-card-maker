"""
API routes for Celery worker management and monitoring.
"""

import os
import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.auth import admin_required

logger = logging.getLogger(__name__)

# Create blueprint
celery_bp = Blueprint('celery', __name__, url_prefix='/celery')


@celery_bp.route('/status', methods=['GET'])
@jwt_required()
@admin_required
def get_worker_status():
    """Get comprehensive Celery worker status"""
    try:
        from app.celery_manager import worker_manager
        
        status = worker_manager.get_worker_status()
        
        return jsonify({
            'success': True,
            'worker_status': status,
            'healthy': worker_manager.is_worker_healthy(),
            'auto_start_enabled': os.environ.get('START_CELERY_WORKER', 'false').lower() == 'true'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'worker_status': None,
            'healthy': False
        }), 500


@celery_bp.route('/start', methods=['POST'])
@jwt_required()
@admin_required
def start_worker():
    """Start Celery worker"""
    try:
        from app.celery_manager import worker_manager
        
        # Get parameters from request
        data = request.get_json() or {}
        concurrency = data.get('concurrency', 2)
        queues = data.get('queues', ['pdf_generation', 'pdf_offset', 'default'])
        hostname = data.get('hostname', f"worker@{os.uname().nodename if hasattr(os, 'uname') else 'localhost'}")
        
        success = worker_manager.start_worker(
            concurrency=concurrency,
            queues=queues,
            hostname=hostname,
            loglevel='info'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Celery worker started successfully',
                'worker_info': worker_manager.get_worker_status()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start Celery worker'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting worker: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@celery_bp.route('/stop', methods=['POST'])
@jwt_required()
@admin_required
def stop_worker():
    """Stop Celery worker"""
    try:
        from app.celery_manager import worker_manager
        
        timeout = request.get_json().get('timeout', 30) if request.get_json() else 30
        
        success = worker_manager.stop_worker(timeout=timeout)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Celery worker stopped successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop Celery worker'
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping worker: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@celery_bp.route('/restart', methods=['POST'])
@jwt_required()
@admin_required
def restart_worker():
    """Restart Celery worker"""
    try:
        from app.celery_manager import worker_manager
        
        success = worker_manager.restart_worker()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Celery worker restarted successfully',
                'worker_info': worker_manager.get_worker_status()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to restart Celery worker'
            }), 500
            
    except Exception as e:
        logger.error(f"Error restarting worker: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@celery_bp.route('/health', methods=['GET'])
def worker_health():
    """Get worker health status (public endpoint)"""
    try:
        from app.celery_manager import worker_manager
        
        is_healthy = worker_manager.is_worker_healthy()
        status = worker_manager.get_worker_status()
        
        return jsonify({
            'healthy': is_healthy,
            'status': status.get('status', 'unknown'),
            'uptime_seconds': status.get('uptime_seconds', 0),
            'restart_count': status.get('restart_count', 0)
        }), 200 if is_healthy else 503
        
    except Exception as e:
        logger.error(f"Error checking worker health: {e}")
        return jsonify({
            'healthy': False,
            'error': str(e)
        }), 503


@celery_bp.route('/tasks', methods=['GET'])
@jwt_required()
@admin_required
def get_active_tasks():
    """Get information about active Celery tasks"""
    try:
        from celery_app import celery_app
        
        # Get active tasks
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        
        return jsonify({
            'success': True,
            'active_tasks': active_tasks or {},
            'scheduled_tasks': scheduled_tasks or {},
            'reserved_tasks': reserved_tasks or {}
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@celery_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_worker_stats():
    """Get detailed worker statistics"""
    try:
        from celery_app import celery_app
        
        # Get worker stats
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        return jsonify({
            'success': True,
            'worker_stats': stats or {}
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting worker stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@celery_bp.route('/purge', methods=['POST'])
@jwt_required()
@admin_required
def purge_queues():
    """Purge all task queues"""
    try:
        from celery_app import celery_app
        
        data = request.get_json() or {}
        queues = data.get('queues', ['pdf_generation', 'pdf_offset', 'default'])
        
        purged_queues = {}
        for queue in queues:
            try:
                purged_count = celery_app.control.purge()
                purged_queues[queue] = purged_count
            except Exception as e:
                purged_queues[queue] = f"Error: {str(e)}"
        
        return jsonify({
            'success': True,
            'message': 'Queues purged successfully',
            'purged_queues': purged_queues
        }), 200
        
    except Exception as e:
        logger.error(f"Error purging queues: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
