import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Optional, List
import json
import subprocess
from io import BytesIO

from flask import Flask, request, render_template, send_file, flash, redirect, url_for, jsonify, Response
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import pypdfium2 as pdfium

from utilities import (
    CardSize, PaperSize, generate_pdf, load_saved_offset, offset_images, 
    save_offset, delete_hidden_files_in_directory, get_back_card_image_path
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'txt', 'json'}
PLUGIN_GAMES = {
    'mtg': ['simple', 'mtga', 'mtgo', 'archidekt', 'deckstats', 'moxfield', 'scryfall_json'],
    'yugioh': ['ydke', 'ydk'],
    'lorcana': ['dreamborn'],
    'riftbound': ['tts', 'pixelborn', 'piltover_archive'],
    'altered': ['ajordat'],
    'netrunner': ['text', 'bbcode', 'markdown', 'plain_text', 'jinteki'],
    'gundam': ['deckplanet', 'limitless', 'egman', 'exburst'],
    'grand_archive': ['omnideck'],
    'digimon': ['tts', 'digimoncardio', 'digimoncarddev', 'digimoncardapp', 'digimonmeta', 'untap'],
    'one_piece': ['optcgsim', 'egman'],
    'flesh_and_blood': ['fabrary']
}

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
    decklist_dir = os.path.join(temp_dir, 'decklist')
    
    os.makedirs(front_dir)
    os.makedirs(back_dir)
    os.makedirs(double_sided_dir)
    os.makedirs(output_dir)
    os.makedirs(decklist_dir)
    
    return temp_dir, front_dir, back_dir, double_sided_dir, output_dir, decklist_dir

def save_uploaded_files(files, directory):
    """Save uploaded files to a directory"""
    saved_files = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(directory, filename)
            file.save(file_path)
            saved_files.append(filename)
    
    # Clean up hidden files like CLI does
    delete_hidden_files_in_directory(directory)
    return saved_files

def handle_multiple_back_images(back_dir, selected_back_index=None):
    """Handle multiple back images similar to CLI behavior"""
    files = [f for f in os.listdir(back_dir) if (os.path.isfile(os.path.join(back_dir, f)) and not f.endswith(".md"))]
    
    if len(files) == 0:
        return None
    
    if len(files) == 1:
        return os.path.join(back_dir, files[0])
    
    # Multiple back files - return list for web interface to handle
    if selected_back_index is not None and 0 <= selected_back_index < len(files):
        return os.path.join(back_dir, files[selected_back_index])
    
    return files  # Return list of filenames for web interface

