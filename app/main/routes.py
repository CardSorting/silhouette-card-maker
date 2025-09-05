import os
import zipfile
from io import BytesIO

from flask import render_template, request, send_file, flash, redirect, url_for, Response, current_app
from werkzeug.utils import secure_filename

from app.main import bp
from app.utils import (
    create_temp_directories, save_uploaded_files, handle_multiple_back_images,
    run_plugin, cleanup_temp_directory
)
from utilities import (
    CardSize, PaperSize, generate_pdf, load_saved_offset
)


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


@bp.route('/')
def index():
    """Main page with unified card generation interface"""
    # Load saved offset for display
    saved_offset = load_saved_offset()
    return render_template('index_clean.html', 
                         card_sizes=[size.value for size in CardSize],
                         paper_sizes=[size.value for size in PaperSize],
                         plugin_games=current_app.config['PLUGIN_GAMES'],
                         saved_offset=saved_offset)


@bp.route('/grid')
def grid_upload():
    """Grid-based upload interface"""
    # Load saved offset for display
    saved_offset = load_saved_offset()
    return render_template('grid_upload.html', 
                         card_sizes=[size.value for size in CardSize],
                         paper_sizes=[size.value for size in PaperSize],
                         plugin_games=current_app.config['PLUGIN_GAMES'],
                         saved_offset=saved_offset)


@bp.route('/select_back', methods=['POST'])
def select_back():
    """Handle multiple back image selection - redirect to main page"""
    flash("Please re-upload your files and select the back image.")
    return redirect(url_for('main.index'))


@bp.route('/generate', methods=['POST'])
def generate():
    """Generate PDF or images based on form data"""
    temp_dir = None
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
                return redirect(url_for('main.index'))
            
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
                return redirect(url_for('main.index'))
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
                return redirect(url_for('main.index'))
            
            # Handle multiple back images like CLI
            if back_saved:
                back_result = handle_multiple_back_images(back_dir, selected_back_index)
                if isinstance(back_result, list):
                    # Multiple back images found, need user selection
                    flash(f"Multiple back images found: {', '.join(back_result)}. Please re-upload and select one back image.")
                    return redirect(url_for('main.index'))
        
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
        return redirect(url_for('main.index'))
    
    finally:
        cleanup_temp_directory(temp_dir)


@bp.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up game directories like clean_up.py"""
    try:
        from clean_up import delete_files
        delete_files()
        flash('Game directories cleaned up successfully')
    except Exception as e:
        flash(f'Error cleaning up: {str(e)}')
    
    return redirect(url_for('main.index'))