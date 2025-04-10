"""
Flask Application Module

This module provides the Flask application for the web interface.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger, rotate_logs
from src.utils.paths import get_path_manager

# Get logger
logger = get_logger('web_interface')

def create_app(test_config=None):
    """
    Create and configure the Flask application.

    Args:
        test_config (dict, optional): Test configuration. Defaults to None.

    Returns:
        Flask: Configured Flask application
    """
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        UPLOAD_FOLDER=get_path_manager().downloads_dir,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB max upload size
    )

    # No Bootstrap initialization needed

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register blueprints
    from .views import main, photos, settings, logs
    app.register_blueprint(main.bp)
    app.register_blueprint(photos.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(logs.bp)

    # Add template filters
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        """Format a datetime object."""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(format)

    @app.template_filter('filesize')
    def format_filesize(value):
        """Format a filesize in bytes to a human-readable format."""
        if value is None:
            return "0 B"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0

        return f"{value:.1f} PB"

    # Add context processors
    @app.context_processor
    def inject_config():
        """Inject configuration into templates."""
        return {'config': get_config()}

    @app.context_processor
    def inject_now():
        """Inject current datetime into templates."""
        return {'now': datetime.now()}

    # Add error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(e)}")
        return render_template('errors/500.html'), 500

    # Log application startup
    logger.info("Web interface started")

    return app
