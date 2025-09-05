import os
import uuid
from datetime import datetime
from flask import request, send_file, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from app.api import bp
from app.utils import create_temp_directories, save_uploaded_files, cleanup_temp_directory
from app.performance import memory_aware, track_performance, performance_monitor, monitor_memory_usage
from app.auth import require_user, require_admin, get_current_user
from utilities import CardSize, PaperSize, generate_pdf


@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0',
        'service': 'Silhouette Card Maker API'
    })


@bp.route('/config', methods=['GET'])
def get_config():
    """Get available configuration options"""
    return jsonify({
        'card_sizes': [size.value for size in CardSize],
        'paper_sizes': [size.value for size in PaperSize],
        'max_file_size': current_app.config['MAX_CONTENT_LENGTH'],
        'allowed_extensions': list(current_app.config['ALLOWED_EXTENSIONS']),
        'plugin_games': current_app.config.get('PLUGIN_GAMES', {})
    })


@bp.route('/generate', methods=['POST'])
@require_user
@track_performance
@memory_aware
def api_generate():
    """API endpoint for programmatic PDF generation"""
    temp_dir = None
    request_id = str(uuid.uuid4())
    
    try:
        # Validate request content type
        if not request.files:
            return jsonify({
                'error': 'No files provided',
                'code': 'NO_FILES',
                'request_id': request_id
            }), 400
        
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir, _ = create_temp_directories()
        
        # Get form data with validation
        try:
            card_size = request.form.get('card_size', CardSize.STANDARD.value)
            paper_size = request.form.get('paper_size', PaperSize.LETTER.value)
            only_fronts = request.form.get('only_fronts', 'false').lower() == 'true'
            crop = request.form.get('crop', '').strip() or None
            extend_corners = int(request.form.get('extend_corners', 0))
            ppi = int(request.form.get('ppi', 300))
            quality = int(request.form.get('quality', 75))
            skip_indices_str = request.form.get('skip_indices', '').strip()
            name = request.form.get('name', '').strip() or None
            output_images = request.form.get('output_images', 'false').lower() == 'true'
            load_offset = request.form.get('load_offset', 'false').lower() == 'true'
            
            # Parse skip indices
            skip_indices = []
            if skip_indices_str:
                skip_indices = [int(x.strip()) for x in skip_indices_str.split(',') if x.strip().isdigit()]
                
        except (ValueError, TypeError) as e:
            return jsonify({
                'error': f'Invalid parameter: {str(e)}',
                'code': 'INVALID_PARAMETER',
                'request_id': request_id
            }), 400
        
        # Validate card and paper sizes
        try:
            card_size_enum = CardSize(card_size)
            paper_size_enum = PaperSize(paper_size)
        except ValueError as e:
            return jsonify({
                'error': f'Invalid size: {str(e)}',
                'code': 'INVALID_SIZE',
                'request_id': request_id
            }), 400
        
        # Handle file uploads
        front_files = request.files.getlist('front_files')
        back_files = request.files.getlist('back_files')
        double_sided_files = request.files.getlist('double_sided_files')
        
        # Save uploaded files
        front_saved = save_uploaded_files(front_files, front_dir)
        back_saved = save_uploaded_files(back_files, back_dir)
        double_sided_saved = save_uploaded_files(double_sided_files, double_sided_dir)
        
        if not front_saved:
            return jsonify({
                'error': 'No valid front images provided',
                'code': 'NO_FRONT_IMAGES',
                'request_id': request_id
            }), 400
        
        # Generate output path
        if output_images:
            output_path = output_dir
        else:
            output_path = os.path.join(output_dir, 'cards.pdf')
        
        # Generate PDF/Images
        generate_pdf(
            front_dir_path=front_dir,
            back_dir_path=back_dir,
            double_sided_dir_path=double_sided_dir,
            output_path=output_path,
            output_images=output_images,
            card_size=card_size_enum,
            paper_size=paper_size_enum,
            only_fronts=only_fronts,
            crop_string=crop,
            extend_corners=extend_corners,
            ppi=ppi,
            quality=quality,
            skip_indices=skip_indices,
            load_offset=load_offset,
            name=name
        )
        
        # Return the generated file(s)
        if output_images:
            # For images, we'll return a JSON response with download info
            # In a real implementation, you might want to zip the images
            return jsonify({
                'success': True,
                'message': 'Images generated successfully',
                'request_id': request_id,
                'output_type': 'images',
                'output_path': output_path
            })
        else:
            # Return the generated PDF
            return send_file(output_path, 
                            as_attachment=True, 
                            download_name=f'{name or "cards"}.pdf',
                            mimetype='application/pdf')
    
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
    
    finally:
        cleanup_temp_directory(temp_dir)


@bp.route('/version')
def version():
    """API endpoint to get version information"""
    return jsonify({
        'version': '2.0.0',
        'app': 'Silhouette Card Maker Flask (Refactored)',
        'api_version': current_app.config.get('API_VERSION', '2.0.0'),
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
            'CORS Support'
        ]
    })


