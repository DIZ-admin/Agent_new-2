"""
Processes views for the web interface.
"""

import os
import json
import psutil
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.utils.process_tracker import get_process_tracker
from src.utils.logging import get_logger

# Get logger
logger = get_logger('web.processes')

# Create blueprint
bp = Blueprint('processes', __name__)

@bp.route('/')
def index():
    """Render the processes page."""
    # Get process tracker
    process_tracker = get_process_tracker()

    # Get all processes
    processes = process_tracker.get_all_processes()

    # Format processes for display
    formatted_processes = {}
    for pid, process_info in processes.items():
        formatted_processes[pid] = process_tracker.format_process_info(process_info)

    return render_template('processes/index.html',
                          processes=formatted_processes)

@bp.route('/<pid>')
def view_process(pid):
    """Render the process details page."""
    # Get process tracker
    process_tracker = get_process_tracker()

    # Get process
    process_info = process_tracker.get_process(pid)

    if not process_info:
        flash('Process not found.', 'danger')
        return redirect(url_for('processes.index'))

    # Format process for display
    formatted_process = process_tracker.format_process_info(process_info)

    return render_template('processes/view.html',
                          process=formatted_process)

@bp.route('/status/<pid>')
def process_status(pid):
    """Get the status of a process."""
    # Get process tracker
    process_tracker = get_process_tracker()

    # Get process
    process_info = process_tracker.get_process(pid)

    if not process_info:
        return jsonify({'status': 'not_found'})

    # Format process for display
    formatted_process = process_tracker.format_process_info(process_info)

    return jsonify(formatted_process)

@bp.route('/active')
def active():
    """Get active processes."""
    # Get process tracker
    process_tracker = get_process_tracker()

    # Get active processes
    active_processes = process_tracker.get_active_processes()

    # Format processes for display
    formatted_processes = {}
    for pid, process_info in active_processes.items():
        formatted_processes[pid] = process_tracker.format_process_info(process_info)

    return jsonify(formatted_processes)

@bp.route('/kill/<pid>', methods=['POST'])
def kill_process(pid):
    """Kill a process."""
    try:
        # Get process
        process = psutil.Process(int(pid))

        # Kill process
        process.kill()

        # Get process tracker
        process_tracker = get_process_tracker()

        # Update process status
        process_tracker.update_process(int(pid), status="killed")

        flash('Process killed successfully.', 'success')
    except Exception as e:
        logger.error(f"Error killing process {pid}: {str(e)}")
        flash(f'Error killing process: {str(e)}', 'danger')

    return redirect(url_for('processes.index'))
