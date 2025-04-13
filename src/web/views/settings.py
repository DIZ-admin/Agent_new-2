"""
Settings Views Module

This module provides the settings views for the web interface.
"""

import os
import json
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import datetime

from src.utils.config import get_config, reload_config
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
        'TEMPERATURE': os.environ.get('TEMPERATURE', '0.5'),
        'MODEL_NAME': os.environ.get('MODEL_NAME', 'gpt-4-vision-preview'),
        'IMAGE_DETAIL': os.environ.get('IMAGE_DETAIL', 'high'),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL', ''),
        'LOG_FILE': os.environ.get('LOG_FILE', ''),
        'OPENAI_PROMPT_TYPE': os.environ.get('OPENAI_PROMPT_TYPE', 'default'),
        'OPENAI_PROMPT_ROLE': os.environ.get('OPENAI_PROMPT_ROLE', ''),
        'OPENAI_PROMPT_INSTRUCTIONS_PRE': os.environ.get('OPENAI_PROMPT_INSTRUCTIONS_PRE', ''),
        'OPENAI_PROMPT_INSTRUCTIONS_POST': os.environ.get('OPENAI_PROMPT_INSTRUCTIONS_POST', ''),
        'OPENAI_PROMPT_EXAMPLE': os.environ.get('OPENAI_PROMPT_EXAMPLE', '')
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
        'LOG_FILE': request.form.get('LOG_FILE', ''),
        'OPENAI_PROMPT_TYPE': request.form.get('OPENAI_PROMPT_TYPE', 'default')
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
                value = env_vars[key]
                if '\n' in value:
                    # For multiline values, use triple quotes and preserve newlines
                    new_lines.append(f'{key}="""{value}"""')
                else:
                    # For single line values, use regular quotes
                    new_lines.append(f'{key}="{value}"')
            else:
                new_lines.append(line)

        # Write back to file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))

        # Reload configuration
        reload_config()

        flash("Settings updated successfully. Changes have been applied.", "success")
        logger.info("Environment variables updated via web interface and configuration reloaded")
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
        'upload_metadata': path_manager.upload_metadata_dir,
        'uploaded': path_manager.uploaded_dir,
        'processed': path_manager.processed_dir,
        'reports': path_manager.reports_dir
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

@bp.route('/update_openai_prompt', methods=['POST'])
def update_openai_prompt():
    """Update OpenAI prompt settings."""
    # Get form data
    prompt_vars = {
        'OPENAI_PROMPT_TYPE': request.form.get('OPENAI_PROMPT_TYPE', 'default'),
        'OPENAI_PROMPT_ROLE': request.form.get('OPENAI_PROMPT_ROLE', ''),
        'OPENAI_PROMPT_INSTRUCTIONS_PRE': request.form.get('OPENAI_PROMPT_INSTRUCTIONS_PRE', ''),
        'OPENAI_PROMPT_INSTRUCTIONS_POST': request.form.get('OPENAI_PROMPT_INSTRUCTIONS_POST', ''),
        'OPENAI_PROMPT_EXAMPLE': request.form.get('OPENAI_PROMPT_EXAMPLE', '')
    }

    # Update environment variables in config.env
    try:
        config_dir = get_config().config_dir
        env_path = os.path.join(config_dir, 'config.env')

        # Read existing file
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Update values
        new_lines = []
        updated_keys = set()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                new_lines.append(line)
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()

                if key in prompt_vars:
                    # Properly format the value for .env file
                    # Use triple quotes for multiline values
                    value = prompt_vars[key]
                    if '\n' in value:
                        # For multiline values, use triple quotes and preserve newlines
                        new_lines.append(f'{key}="""{value}"""')
                    else:
                        # For single line values, use regular quotes
                        new_lines.append(f'{key}="{value}"')
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add any keys that weren't in the file
        for key, value in prompt_vars.items():
            if key not in updated_keys:
                escaped_value = value.replace('"', '\\"').replace('\n', '\\n')
                new_lines.append(f'{key}="{escaped_value}"')

        # Write back to file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))

        # Reload configuration
        reload_config()

        flash("OpenAI prompt settings updated successfully. Changes have been applied.", "success")
        logger.info("OpenAI prompt settings updated via web interface and configuration reloaded")
    except Exception as e:
        flash(f"Error updating OpenAI prompt settings: {str(e)}", "danger")
        logger.error(f"Error updating OpenAI prompt settings: {str(e)}")

    return redirect(url_for('settings.index'))