@bp.route('/metrics', methods=['GET'])
@require_admin
def get_metrics():
    """Get performance metrics (admin endpoint)"""
    metrics = performance_monitor.get_metrics()
    current_memory = monitor_memory_usage()
    
    return jsonify({
        'performance_metrics': metrics,
        'current_memory_usage': current_memory,
        'timestamp': datetime.utcnow().isoformat()
    })


@bp.route('/offset', methods=['POST'])
@require_user
def api_offset_pdf():
    """API endpoint for PDF offset correction"""
    temp_dir = None
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
        
        # Get form data
        try:
            x_offset = int(request.form.get('x_offset', 0))
            y_offset = int(request.form.get('y_offset', 0))
            ppi = int(request.form.get('ppi', 300))
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
        
        # Save uploaded PDF
        pdf_file.save(input_pdf_path)
        
        # Process PDF with offset
        import pypdfium2 as pdfium
        from utilities import offset_images
        
        pdf = pdfium.PdfDocument(input_pdf_path)
        raw_images = []
        for page_number in range(len(pdf)):
            page = pdf.get_page(page_number)
            raw_images.append(page.render(ppi/72).to_pil())
        
        # Apply offset
        final_images = offset_images(raw_images, x_offset, y_offset, ppi)
        
        # Save offset PDF
        final_images[0].save(output_pdf_path, save_all=True, append_images=final_images[1:], 
                           resolution=ppi, speed=0, subsampling=0, quality=100)
        
        # Return the offset PDF
        return send_file(output_pdf_path, 
                        as_attachment=True, 
                        download_name='cards_offset.pdf',
                        mimetype='application/pdf')
    
    except Exception as e:
        current_app.logger.error(f'PDF offset failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Internal server error during PDF offset',
            'code': 'OFFSET_ERROR',
            'request_id': request_id
        }), 500
    
    finally:
        cleanup_temp_directory(temp_dir)


@bp.route('/plugins', methods=['GET'])
def get_plugins():
    """Get available plugins and their formats"""
    return jsonify({
        'plugins': current_app.config.get('PLUGIN_GAMES', {}),
        'total_plugins': len(current_app.config.get('PLUGIN_GAMES', {}))
    })


@bp.route('/plugins/<game>/<format>', methods=['POST'])
@require_user
def run_plugin_api(game, format):
    """API endpoint to run a plugin for fetching card images"""
    temp_dir = None
    request_id = str(uuid.uuid4())
    
    try:
        # Validate plugin exists
        plugin_games = current_app.config.get('PLUGIN_GAMES', {})
        if game not in plugin_games:
            return jsonify({
                'error': f'Plugin "{game}" not found',
                'code': 'PLUGIN_NOT_FOUND',
                'request_id': request_id
            }), 404
        
        if format not in plugin_games[game]:
            return jsonify({
                'error': f'Format "{format}" not supported for plugin "{game}"',
                'code': 'FORMAT_NOT_SUPPORTED',
                'request_id': request_id
            }), 400
        
        # Validate decklist file
        if 'decklist_file' not in request.files:
            return jsonify({
                'error': 'No decklist file provided',
                'code': 'NO_DECKLIST_FILE',
                'request_id': request_id
            }), 400
        
        decklist_file = request.files['decklist_file']
        if not decklist_file.filename:
            return jsonify({
                'error': 'No decklist file selected',
                'code': 'NO_DECKLIST_FILE',
                'request_id': request_id
            }), 400
        
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir, decklist_dir = create_temp_directories()
        
        # Save decklist file
        from werkzeug.utils import secure_filename
        decklist_filename = secure_filename(decklist_file.filename)
        decklist_path = os.path.join(decklist_dir, decklist_filename)
        decklist_file.save(decklist_path)
        
        # Get plugin options from form data
        plugin_options = {}
        for key, value in request.form.items():
            if key.startswith('plugin_'):
                option_name = key[7:]  # Remove 'plugin_' prefix
                plugin_options[option_name] = value
        
        # Run plugin
        from app.utils import run_plugin
        try:
            plugin_output = run_plugin(game, format, decklist_path, front_dir, plugin_options)
            
            # Count generated images
            import os
            image_count = len([f for f in os.listdir(front_dir) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            
            return jsonify({
                'success': True,
                'message': f'Plugin completed successfully',
                'plugin_output': plugin_output,
                'images_generated': image_count,
                'request_id': request_id
            })
            
        except Exception as e:
            return jsonify({
                'error': f'Plugin execution failed: {str(e)}',
                'code': 'PLUGIN_EXECUTION_ERROR',
                'request_id': request_id
            }), 500
    
    except Exception as e:
        current_app.logger.error(f'Plugin API failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Internal server error during plugin execution',
            'code': 'PLUGIN_ERROR',
            'request_id': request_id
        }), 500
    
    finally:
        cleanup_temp_directory(temp_dir)