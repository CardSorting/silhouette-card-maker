import os
from flask import request, send_file, jsonify
from app.api import bp
from app.utils import create_temp_directories, save_uploaded_files, cleanup_temp_directory
from utilities import CardSize, PaperSize, generate_pdf


@bp.route('/generate', methods=['POST'])
def api_generate():
    """API endpoint for programmatic PDF generation"""
    temp_dir = None
    try:
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir, _ = create_temp_directories()
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        card_size = data.get('card_size', CardSize.STANDARD.value)
        paper_size = data.get('paper_size', PaperSize.LETTER.value)
        only_fronts = data.get('only_fronts', False)
        crop = data.get('crop')
        extend_corners = data.get('extend_corners', 0)
        ppi = data.get('ppi', 300)
        quality = data.get('quality', 75)
        skip_indices = data.get('skip_indices', [])
        name = data.get('name')
        
        # Handle file uploads through multipart
        front_files = request.files.getlist('front_files')
        back_files = request.files.getlist('back_files')
        double_sided_files = request.files.getlist('double_sided_files')
        
        # Save uploaded files
        front_saved = save_uploaded_files(front_files, front_dir)
        back_saved = save_uploaded_files(back_files, back_dir)
        double_sided_saved = save_uploaded_files(double_sided_files, double_sided_dir)
        
        if not front_saved:
            return jsonify({'error': 'No front images provided'}), 400
        
        # Generate output path
        output_path = os.path.join(output_dir, 'cards.pdf')
        
        # Generate PDF
        generate_pdf(
            front_dir_path=front_dir,
            back_dir_path=back_dir,
            double_sided_dir_path=double_sided_dir,
            output_path=output_path,
            output_images=False,
            card_size=CardSize(card_size),
            paper_size=PaperSize(paper_size),
            only_fronts=only_fronts,
            crop_string=crop,
            extend_corners=extend_corners,
            ppi=ppi,
            quality=quality,
            skip_indices=skip_indices,
            load_offset=False,
            name=name
        )
        
        # Return the generated PDF
        return send_file(output_path, 
                        as_attachment=True, 
                        download_name='cards.pdf',
                        mimetype='application/pdf')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cleanup_temp_directory(temp_dir)


@bp.route('/version')
def version():
    """API endpoint to get version information"""
    return jsonify({
        'version': '2.0.0',
        'app': 'Silhouette Card Maker Flask (Refactored)',
        'features': [
            'PDF Generation',
            'Image Output',
            'Plugin System',
            'Offset Correction',
            'Calibration',
            'Multiple Card Sizes',
            'Multiple Paper Sizes',
            'Blueprint Architecture',
            'TailwindCSS UI'
        ]
    })