def create_images_zip(images_dir):
    """Create a ZIP file containing all images"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, images_dir)
                    zip_file.write(file_path, arc_name)
    zip_buffer.seek(0)
    return zip_buffer

def run_plugin(game, deck_format, decklist_path, front_dir, plugin_options=None):
    """Run a plugin to fetch card images"""
    plugin_script = f"plugins/{game}/fetch.py"
    if not os.path.exists(plugin_script):
        raise Exception(f"Plugin not found: {plugin_script}")
    
    # Temporarily change front directory in game structure
    original_game_front = "game/front"
    if os.path.exists(original_game_front):
        # Backup original front directory
        backup_dir = f"{original_game_front}_backup_{os.getpid()}"
        os.rename(original_game_front, backup_dir)
    
    try:
        # Create symlink to our temp front directory
        os.symlink(os.path.abspath(front_dir), original_game_front)
        
        # Build command
        cmd = ["python", plugin_script, decklist_path, deck_format]
        if plugin_options:
            for opt, value in plugin_options.items():
                if value:
                    cmd.extend([f"--{opt}", str(value)])
        
        # Run plugin
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            raise Exception(f"Plugin failed: {result.stderr}")
        
        return result.stdout
        
    finally:
        # Restore original directory structure
        if os.path.exists(original_game_front):
            os.unlink(original_game_front)
        backup_dir = f"{original_game_front}_backup_{os.getpid()}"
        if os.path.exists(backup_dir):
            os.rename(backup_dir, original_game_front)

@app.route('/')
def index():
    # Load saved offset for display
    saved_offset = load_saved_offset()
    return render_template('index_enhanced.html', 
                         card_sizes=[size.value for size in CardSize],
                         paper_sizes=[size.value for size in PaperSize],
                         plugin_games=PLUGIN_GAMES,
                         saved_offset=saved_offset)

@app.route('/select_back', methods=['POST'])
def select_back():
    """Handle multiple back image selection"""
    selected_index = int(request.form.get('selected_back_index'))
    
    # Re-process the original form data with selected back image
    form_data = dict(request.form)
    form_data['selected_back_index'] = selected_index
    
    # Recreate the request and call generate
    return generate_with_selected_back(form_data)

def generate_with_selected_back(form_data):
    """Generate PDF with a specific back image selected"""
    # This would need to store the temp files somehow
    # For simplicity, redirect back to main form
    flash("Please re-upload your files and select the back image.")
    return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir, decklist_dir = create_temp_directories()
        
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
        output_images = request.form.get('output_images') == 'on'
        load_offset = request.form.get('load_offset') == 'on'
        selected_back_index = request.form.get('selected_back_index')
        if selected_back_index:
            selected_back_index = int(selected_back_index)
        
        # Plugin support
        use_plugin = request.form.get('use_plugin') == 'on'
        plugin_game = request.form.get('plugin_game')
        plugin_format = request.form.get('plugin_format')
        
        if use_plugin and plugin_game and plugin_format:
            # Handle plugin workflow
            decklist_files = request.files.getlist('decklist_files')
            if not decklist_files or not decklist_files[0].filename:
                flash('Decklist file required for plugin mode.')
                return redirect(url_for('index'))
            
            # Save decklist file
            decklist_file = decklist_files[0]
            decklist_filename = secure_filename(decklist_file.filename)
            decklist_path = os.path.join(decklist_dir, decklist_filename)
            decklist_file.save(decklist_path)
            
            # Get plugin options
            plugin_options = {}
            if plugin_game == 'mtg':
                plugin_options['ignore_set_and_collector_number'] = request.form.get('ignore_set_and_collector_number') == 'on'
                plugin_options['prefer_older_sets'] = request.form.get('prefer_older_sets') == 'on'
                plugin_options['prefer_showcase'] = request.form.get('prefer_showcase') == 'on'
                plugin_options['prefer_extra_art'] = request.form.get('prefer_extra_art') == 'on'
                prefer_sets = request.form.getlist('prefer_set')
                if prefer_sets:
                    for pset in prefer_sets:
                        plugin_options[f'prefer_set_{pset}'] = True
            
            # Run plugin
            try:
                plugin_output = run_plugin(plugin_game, plugin_format, decklist_path, front_dir, plugin_options)
                flash(f'Plugin completed successfully: {plugin_output}')
            except Exception as e:
                flash(f'Plugin error: {str(e)}')
                return redirect(url_for('index'))
        else:
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
            
            # Handle multiple back images like CLI
            if back_saved:
                back_result = handle_multiple_back_images(back_dir, selected_back_index)
                if isinstance(back_result, list):
                    # Multiple back images found, need user selection
                    return render_template('select_back.html', 
                                         back_images=back_result,
                                         form_data=request.form.to_dict())
        
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
            card_size=CardSize(card_size),
            paper_size=PaperSize(paper_size),
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
            # Create ZIP file with all images
            zip_buffer = create_images_zip(output_dir)
            return Response(zip_buffer.getvalue(),
                          mimetype='application/zip',
                          headers={'Content-Disposition': 'attachment; filename=cards.zip'})
        else:
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
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir)
        except:
            pass

@app.route('/offset', methods=['GET', 'POST'])
def offset_pdf():
    """Handle PDF offset functionality like offset_pdf.py"""
    if request.method == 'GET':
        saved_offset = load_saved_offset()
        return render_template('offset.html', saved_offset=saved_offset)
    
    try:
        # Get form data
        pdf_file = request.files.get('pdf_file')
        x_offset = request.form.get('x_offset', type=int, default=0)
        y_offset = request.form.get('y_offset', type=int, default=0)
        save_offsets = request.form.get('save_offsets') == 'on'
        ppi = int(request.form.get('ppi', 300))
        
        if not pdf_file or not pdf_file.filename:
            flash('Please upload a PDF file.')
            return redirect(url_for('offset_pdf'))
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        input_pdf_path = os.path.join(temp_dir, 'input.pdf')
        output_pdf_path = os.path.join(temp_dir, 'output_offset.pdf')
        
        # Save uploaded PDF
        pdf_file.save(input_pdf_path)
        
        # Load saved offset if available
        new_x_offset = 0
        new_y_offset = 0
        
        saved_offset = load_saved_offset()
        if saved_offset is not None:
            new_x_offset = saved_offset.x_offset
            new_y_offset = saved_offset.y_offset
        
        # Use provided offsets
        if x_offset is not None:
            new_x_offset = x_offset
        if y_offset is not None:
            new_y_offset = y_offset
        
        # Save new offset if requested
        if save_offsets:
            save_offset(new_x_offset, new_y_offset)
            flash(f'Saved offset: x={new_x_offset}, y={new_y_offset}')
        
        # Process PDF
        pdf = pdfium.PdfDocument(input_pdf_path)
        
        # Get all the raw page images from the PDF
        raw_images = []
        for page_number in range(len(pdf)):
            page = pdf.get_page(page_number)
            raw_images.append(page.render(ppi/72).to_pil())
        
        # Offset images
        final_images = offset_images(raw_images, new_x_offset, new_y_offset, ppi)
        
        # Save offset PDF
        final_images[0].save(output_pdf_path, save_all=True, append_images=final_images[1:], 
                           resolution=ppi, speed=0, subsampling=0, quality=100)
        
        # Return the offset PDF
        return send_file(output_pdf_path, 
                        as_attachment=True, 
                        download_name='cards_offset.pdf',
                        mimetype='application/pdf')
    
    except Exception as e:
        flash(f'Error processing PDF: {str(e)}')
        return redirect(url_for('offset_pdf'))
    
    finally:
        # Clean up
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir)
        except:
            pass

@app.route('/calibration')
def calibration():
    """Generate calibration PDFs for all paper sizes"""
    try:
        # Import and run calibration script
        import calibration
        flash('Calibration PDFs generated in calibration/ directory')
    except Exception as e:
        flash(f'Error generating calibration PDFs: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up game directories like clean_up.py"""
    try:
        from clean_up import delete_files
        delete_files()
        flash('Game directories cleaned up successfully')
    except Exception as e:
        flash(f'Error cleaning up: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/api/version')
def version():
    """API endpoint to get version information"""
    return jsonify({
        'version': '1.4.0',
        'app': 'Silhouette Card Maker Flask',
        'features': [
            'PDF Generation',
            'Image Output',
            'Plugin System',
            'Offset Correction',
            'Calibration',
            'Multiple Card Sizes',
            'Multiple Paper Sizes'
        ]
    })

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum file size is 64MB.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)