"""
Main Views Module

This module provides the main views for the web interface.
"""

import os
import json
import time
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_wtf.csrf import CSRFProtect
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager
from src.utils.registry import get_registry
from src.utils.process_tracker import get_process_tracker
from src.web.views.photos import allowed_file
from src.web.utils import handle_api_error, log_with_context, Timer
from src.web.process_monitor import run_process
from src.web.file_manager import FileManager
from src.web.exceptions import ProcessExecutionError

# Get logger
logger = get_logger('web.main')

# Create blueprint
bp = Blueprint('main', __name__)

# Initialize file manager
file_manager = FileManager(get_path_manager())

@bp.route('/')
def index():
    """Render the dashboard page with optimized file operations."""
    with Timer() as timer:
        # Get path manager and registry
        path_manager = get_path_manager()
        registry = get_registry()
        
        try:
            # Use optimized file operations through the file manager
            downloads_files, _ = file_manager.get_files_in_directory(
                path_manager.downloads_dir, 
                page=1, 
                per_page=1000,  # Get all files for counting
                filter_func=allowed_file
            )
            downloads_count = len(downloads_files)
            
            analysis_files, _ = file_manager.get_files_in_directory(
                path_manager.analysis_dir,
                page=1,
                per_page=1000,
                filter_func=lambda f: f.endswith('.json')
            )
            analysis_count = len(analysis_files)
            
            upload_files, _ = file_manager.get_files_in_directory(
                path_manager.upload_dir,
                page=1,
                per_page=1000,
                filter_func=lambda f: f != 'metadata' and allowed_file(f)
            )
            upload_count = len(upload_files)
            
            uploaded_files, _ = file_manager.get_files_in_directory(
                path_manager.uploaded_dir,
                page=1,
                per_page=1000,
                filter_func=lambda f: not f.endswith('.json') and not f.endswith('.yml') and allowed_file(f)
            )
            uploaded_count = len(uploaded_files)
            
            # Get processed files for recent activity (limited to 5)
            processed_files, _ = file_manager.get_files_in_directory(
                path_manager.processed_dir,
                page=1,
                per_page=5,
                filter_func=allowed_file,
                sort_by='modified',
                reverse=True
            )
            
            # Create recent activity list
            recent_activity = []
            
            # Add processed files to recent activity
            for file_info in processed_files:
                recent_activity.append({
                    'type': 'processed',
                    'filename': file_info['name'],
                    'timestamp': file_info['modified'].isoformat(),
                    'info': {
                        'path': file_info['path'],
                        'size': file_info['size']
                    }
                })
            
            # Get recently uploaded files (limited to 5)
            uploaded_recent, _ = file_manager.get_files_in_directory(
                path_manager.uploaded_dir,
                page=1,
                per_page=5,
                filter_func=allowed_file,
                sort_by='modified',
                reverse=True
            )
            
            # Add uploaded files to recent activity
            for file_info in uploaded_recent:
                # Get metadata if available using file manager
                metadata = file_manager.get_metadata_for_file(
                    file_info['name'],
                    path_manager.uploaded_dir
                )
                
                recent_activity.append({
                    'type': 'uploaded',
                    'filename': file_info['name'],
                    'timestamp': file_info['modified'].isoformat(),
                    'info': {
                        'path': file_info['path'],
                        'size': file_info['size'],
                        'metadata': metadata
                    }
                })
            
            # Sort and limit recent activity
            recent_activity.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
            recent_activity = recent_activity[:10]
            
            processed_count = len(processed_files)
            uploaded_files_count = len(uploaded_recent)
            
        except Exception as e:
            logger.error(f"Error getting file statistics: {str(e)}")
            flash(f"Error loading dashboard data: {str(e)}", "danger")
            # Set default values in case of error
            downloads_count = 0
            analysis_count = 0
            upload_count = 0
            uploaded_count = 0
            processed_count = 0
            uploaded_files_count = 0
            recent_activity = []
    
    # Log performance for slow operations
    if timer.elapsed > 1.0:
        log_with_context(
            logger.warning,
            "Dashboard page load was slow",
            {
                'time_ms': int(timer.elapsed * 1000),
                'downloads_count': downloads_count,
                'analysis_count': analysis_count
            }
        )
        
    return render_template('main/index.html',
                          downloads_count=downloads_count,
                          analysis_count=analysis_count,
                          upload_count=upload_count,
                          uploaded_count=uploaded_count,
                          processed_count=processed_count,
                          uploaded_files_count=uploaded_files_count,
                          recent_activity=recent_activity)

