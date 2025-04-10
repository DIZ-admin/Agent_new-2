"""
Photos Views Module

This module provides the photos views for the web interface.
"""

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager
from src.utils.registry import get_registry

# Get logger
logger = get_logger('web.photos')

# Create blueprint
bp = Blueprint('photos', __name__, url_prefix='/photos')

def allowed_file(filename):
    """Check if a file has an allowed extension."""
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    """Render the photos page."""
    # Get path manager
    path_manager = get_path_manager()
    
    # Get photos from different directories
    downloads = []
    for filename in os.listdir(path_manager.downloads_dir):
        if allowed_file(filename):
            file_path = os.path.join(path_manager.downloads_dir, filename)
            downloads.append({
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    
    analyzed = []
    for filename in os.listdir(path_manager.analysis_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(path_manager.analysis_dir, filename)
            photo_name = filename.replace('_analysis.json', '')
            
            # Try to find the original photo
            original_path = os.path.join(path_manager.downloads_dir, photo_name)
            if not os.path.exists(original_path):
                # Try with common extensions
                for ext in ['.jpg', '.jpeg', '.png']:
                    if os.path.exists(original_path + ext):
                        original_path = original_path + ext
                        break
            
            analyzed.append({
                'name': photo_name,
                'analysis_path': file_path,
                'original_path': original_path if os.path.exists(original_path) else None,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    
    upload_ready = []
    for filename in os.listdir(path_manager.upload_dir):
        if allowed_file(filename):
            file_path = os.path.join(path_manager.upload_dir, filename)
            
            # Check if metadata exists
            metadata_path = os.path.join(path_manager.upload_metadata_dir, os.path.splitext(filename)[0] + '.json')
            metadata = None
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata for {filename}: {str(e)}")
            
            upload_ready.append({
                'name': filename,
                'path': file_path,
                'metadata_path': metadata_path if os.path.exists(metadata_path) else None,
                'metadata': metadata,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    
    uploaded = []
    for filename in os.listdir(path_manager.uploaded_dir):
        if allowed_file(filename):
            file_path = os.path.join(path_manager.uploaded_dir, filename)
            
            # Check if metadata exists
            metadata_path = os.path.join(path_manager.uploaded_dir, os.path.splitext(filename)[0] + '.json')
            metadata = None
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata for {filename}: {str(e)}")
            
            uploaded.append({
                'name': filename,
                'path': file_path,
                'metadata_path': metadata_path if os.path.exists(metadata_path) else None,
                'metadata': metadata,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    
    return render_template('photos/index.html', 
                          downloads=sorted(downloads, key=lambda x: x['modified'], reverse=True),
                          analyzed=sorted(analyzed, key=lambda x: x['modified'], reverse=True),
                          upload_ready=sorted(upload_ready, key=lambda x: x['modified'], reverse=True),
                          uploaded=sorted(uploaded, key=lambda x: x['modified'], reverse=True))

@bp.route('/upload', methods=['POST'])
def upload():
    """Upload photos."""
    if 'photos' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('photos.index'))
    
    files = request.files.getlist('photos')
    
    if not files or files[0].filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('photos.index'))
    
    path_manager = get_path_manager()
    uploaded_count = 0
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(path_manager.downloads_dir, filename)
            
            # Save the file
            file.save(file_path)
            uploaded_count += 1
            logger.info(f"Uploaded file: {filename}")
    
    if uploaded_count > 0:
        flash(f'Successfully uploaded {uploaded_count} photos', 'success')
    else:
        flash('No valid photos uploaded', 'warning')
    
    return redirect(url_for('photos.index'))

@bp.route('/view/<path:filename>')
def view_photo(filename):
    """View a photo."""
    path_manager = get_path_manager()
    
    # Determine which directory the file is in
    if os.path.exists(os.path.join(path_manager.downloads_dir, filename)):
        return send_from_directory(path_manager.downloads_dir, filename)
    elif os.path.exists(os.path.join(path_manager.upload_dir, filename)):
        return send_from_directory(path_manager.upload_dir, filename)
    elif os.path.exists(os.path.join(path_manager.uploaded_dir, filename)):
        return send_from_directory(path_manager.uploaded_dir, filename)
    else:
        flash(f"File not found: {filename}", "danger")
        return redirect(url_for('photos.index'))

@bp.route('/analysis/<path:filename>')
def view_analysis(filename):
    """View analysis for a photo."""
    path_manager = get_path_manager()
    
    # Try to find the analysis file
    analysis_path = os.path.join(path_manager.analysis_dir, filename)
    if not analysis_path.endswith('.json'):
        analysis_path += '_analysis.json'
    
    if os.path.exists(analysis_path):
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            # Find the original photo
            photo_name = filename.replace('_analysis.json', '')
            original_path = None
            
            # Try in downloads directory
            for ext in ['', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                if os.path.exists(os.path.join(path_manager.downloads_dir, photo_name + ext)):
                    original_path = url_for('photos.view_photo', filename=photo_name + ext)
                    break
            
            return render_template('photos/analysis.html', 
                                  filename=filename,
                                  analysis=analysis,
                                  original_path=original_path)
        except Exception as e:
            flash(f"Error loading analysis: {str(e)}", "danger")
            logger.error(f"Error loading analysis for {filename}: {str(e)}")
            return redirect(url_for('photos.index'))
    else:
        flash(f"Analysis not found for: {filename}", "danger")
        return redirect(url_for('photos.index'))
