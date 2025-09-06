"""
Optimized API routes for PDF generation with enhanced performance features.
"""

import os
import uuid
import time
from datetime import datetime
from flask import request, send_file, jsonify, current_app, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.api import bp
from app.utils import create_temp_directories, save_uploaded_files, cleanup_temp_directory
from app.performance import memory_aware, track_performance, performance_monitor, monitor_memory_usage
from app.auth import require_user, require_admin, get_current_user
from app.async_tasks import task_manager, TaskStatus
from app.pdf_service import pdf_service
from utilities import CardSize, PaperSize


# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)


@bp.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check with performance metrics"""
    memory_usage = monitor_memory_usage()
    metrics = performance_monitor.get_metrics()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.1.0',
        'service': 'Silhouette Card Maker API (Optimized)',
        'memory_usage': memory_usage,
        'performance_metrics': {
            'total_requests': metrics['requests_total'],
            'success_rate': metrics['requests_successful'] / max(metrics['requests_total'], 1) * 100,
            'avg_response_time': metrics['avg_response_time']
        }
    })


@bp.route('/config', methods=['GET'])
def get_config():
    """Get available configuration options with optimization info"""
    return jsonify({
        'card_sizes': [size.value for size in CardSize],
        'paper_sizes': [size.value for size in PaperSize],
        'max_file_size': current_app.config['MAX_CONTENT_LENGTH'],
        'allowed_extensions': list(current_app.config['ALLOWED_EXTENSIONS']),
        'plugin_games': current_app.config.get('PLUGIN_GAMES', {}),
        'optimization_features': {
            'async_generation': True,
            'streaming_output': True,
            'caching': True,
            'parallel_processing': True,
            'memory_optimization': True,
            'progress_tracking': True
        },
        'rate_limits': {
            'requests_per_hour': 1000,
            'requests_per_minute': 100
        }
    })


@bp.route('/generate', methods=['POST'])
@require_user
@track_performance
@memory_aware
@limiter.limit("10 per minute")
def api_generate_optimized():
    """Optimized API endpoint for PDF generation"""
    request_id = str(uuid.uuid4())
    
    try:
        # Validate request
        if not request.files:
            return jsonify({
                'error': 'No files provided',
                'code': 'NO_FILES',
                'request_id': request_id
            }), 400
        
        # Get form data with enhanced validation
        try:
            request_data = {
                'card_size': request.form.get('card_size', CardSize.STANDARD.value),
                'paper_size': request.form.get('paper_size', PaperSize.LETTER.value),
                'only_fronts': request.form.get('only_fronts', 'false').lower() == 'true',
                'crop': request.form.get('crop', '').strip() or None,
                'extend_corners': int(request.form.get('extend_corners', 0)),
                'ppi': int(request.form.get('ppi', 300)),
                'quality': int(request.form.get('quality', 75)),
                'skip_indices_str': request.form.get('skip_indices', '').strip(),
                'name': request.form.get('name', '').strip() or None,
                'output_images': request.form.get('output_images', 'false').lower() == 'true',
                'load_offset': request.form.get('load_offset', 'false').lower() == 'true',
                'use_cache': request.form.get('use_cache', 'true').lower() == 'true',
                'stream_output': request.form.get('stream_output', 'false').lower() == 'true',
                'async_generation': request.form.get('async_generation', 'false').lower() == 'true'
            }
            
            # Parse skip indices
            skip_indices = []
            if request_data['skip_indices_str']:
                skip_indices = [int(x.strip()) for x in request_data['skip_indices_str'].split(',') if x.strip().isdigit()]
            request_data['skip_indices'] = skip_indices
            
            # Validate ranges
            if not (1 <= request_data['ppi'] <= 600):
                raise ValueError("PPI must be between 1 and 600")
            if not (1 <= request_data['quality'] <= 100):
                raise ValueError("Quality must be between 1 and 100")
            if not (0 <= request_data['extend_corners'] <= 50):
                raise ValueError("Extend corners must be between 0 and 50")
                
        except (ValueError, TypeError) as e:
            return jsonify({
                'error': f'Invalid parameter: {str(e)}',
                'code': 'INVALID_PARAMETER',
                'request_id': request_id
            }), 400
        
        # Validate card and paper sizes
        try:
            card_size_enum = CardSize(request_data['card_size'])
            paper_size_enum = PaperSize(request_data['paper_size'])
        except ValueError as e:
            return jsonify({
                'error': f'Invalid size: {str(e)}',
                'code': 'INVALID_SIZE',
                'request_id': request_id
            }), 400
        
        # Handle file uploads
        files = {
            'front_files': request.files.getlist('front_files'),
            'back_files': request.files.getlist('back_files'),
            'double_sided_files': request.files.getlist('double_sided_files')
        }
        
        # Check if we have front files
        if not files['front_files'] or not any(f.filename for f in files['front_files']):
            return jsonify({
                'error': 'No valid front images provided',
                'code': 'NO_FRONT_IMAGES',
                'request_id': request_id
            }), 400
        
        # Handle async generation
        if request_data['async_generation']:
            task_id = task_manager.create_task('pdf_generation', {
                **request_data,
                'files': files
            })
            
            return jsonify({
                'success': True,
                'message': 'PDF generation started',
                'task_id': task_id,
                'status_url': f'/api/tasks/{task_id}',
                'request_id': request_id
            }), 202
        
        # Synchronous generation with optimizations
        result = pdf_service.generate_pdf_optimized(
            request_data=request_data,
            files=files,
            use_cache=request_data['use_cache'],
            stream_output=request_data['stream_output']
        )
        
        if result['success']:
            if result.get('streaming'):
                # Return streaming response for large files
                filename = f"{request_data['name'] or 'cards'}.pdf"
                return pdf_service.create_streaming_response(result['file_path'], filename)
            else:
                # Return regular file response
                filename = f"{request_data['name'] or 'cards'}.pdf"
                return send_file(
                    result['file_path'],
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf'
                )
        else:
            return jsonify({
                'error': 'PDF generation failed',
                'code': 'GENERATION_ERROR',
                'request_id': request_id
            }), 500
    
    except RequestEntityTooLarge:
        return jsonify({
            'error': 'File too large. Maximum file size exceeded.',
            'code': 'FILE_TOO_LARGE',
            'request_id': request_id
        }), 413
    
    except BadRequest as e:
        return jsonify({
            'error': f'Bad request: {str(e)}',
            'code': 'BAD_REQUEST',
            'request_id': request_id
        }), 400
    
    except Exception as e:
        current_app.logger.error(f'PDF generation failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Internal server error during PDF generation',
            'code': 'GENERATION_ERROR',
            'request_id': request_id
        }), 500


@bp.route('/tasks/<task_id>', methods=['GET'])
@require_user
def get_task_status(task_id: str):
    """Get the status of an async task"""
    task_info = task_manager.get_task_status(task_id)
    
    if not task_info:
        return jsonify({
            'error': 'Task not found',
            'code': 'TASK_NOT_FOUND'
        }), 404
    
    response_data = {
        'task_id': task_info.task_id,
        'status': task_info.status.value,
        'progress': task_info.progress,
        'created_at': task_info.created_at.isoformat(),
        'started_at': task_info.started_at.isoformat() if task_info.started_at else None,
        'completed_at': task_info.completed_at.isoformat() if task_info.completed_at else None
    }
    
    if task_info.status == TaskStatus.SUCCESS and task_info.result:
        response_data['result'] = task_info.result
    elif task_info.status == TaskStatus.FAILURE and task_info.error:
        response_data['error'] = task_info.error
    
    return jsonify(response_data)


@bp.route('/tasks/<task_id>/result', methods=['GET'])
@require_user
def get_task_result(task_id: str):
    """Get the result file from a completed task"""
    task_info = task_manager.get_task_status(task_id)
    
    if not task_info:
        return jsonify({
            'error': 'Task not found',
            'code': 'TASK_NOT_FOUND'
        }), 404
    
    if task_info.status != TaskStatus.SUCCESS:
        return jsonify({
            'error': f'Task not completed successfully. Status: {task_info.status.value}',
            'code': 'TASK_NOT_COMPLETED'
        }), 400
    
    if not task_info.result or 'file_path' not in task_info.result:
        return jsonify({
            'error': 'No result file available',
            'code': 'NO_RESULT_FILE'
        }), 404
    
    file_path = task_info.result['file_path']
    if not os.path.exists(file_path):
        return jsonify({
            'error': 'Result file no longer available',
            'code': 'FILE_EXPIRED'
        }), 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name='cards.pdf',
        mimetype='application/pdf'
    )


@bp.route('/tasks/<task_id>', methods=['DELETE'])
@require_user
def cancel_task(task_id: str):
    """Cancel a running task"""
    success = task_manager.cancel_task(task_id)
    
    if not success:
        return jsonify({
            'error': 'Task not found or cannot be cancelled',
            'code': 'TASK_CANCEL_FAILED'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'Task cancelled successfully'
    })


@bp.route('/cache/clear', methods=['POST'])
@require_admin
def clear_cache():
    """Clear the PDF cache (admin only)"""
    pdf_service.cleanup_cache()
    
    return jsonify({
        'success': True,
        'message': 'Cache cleared successfully'
    })


@bp.route('/cache/stats', methods=['GET'])
@require_admin
def get_cache_stats():
    """Get cache statistics (admin only)"""
    if hasattr(pdf_service.cache, 'get_stats'):
        # Redis cache
        cache_stats = pdf_service.cache.get_stats()
    else:
        # In-memory cache
        cache_stats = {
            'available': True,
            'cache_size_mb': pdf_service.cache.current_size / (1024 * 1024),
            'max_size_mb': pdf_service.cache.max_size_bytes / (1024 * 1024),
            'entry_count': len(pdf_service.cache.cache),
            'hit_rate': 'N/A'  # Would need to track hits/misses
        }
    
    return jsonify(cache_stats)


@bp.route('/offset', methods=['POST'])
@require_user
@track_performance
@memory_aware
@limiter.limit("20 per minute")
def api_offset_pdf_optimized():
    """Optimized API endpoint for PDF offset correction"""
    request_id = str(uuid.uuid4())
    
    try:
        # Validate request
        if 'pdf_file' not in request.files:
            return jsonify({
                'error': 'No PDF file provided',
                'code': 'NO_PDF_FILE',
                'request_id': request_id
            }), 400
        
        pdf_file = request.files['pdf_file']
        if not pdf_file.filename:
            return jsonify({
                'error': 'No PDF file selected',
                'code': 'NO_PDF_FILE',
                'request_id': request_id
            }), 400
        
        # Get form data with validation
        try:
            x_offset = int(request.form.get('x_offset', 0))
            y_offset = int(request.form.get('y_offset', 0))
            ppi = int(request.form.get('ppi', 300))
            stream_output = request.form.get('stream_output', 'false').lower() == 'true'
            
            # Validate ranges
            if not (-1000 <= x_offset <= 1000):
                raise ValueError("X offset must be between -1000 and 1000")
            if not (-1000 <= y_offset <= 1000):
                raise ValueError("Y offset must be between -1000 and 1000")
            if not (72 <= ppi <= 600):
                raise ValueError("PPI must be between 72 and 600")
                
        except (ValueError, TypeError) as e:
            return jsonify({
                'error': f'Invalid offset parameter: {str(e)}',
                'code': 'INVALID_OFFSET',
                'request_id': request_id
            }), 400
        
        # Create temp directory
        import tempfile
        temp_dir = tempfile.mkdtemp()
        input_pdf_path = os.path.join(temp_dir, 'input.pdf')
        output_pdf_path = os.path.join(temp_dir, 'output_offset.pdf')
        
        try:
            # Save uploaded PDF
            pdf_file.save(input_pdf_path)
            
            # Process PDF with offset using optimized method
            import pypdfium2 as pdfium
            from utilities import offset_images
            
            pdf = pdfium.PdfDocument(input_pdf_path)
            raw_images = []
            
            # Process pages with progress tracking
            total_pages = len(pdf)
            for page_number in range(total_pages):
                page = pdf.get_page(page_number)
                raw_images.append(page.render(ppi/72).to_pil())
            
            # Apply offset
            final_images = offset_images(raw_images, x_offset, y_offset, ppi)
            
            # Save offset PDF with optimization
            final_images[0].save(
                output_pdf_path, 
                save_all=True, 
                append_images=final_images[1:], 
                resolution=ppi, 
                speed=0, 
                subsampling=0, 
                quality=100
            )
            
            # Return the offset PDF
            if stream_output:
                return pdf_service.create_streaming_response(output_pdf_path, 'cards_offset.pdf')
            else:
                return send_file(
                    output_pdf_path, 
                    as_attachment=True, 
                    download_name='cards_offset.pdf',
                    mimetype='application/pdf'
                )
        
        finally:
            # Clean up temp directory after a delay to allow file serving
            import threading
            def delayed_cleanup():
                time.sleep(30)  # Wait 30 seconds before cleanup
                cleanup_temp_directory(temp_dir)
            
            cleanup_thread = threading.Thread(target=delayed_cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
    except Exception as e:
        current_app.logger.error(f'PDF offset failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Internal server error during PDF offset',
            'code': 'OFFSET_ERROR',
            'request_id': request_id
        }), 500


@bp.route('/version')
def version():
    """API endpoint to get version information"""
    return jsonify({
        'version': '2.1.0',
        'app': 'Silhouette Card Maker Flask (Optimized)',
        'api_version': current_app.config.get('API_VERSION', '2.1.0'),
        'features': [
            'PDF Generation',
            'Image Output',
            'Plugin System',
            'Offset Correction',
            'Calibration',
            'Multiple Card Sizes',
            'Multiple Paper Sizes',
            'Blueprint Architecture',
            'REST API',
            'CORS Support',
            'Async Generation',
            'Streaming Output',
            'Caching',
            'Parallel Processing',
            'Memory Optimization',
            'Progress Tracking',
            'Rate Limiting'
        ]
    })


@bp.route('/metrics', methods=['GET'])
@require_admin
def get_metrics():
    """Get enhanced performance metrics (admin endpoint)"""
    metrics = performance_monitor.get_metrics()
    current_memory = monitor_memory_usage()
    
    # Add cache metrics
    if hasattr(pdf_service.cache, 'get_stats'):
        cache_stats = pdf_service.cache.get_stats()
    else:
        cache_stats = {
            'cache_size_mb': pdf_service.cache.current_size / (1024 * 1024),
            'max_size_mb': pdf_service.cache.max_size_bytes / (1024 * 1024),
            'entry_count': len(pdf_service.cache.cache)
        }
    
    return jsonify({
        'performance_metrics': metrics,
        'current_memory_usage': current_memory,
        'cache_metrics': cache_stats,
        'timestamp': datetime.utcnow().isoformat()
    })
