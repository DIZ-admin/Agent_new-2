"""
Settings Views Module

This module provides the settings views for the web interface.
"""

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager

# Get logger
logger = get_logger('web.settings')

# Create blueprint
bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/')
def index():
    """Render the settings page."""
    config = get_config()
    path_manager = get_path_manager()
    
    # Load SharePoint schema
    schema_path = path_manager.get_schema_path()
    schema = None
    if os.path.exists(schema_path):
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        except Exception as e:
            logger.error(f"Error loading schema: {str(e)}")
    
    # Get environment variables
    env_vars = {
        'SHAREPOINT_SITE_URL': os.environ.get('SHAREPOINT_SITE_URL', ''),
        'SHAREPOINT_USERNAME': os.environ.get('SHAREPOINT_USERNAME', ''),
        'SHAREPOINT_PASSWORD': '********' if os.environ.get('SHAREPOINT_PASSWORD') else '',
        'SOURCE_LIBRARY_TITLE': os.environ.get('SOURCE_LIBRARY_TITLE', ''),
        'SHAREPOINT_LIBRARY': os.environ.get('SHAREPOINT_LIBRARY', ''),
        'OPENAI_API_KEY': '********' if os.environ.get('OPENAI_API_KEY') else '',
        'OPENAI_CONCURRENCY_LIMIT': os.environ.get('OPENAI_CONCURRENCY_LIMIT', ''),
        'MAX_TOKENS': os.environ.get('MAX_TOKENS', ''),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL', ''),
        'LOG_FILE': os.environ.get('LOG_FILE', '')
    }
    
    return render_template('settings/index.html', 
                          config=config,
                          schema=schema,
                          env_vars=env_vars)

@bp.route('/update_env', methods=['POST'])
def update_env():
    """Update environment variables."""
    # This is a simplified version - in a real application, you would want to validate
    # and sanitize the input, and possibly use a more secure method to store credentials
    
    # Get form data
    env_vars = {
        'SHAREPOINT_SITE_URL': request.form.get('SHAREPOINT_SITE_URL', ''),
        'SHAREPOINT_USERNAME': request.form.get('SHAREPOINT_USERNAME', ''),
        'SOURCE_LIBRARY_TITLE': request.form.get('SOURCE_LIBRARY_TITLE', ''),
        'SHAREPOINT_LIBRARY': request.form.get('SHAREPOINT_LIBRARY', ''),
        'OPENAI_CONCURRENCY_LIMIT': request.form.get('OPENAI_CONCURRENCY_LIMIT', ''),
        'MAX_TOKENS': request.form.get('MAX_TOKENS', ''),
        'LOG_LEVEL': request.form.get('LOG_LEVEL', ''),
        'LOG_FILE': request.form.get('LOG_FILE', '')
    }
    
    # Update password and API key only if provided
    if request.form.get('SHAREPOINT_PASSWORD'):
        env_vars['SHAREPOINT_PASSWORD'] = request.form.get('SHAREPOINT_PASSWORD')
    
    if request.form.get('OPENAI_API_KEY'):
        env_vars['OPENAI_API_KEY'] = request.form.get('OPENAI_API_KEY')
    
    # Update environment variables in config.env
    try:
        config_dir = get_config().config_dir
        env_path = os.path.join(config_dir, 'config.env')
        
        # Read existing file
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Update values
        new_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                new_lines.append(line)
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            
            if key in env_vars and env_vars[key]:
                new_lines.append(f"{key}={env_vars[key]}")
            else:
                new_lines.append(line)
        
        # Write back to file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        flash("Settings updated successfully. Restart the application for changes to take effect.", "success")
        logger.info("Environment variables updated via web interface")
    except Exception as e:
        flash(f"Error updating settings: {str(e)}", "danger")
        logger.error(f"Error updating environment variables: {str(e)}")
    
    return redirect(url_for('settings.index'))

@bp.route('/clean_directory/<directory>')
def clean_directory(directory):
    """Clean a directory."""
    path_manager = get_path_manager()
    
    valid_directories = {
        'downloads': path_manager.downloads_dir,
        'metadata': path_manager.metadata_dir,
        'analysis': path_manager.analysis_dir,
        'upload': path_manager.upload_dir,
        'upload_metadata': path_manager.upload_metadata_dir
    }
    
    if directory not in valid_directories:
        flash(f"Invalid directory: {directory}", "danger")
        return redirect(url_for('settings.index'))
    
    try:
        dir_path = valid_directories[directory]
        count = 0
        
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                count += 1
        
        flash(f"Successfully cleaned {count} files from {directory} directory", "success")
        logger.info(f"Cleaned {count} files from {directory} directory via web interface")
    except Exception as e:
        flash(f"Error cleaning {directory} directory: {str(e)}", "danger")
        logger.error(f"Error cleaning {directory} directory: {str(e)}")
    
    return redirect(url_for('settings.index'))
