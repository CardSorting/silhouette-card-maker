import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from flask import Flask, request, render_template, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from utilities import CardSize, PaperSize, generate_pdf

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_temp_directories():
    """Create temporary directories for processing"""
    temp_dir = tempfile.mkdtemp()
    front_dir = os.path.join(temp_dir, 'front')
    back_dir = os.path.join(temp_dir, 'back')
    double_sided_dir = os.path.join(temp_dir, 'double_sided')
    output_dir = os.path.join(temp_dir, 'output')
    
    os.makedirs(front_dir)
    os.makedirs(back_dir)
    os.makedirs(double_sided_dir)
    os.makedirs(output_dir)
    
    return temp_dir, front_dir, back_dir, double_sided_dir, output_dir

def save_uploaded_files(files, directory):
    """Save uploaded files to a directory"""
    saved_files = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(directory, filename)
            file.save(file_path)
            saved_files.append(filename)
    return saved_files

@app.route('/')
def index():
    return render_template('index.html', 
                         card_sizes=[size.value for size in CardSize],
                         paper_sizes=[size.value for size in PaperSize])

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir = create_temp_directories()
        
        # Get form data
        card_size = request.form.get('card_size', CardSize.STANDARD.value)
        paper_size = request.form.get('paper_size', PaperSize.LETTER.value)
        only_fronts = request.form.get('only_fronts') == 'on'
        crop = request.form.get('crop', '').strip() or None
        extend_corners = int(request.form.get('extend_corners', 0))
        ppi = int(request.form.get('ppi', 300))
        quality = int(request.form.get('quality', 75))
        skip_indices_str = request.form.get('skip_indices', '').strip()
        skip_indices = []
        if skip_indices_str:
            skip_indices = [int(x.strip()) for x in skip_indices_str.split(',') if x.strip().isdigit()]
        name = request.form.get('name', '').strip() or None
        
        # Handle file uploads
        front_files = request.files.getlist('front_files')
        back_files = request.files.getlist('back_files')
        double_sided_files = request.files.getlist('double_sided_files')
        
        # Save uploaded files
        front_saved = save_uploaded_files(front_files, front_dir)
        back_saved = save_uploaded_files(back_files, back_dir)
        double_sided_saved = save_uploaded_files(double_sided_files, double_sided_dir)
        
        if not front_saved:
            flash('No front images provided. Please upload at least one front image.')
            return redirect(url_for('index'))
        
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
        flash(f'Error generating PDF: {str(e)}')
        return redirect(url_for('index'))
    
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API endpoint for programmatic PDF generation"""
    try:
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir = create_temp_directories()
        
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
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum file size is 16MB.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)