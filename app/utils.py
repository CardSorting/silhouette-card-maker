import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


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
    """Save uploaded files to a directory with enhanced validation"""
    from utilities import delete_hidden_files_in_directory
    from flask import current_app
    
    saved_files = []
    total_size = 0
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 64 * 1024 * 1024)
    
    for file in files:
        if not file or not file.filename:
            continue
            
        # Check file extension
        if not allowed_file(file.filename):
            current_app.logger.warning(f'File {file.filename} has invalid extension')
            continue
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            current_app.logger.warning(f'File {file.filename} exceeds size limit')
            continue
            
        total_size += file_size
        if total_size > max_size:
            current_app.logger.warning(f'Total upload size would exceed limit')
            break
        
        # Save file
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(directory, filename)
            file.save(file_path)
            saved_files.append(filename)
            current_app.logger.info(f'Saved file: {filename} ({file_size} bytes)')
        except Exception as e:
            current_app.logger.error(f'Failed to save file {file.filename}: {str(e)}')
            continue
    
    # Clean up hidden files like CLI does
    delete_hidden_files_in_directory(directory)
    return saved_files


def handle_multiple_back_images(back_dir, selected_back_index=None):
    """Handle multiple back images similar to CLI behavior"""
    files = [f for f in os.listdir(back_dir) 
             if (os.path.isfile(os.path.join(back_dir, f)) and not f.endswith(".md"))]
    
    if len(files) == 0:
        return None
    
    if len(files) == 1:
        return os.path.join(back_dir, files[0])
    
    # Multiple back files - return list for web interface to handle
    if selected_back_index is not None and 0 <= selected_back_index < len(files):
        return os.path.join(back_dir, files[selected_back_index])
    
    return files  # Return list of filenames for web interface


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


def cleanup_temp_directory(temp_dir):
    """Clean up temporary directory"""
    try:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception:
        pass