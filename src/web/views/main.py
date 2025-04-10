"""
Main Views Module

This module provides the main views for the web interface.
"""

import os
import subprocess
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager
from src.utils.registry import get_registry

# Get logger
logger = get_logger('web.main')

# Create blueprint
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Render the dashboard page."""
    # Get statistics
    path_manager = get_path_manager()
    registry = get_registry()

    # Count files in directories
    downloads_count = len(os.listdir(path_manager.downloads_dir))
    analysis_count = len([f for f in os.listdir(path_manager.analysis_dir) if f.endswith('.json')])
    upload_count = len([f for f in os.listdir(path_manager.upload_dir) if not f == 'metadata'])
    uploaded_count = len([f for f in os.listdir(path_manager.uploaded_dir) if not f.endswith('.json') and not f.endswith('.yml')])

    # Get registry statistics
    processed_files_list = registry.get_processed_files()
    uploaded_files_list = registry.get_uploaded_files()

    # Get recent activity
    recent_activity = []

    # Add recent processed files
    for filename in processed_files_list[:5]:
        # Get processing metadata
        info = registry.get_processing_metadata(filename) or {}
        recent_activity.append({
            'type': 'processed',
            'filename': filename,
            'timestamp': info.get('timestamp', ''),
            'info': info
        })

    # Add recent uploaded files
    for filename in uploaded_files_list[:5]:
        # Get upload info
        info = registry.get_upload_info(filename) or {}
        recent_activity.append({
            'type': 'uploaded',
            'filename': filename,
            'timestamp': info.get('timestamp', ''),
            'info': info
        })

    # Sort by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
    recent_activity = recent_activity[:10]  # Keep only 10 most recent

    return render_template('main/index.html',
                          downloads_count=downloads_count,
                          analysis_count=analysis_count,
                          upload_count=upload_count,
                          uploaded_count=uploaded_count,
                          processed_count=len(processed_files_list),
                          uploaded_files_count=len(uploaded_files_list),
                          recent_activity=recent_activity)

@bp.route('/run/<script>', methods=['POST'])
def run_script(script):
    """Run a script."""
    valid_scripts = {
        'metadata_schema': 'src.metadata_schema',
        'photo_metadata': 'src.photo_metadata',
        'openai_analyzer': 'src.openai_analyzer',
        'metadata_generator': 'src.metadata_generator',
        'sharepoint_uploader': 'src.sharepoint_uploader',
        'auto_process': 'src.auto_process'
    }

    if script not in valid_scripts:
        flash(f"Invalid script: {script}", "danger")
        return redirect(url_for('main.index'))

    try:
        # Run the script in a subprocess
        module = valid_scripts[script]
        subprocess.Popen(['python', '-m', module],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

        flash(f"Started {script} process", "success")
        logger.info(f"Started {script} process via web interface")
    except Exception as e:
        flash(f"Error running {script}: {str(e)}", "danger")
        logger.error(f"Error running {script}: {str(e)}")

    return redirect(url_for('main.index'))

@bp.route('/status')
def status():
    """Get system status."""
    # Get statistics
    path_manager = get_path_manager()
    registry = get_registry()

    # Count files in directories
    downloads_count = len(os.listdir(path_manager.downloads_dir))
    analysis_count = len([f for f in os.listdir(path_manager.analysis_dir) if f.endswith('.json')])
    upload_count = len([f for f in os.listdir(path_manager.upload_dir) if not f == 'metadata'])
    uploaded_count = len([f for f in os.listdir(path_manager.uploaded_dir) if not f.endswith('.json') and not f.endswith('.yml')])

    # Get registry statistics
    processed_files_list = registry.get_processed_files()
    uploaded_files_list = registry.get_uploaded_files()

    # Check if processes are running
    processes = []
    try:
        # Check for Python processes
        output = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq python.exe'], universal_newlines=True)
        processes = [line for line in output.split('\n') if 'python.exe' in line]
    except Exception as e:
        logger.error(f"Error checking processes: {str(e)}")

    return jsonify({
        'downloads_count': downloads_count,
        'analysis_count': analysis_count,
        'upload_count': upload_count,
        'uploaded_count': uploaded_count,
        'processed_count': len(processed_files_list),
        'uploaded_files_count': len(uploaded_files_list),
        'processes': len(processes),
        'timestamp': datetime.now().isoformat()
    })