@bp.route('/get_prompt_template')
def get_prompt_template():
    """Get prompt template based on type."""
    prompt_type = request.args.get('type', 'default')

    # Map prompt type to file name
    prompt_files = {
        'minimal': 'minimal_prompt.env',
        'structured_simple': 'structured_simple_prompt.env',
        'accuracy_focused': 'accuracy_focused_prompt.env',
        'examples': 'examples_prompt.env',
        'step_by_step': 'step_by_step_prompt.env',
        'optimized': 'optimized_prompt.env'
    }

    # Default response
    response = {
        'success': False,
        'error': 'Invalid prompt type'
    }

    try:
        # If using default, get from config
        if prompt_type == 'default':
            current_config = get_config()
            response = {
                'success': True,
                'role': current_config.openai.prompt_role,
                'instructions_pre': current_config.openai.prompt_instructions_pre,
                'instructions_post': current_config.openai.prompt_instructions_post,
                'example': current_config.openai.prompt_example
            }
        # If using a custom prompt file
        elif prompt_type in prompt_files:
            prompt_file = prompt_files[prompt_type]
            config_dir = get_config().config_dir
            prompt_path = os.path.join(config_dir, prompt_file)

            if os.path.exists(prompt_path):
                # Load prompt settings from file
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract settings using regex with better pattern for multiline content
                role_match = re.search(r'OPENAI_PROMPT_ROLE="(.*?)"\s*$', content, re.MULTILINE)
                instructions_pre_match = re.search(r'OPENAI_PROMPT_INSTRUCTIONS_PRE="(.*?)"\s*$', content, re.MULTILINE)
                instructions_post_match = re.search(r'OPENAI_PROMPT_INSTRUCTIONS_POST="(.*?)"\s*$', content, re.MULTILINE)

                # For the example, we need a different approach due to the complex JSON with quotes
                example_start = content.find('OPENAI_PROMPT_EXAMPLE="') + len('OPENAI_PROMPT_EXAMPLE="')
                if example_start > len('OPENAI_PROMPT_EXAMPLE="'):
                    # Find the closing quote that's not escaped
                    example_end = example_start
                    while example_end < len(content):
                        if content[example_end] == '"' and content[example_end-1] != '\\':
                            break
                        example_end += 1

                    example = content[example_start:example_end] if example_end < len(content) else ''

                response = {
                    'success': True,
                    'role': role_match.group(1) if role_match else '',
                    'instructions_pre': instructions_pre_match.group(1) if instructions_pre_match else '',
                    'instructions_post': instructions_post_match.group(1) if instructions_post_match else '',
                    'example': example if 'example' in locals() else ''
                }
            else:
                response['error'] = f'Prompt file not found: {prompt_file}'
    except Exception as e:
        logger.error(f"Error loading prompt template: {str(e)}")
        response['error'] = f'Error loading prompt template: {str(e)}'

    return jsonify(response)


@bp.route('/update_model_params', methods=['POST'])
def update_model_params():
    """Update OpenAI model parameters."""
    # Get form data
    model_params = {
        'MODEL_NAME': request.form.get('MODEL_NAME', 'gpt-4-vision-preview'),
        'MAX_TOKENS': request.form.get('MAX_TOKENS', ''),
        'TEMPERATURE': request.form.get('TEMPERATURE', '0.5'),
        'IMAGE_DETAIL': request.form.get('IMAGE_DETAIL', 'high')
    }

    # Update environment variables in config.env
    try:
        config_dir = get_config().config_dir
        env_path = os.path.join(config_dir, 'config.env')

        # Read existing file
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Update values
        new_lines = []
        updated_keys = set()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                new_lines.append(line)
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()

                if key in model_params:
                    # Properly format the value for .env file
                    value = model_params[key]
                    new_lines.append(f'{key}="{value}"')
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add any keys that weren't in the file
        for key, value in model_params.items():
            if key not in updated_keys:
                new_lines.append(f'{key}="{value}"')

        # Write back to file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))

        # Reload configuration
        reload_config()

        flash("Model parameters updated successfully. Changes have been applied.", "success")
        logger.info("OpenAI model parameters updated via web interface and configuration reloaded")
    except Exception as e:
        flash(f"Error updating model parameters: {str(e)}", "danger")
        logger.error(f"Error updating model parameters: {str(e)}")

    return redirect(url_for('settings.index'))