@bp.route('/run/<script>', methods=['POST'])
def run_script(script):
    """Run a script with improved process monitoring."""
    valid_scripts = {
        'metadata_schema': 'src.metadata_schema',
        'photo_metadata': 'src.photo_metadata',
        'openai_analyzer': 'src.openai_analyzer',
        'metadata_generator': 'src.metadata_generator',
        'sharepoint_uploader': 'src.sharepoint_uploader',
        'auto_process': 'src.auto_process'
    }

    # Validate script name
    if script not in valid_scripts:
        flash(f"Invalid script: {script}", "danger")
        return redirect(url_for('main.index'))

    # Get friendly name for the script
    script_names = {
        'metadata_schema': 'Load Metadata Schema',
        'photo_metadata': 'Download Photos',
        'openai_analyzer': 'Analyze Photos with OpenAI',
        'metadata_generator': 'Generate Metadata',
        'sharepoint_uploader': 'Upload to SharePoint',
        'auto_process': 'Full Process'
    }
    friendly_name = script_names.get(script, script)

    try:
        # Get process tracker
        process_tracker = get_process_tracker()
        
        # Get the module name
        module = valid_scripts[script]
        
        # Prepare the command
        command = ['python', '-m', module]
        
        # Run the process with the improved process monitor
        process, monitor = run_process(command, process_tracker, script)
        
        # Log the process start
        log_with_context(
            logger.info,
            f"Started {script} process via web interface",
            {
                'pid': process.pid,
                'module': module,
                'command': ' '.join(command)
            }
        )
        
        # Flash message with link to process details
        flash(f"<strong>{friendly_name}</strong> started! <a href='{url_for('processes.view_process', pid=process.pid)}' class='alert-link'>View progress</a>", "success")
        
        # Redirect to process details page
        return redirect(url_for('processes.view_process', pid=process.pid))
    except ProcessExecutionError as e:
        return handle_api_error(e, f"Error running {friendly_name}", 'main.index')
    except Exception as e:
        return handle_api_error(e, f"Unexpected error running {friendly_name}", 'main.index')

@bp.route('/status')
def status():
    """Get system status with optimized file operations."""
    try:
        with Timer() as timer:
            # Get path manager and registry
            path_manager = get_path_manager()
            registry = get_registry()
            
            # Use the file manager for more efficient file counting
            downloads_files, _ = file_manager.get_files_in_directory(
                path_manager.downloads_dir, 
                page=1, 
                per_page=1000,
                filter_func=allowed_file
            )
            
            analysis_files, _ = file_manager.get_files_in_directory(
                path_manager.analysis_dir,
                page=1,
                per_page=1000,
                filter_func=lambda f: f.endswith('.json')
            )
            
            upload_files, _ = file_manager.get_files_in_directory(
                path_manager.upload_dir,
                page=1,
                per_page=1000,
                filter_func=lambda f: f != 'metadata' and allowed_file(f)
            )
            
            uploaded_files, _ = file_manager.get_files_in_directory(
                path_manager.uploaded_dir,
                page=1,
                per_page=1000,
                filter_func=lambda f: not f.endswith('.json') and not f.endswith('.yml') and allowed_file(f)
            )
            
            # Get registry statistics in parallel
            processed_files_list = registry.get_processed_files()
            uploaded_files_list = registry.get_uploaded_files()
            
            # Get process tracker statistics
            process_tracker = get_process_tracker()
            active_processes = process_tracker.get_active_processes()
            
            # Create response data
            status_data = {
                'downloads_count': len(downloads_files),
                'analysis_count': len(analysis_files),
                'upload_count': len(upload_files),
                'uploaded_count': len(uploaded_files),
                'processed_count': len(processed_files_list),
                'uploaded_files_count': len(uploaded_files_list),
                'processes': len(active_processes),
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': int(timer.elapsed * 1000)
            }
            
            # Log slow status requests
            if timer.elapsed > 0.5:  # More than 500ms is slow
                log_with_context(
                    logger.warning,
                    "Status API request was slow",
                    {
                        'time_ms': int(timer.elapsed * 1000),
                        'downloads_count': len(downloads_files),
                        'processes': len(active_processes)
                    }
                )
                
            return jsonify(status_data)
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
