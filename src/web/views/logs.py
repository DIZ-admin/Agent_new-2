"""
Logs Views Module

This module provides the logs views for the web interface.
"""

import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger, rotate_logs
from src.utils.paths import get_path_manager

# Get logger
logger = get_logger('web.logs')

# Create blueprint
bp = Blueprint('logs', __name__, url_prefix='/logs')

@bp.route('/')
def index():
    """Render the logs page."""
    config = get_config()
    logs_dir = config.logs_dir
    
    # Get all log files
    log_files = []
    for filename in os.listdir(logs_dir):
        if filename.endswith('.log'):
            file_path = os.path.join(logs_dir, filename)
            
            # Extract date from filename
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
            log_date = None
            if date_match:
                try:
                    log_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                except ValueError:
                    pass
            
            log_files.append({
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'date': log_date
            })
    
    # Sort by date (newest first)
    log_files.sort(key=lambda x: x['modified'], reverse=True)
    
    # Get selected log file
    selected_log = request.args.get('file')
    if selected_log and selected_log in [log['name'] for log in log_files]:
        selected_path = os.path.join(logs_dir, selected_log)
        
        # Read log file content
        try:
            with open(selected_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse log entries
            log_entries = []
            for line in content.split('\n'):
                if not line.strip():
                    continue
                
                # Try to parse log entry
                try:
                    # Format: 2023-04-10 14:25:33,123 - module - LEVEL - Message
                    parts = line.split(' - ', 3)
                    if len(parts) >= 4:
                        timestamp_str, module, level, message = parts
                        try:
                            timestamp = datetime.strptime(timestamp_str.strip(), '%Y-%m-%d %H:%M:%S,%f')
                        except ValueError:
                            timestamp = None
                        
                        log_entries.append({
                            'timestamp': timestamp,
                            'module': module.strip(),
                            'level': level.strip(),
                            'message': message.strip()
                        })
                    else:
                        # If can't parse, add as raw message
                        log_entries.append({
                            'timestamp': None,
                            'module': None,
                            'level': None,
                            'message': line
                        })
                except Exception:
                    # If any error, add as raw message
                    log_entries.append({
                        'timestamp': None,
                        'module': None,
                        'level': None,
                        'message': line
                    })
        except Exception as e:
            flash(f"Error reading log file: {str(e)}", "danger")
            logger.error(f"Error reading log file {selected_log}: {str(e)}")
            log_entries = []
    else:
        selected_log = None
        log_entries = []
    
    return render_template('logs/index.html', 
                          log_files=log_files,
                          selected_log=selected_log,
                          log_entries=log_entries)

@bp.route('/download/<path:filename>')
def download_log(filename):
    """Download a log file."""
    config = get_config()
    logs_dir = config.logs_dir
    
    file_path = os.path.join(logs_dir, filename)
    if os.path.exists(file_path) and filename.endswith('.log'):
        return send_file(file_path, as_attachment=True)
    else:
        flash(f"Log file not found: {filename}", "danger")
        return redirect(url_for('logs.index'))

@bp.route('/rotate', methods=['POST'])
def rotate():
    """Rotate log files."""
    try:
        max_days = int(request.form.get('max_days', 30))
        rotate_logs(max_days=max_days)
        flash(f"Successfully rotated logs (removed logs older than {max_days} days)", "success")
        logger.info(f"Rotated logs (max_days={max_days}) via web interface")
    except Exception as e:
        flash(f"Error rotating logs: {str(e)}", "danger")
        logger.error(f"Error rotating logs: {str(e)}")
    
    return redirect(url_for('logs.index'))
