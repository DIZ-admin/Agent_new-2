#!/usr/bin/env python3
"""
OpenAI Photo Analyzer

This module analyzes photos using OpenAI's API from a wooden construction expert perspective
and generates metadata according to the target SharePoint library schema.
"""

import os
import json
import time
import base64
import re
import threading
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import openai
from PIL import Image
import io
import queue

# Import utilities
from src.utils.paths import get_path_manager, load_json_file, save_json_file
from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.registry import get_registry
from src.photo_metadata import extract_formatted_exif

# Get logger
logger = get_logger('openai_analyzer')

# Initial configuration
config = get_config()

# OpenAI settings
openai.api_key = config.openai.api_key
OPENAI_CONCURRENCY_LIMIT = config.openai.concurrency_limit
MAX_TOKENS = config.openai.max_tokens

# Get model parameters from environment or config
def get_model_params():
    """Get model parameters from environment or config."""
    # Get current config
    current_config = get_config()

    # Get model name
    model_name = os.environ.get('MODEL_NAME', '')
    if not model_name:
        model_name = getattr(current_config.openai, 'model_name', 'gpt-4-vision-preview')

    # Get temperature
    temperature_str = os.environ.get('TEMPERATURE', '')
    try:
        temperature = float(temperature_str) if temperature_str else 0.5
    except ValueError:
        temperature = 0.5

    # Get image detail level
    image_detail = os.environ.get('IMAGE_DETAIL', '')
    if not image_detail:
        image_detail = getattr(current_config.openai, 'image_detail', 'high')

    # Validate image detail
    if image_detail not in ['auto', 'low', 'high']:
        image_detail = 'high'

    return {
        'model_name': model_name,
        'temperature': temperature,
        'image_detail': image_detail
    }

# Metadata schema file
METADATA_SCHEMA_FILE = config.file.metadata_schema_file


def get_prompt_type():
    """
    Get the current prompt type from configuration or environment.

    Returns:
        str: Prompt type (minimal, structured_simple, accuracy_focused, examples, step_by_step, optimized, default)
    """
    # Check environment variable first
    prompt_type = os.environ.get('OPENAI_PROMPT_TYPE', '').lower()

    # If not set in environment, check config file
    if not prompt_type:
        try:
            current_config = get_config()
            prompt_type = getattr(current_config.openai, 'prompt_type', '').lower()
        except Exception:
            prompt_type = ''

    # Validate prompt type
    valid_types = ['minimal', 'structured_simple', 'accuracy_focused', 'examples', 'step_by_step', 'optimized', 'default']
    if prompt_type not in valid_types:
        prompt_type = 'default'  # Default to standard config

    return prompt_type


def get_openai_prompt_settings():
    """
    Get the current OpenAI prompt settings based on the selected prompt type.
    This allows the settings to be updated without restarting the application.

    Returns:
        tuple: (role, instructions_pre, instructions_post, example)
    """
    # Get the prompt type
    prompt_type = get_prompt_type()
    logger.info(f"Using prompt type: {prompt_type}")

    # Map prompt type to file name
    prompt_files = {
        'minimal': 'minimal_prompt.env',
        'structured_simple': 'structured_simple_prompt.env',
        'accuracy_focused': 'accuracy_focused_prompt.env',
        'examples': 'examples_prompt.env',
        'step_by_step': 'step_by_step_prompt.env',
        'optimized': 'optimized_prompt.env'
    }

    # Add any additional prompt files from config directory
    config_dir = get_config().config_dir
    for filename in os.listdir(config_dir):
        if filename.endswith('_prompt.env'):
            prompt_type_name = filename.replace('_prompt.env', '')
            if prompt_type_name not in prompt_files:
                prompt_files[prompt_type_name] = filename

    # If prompt type not found, default to optimized
    if prompt_type not in prompt_files:
        prompt_type = 'optimized'
        logger.warning(f"Prompt type '{prompt_type}' not found, defaulting to 'optimized'")

    # Get the prompt file path
    prompt_file = prompt_files[prompt_type]
    prompt_path = os.path.join(config_dir, prompt_file)

    if os.path.exists(prompt_path):
        logger.info(f"Loading prompt settings from {prompt_file}")
        try:
            # Load prompt settings from file
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract settings using regex
            role_match = re.search(r'OPENAI_PROMPT_ROLE="(.+?)"', content, re.DOTALL)
            instructions_pre_match = re.search(r'OPENAI_PROMPT_INSTRUCTIONS_PRE="(.+?)"', content, re.DOTALL)
            instructions_post_match = re.search(r'OPENAI_PROMPT_INSTRUCTIONS_POST="(.+?)"', content, re.DOTALL)
            example_match = re.search(r'OPENAI_PROMPT_EXAMPLE="(.+?)"', content, re.DOTALL)

            role = role_match.group(1) if role_match else ''
            instructions_pre = instructions_pre_match.group(1) if instructions_pre_match else ''
            instructions_post = instructions_post_match.group(1) if instructions_post_match else ''
            example = example_match.group(1) if example_match else ''

            return role, instructions_pre, instructions_post, example
        except Exception as e:
            logger.error(f"Error loading prompt settings from {prompt_file}: {str(e)}")
            logger.warning("Falling back to default prompt settings")

    # Fall back to empty values if file not found or error occurred
    logger.warning(f"Prompt file {prompt_file} not found or could not be loaded, using empty values")
    return ('', '', '', '')

# Get path manager for directories
path_manager = get_path_manager()
DOWNLOADS_DIR = path_manager.downloads_dir
METADATA_DIR = path_manager.metadata_dir
ANALYSIS_DIR = path_manager.analysis_dir

# OpenAI client is already initialized with config.openai.api_key


class OpenAIRateLimiter:
    """
    Rate limiter for OpenAI API requests to avoid hitting rate limits.
    Implements a token bucket algorithm for rate limiting.
    Also tracks total token usage for monitoring and reporting.
    """

    def __init__(self, requests_per_minute=60, max_tokens_per_minute=90000):
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute (int): Maximum number of requests per minute
            max_tokens_per_minute (int): Maximum number of tokens per minute
        """
        self.requests_per_minute = requests_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute

        # Token bucket for requests
        self.request_tokens = requests_per_minute
        self.max_request_tokens = requests_per_minute

        # Token bucket for tokens
        self.tokens = max_tokens_per_minute
        self.max_tokens = max_tokens_per_minute

        # Lock for thread safety
        self.lock = threading.Lock()

        # Last refill time
        self.last_refill_time = time.time()

        # Start the refill thread
        self.running = True
        self.refill_thread = threading.Thread(target=self._refill_tokens)
        self.refill_thread.daemon = True
        self.refill_thread.start()

        # Queue for pending requests
        self.request_queue = queue.Queue()

        # Token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()

        # Token usage by model
        self.model_usage = {}

        # Token usage history (last 24 hours in 10-minute intervals)
        self.usage_history = []
        self.last_history_update = time.time()
        self.history_interval = 600  # 10 minutes in seconds

        # Path for saving token usage statistics (in logs directory for better container sharing)
        self.stats_file = os.path.join(get_path_manager().logs_dir, 'token_usage_stats.json')

        # Load existing statistics if available
        self._load_stats()

        logger.info(f"OpenAI rate limiter initialized with {requests_per_minute} requests/min and {max_tokens_per_minute} tokens/min")

    def _refill_tokens(self):
        """
        Refill tokens periodically based on elapsed time.
        """
        while self.running:
            time.sleep(1)  # Check every second

            with self.lock:
                current_time = time.time()
                elapsed_time = current_time - self.last_refill_time

                # Calculate tokens to add based on elapsed time
                request_tokens_to_add = self.requests_per_minute * elapsed_time / 60
                tokens_to_add = self.max_tokens_per_minute * elapsed_time / 60

                # Add tokens, but don't exceed max
                self.request_tokens = min(self.max_request_tokens, self.request_tokens + request_tokens_to_add)
                self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)

                # Update last refill time
                self.last_refill_time = current_time

    def wait_for_capacity(self, tokens_needed):
        """
        Wait until there is capacity to make a request.

        Args:
            tokens_needed (int): Number of tokens needed for the request

        Returns:
            bool: True if capacity is available, False if timeout
        """
        start_time = time.time()
        max_wait_time = 60  # Maximum wait time in seconds

        while time.time() - start_time < max_wait_time:
            with self.lock:
                if self.request_tokens >= 1 and self.tokens >= tokens_needed:
                    # Consume tokens
                    self.request_tokens -= 1
                    self.tokens -= tokens_needed
                    return True

            # Wait before checking again
            wait_time = 1 + (tokens_needed / self.max_tokens_per_minute) * 10  # Dynamic wait time based on request size
            logger.debug(f"Waiting {wait_time:.2f}s for API capacity (need {tokens_needed} tokens)")
            time.sleep(wait_time)

        logger.warning(f"Timeout waiting for API capacity after {max_wait_time}s")
        return False

    def update_token_usage(self, prompt_tokens, completion_tokens, model_name):
        """
        Update token usage statistics.

        Args:
            prompt_tokens (int): Number of tokens in the prompt
            completion_tokens (int): Number of tokens in the completion
            model_name (str): Name of the model used
        """
        with self.lock:
            # Update total counts
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += prompt_tokens + completion_tokens
            self.request_count += 1

            # Update model-specific usage
            if model_name not in self.model_usage:
                self.model_usage[model_name] = {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'request_count': 0
                }

            self.model_usage[model_name]['prompt_tokens'] += prompt_tokens
            self.model_usage[model_name]['completion_tokens'] += completion_tokens
            self.model_usage[model_name]['total_tokens'] += prompt_tokens + completion_tokens
            self.model_usage[model_name]['request_count'] += 1

            # Update usage history if needed
            current_time = time.time()
            if current_time - self.last_history_update >= self.history_interval:
                # Add current usage to history
                self.usage_history.append({
                    'timestamp': current_time,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens,
                    'model_name': model_name
                })

                # Keep only last 24 hours (144 entries at 10-minute intervals)
                one_day_ago = current_time - 86400  # 24 hours in seconds
                self.usage_history = [entry for entry in self.usage_history if entry['timestamp'] > one_day_ago]

                # Update last history update time
                self.last_history_update = current_time

            # Save statistics periodically (every 10 requests or after large requests)
            if self.request_count % 10 == 0 or prompt_tokens + completion_tokens > 1000:
                self._save_stats()

    def record_error(self, error_type=None):
        """
        Record an API error.

        Args:
            error_type (str, optional): Type of error
        """
        with self.lock:
            self.error_count += 1

            # Save statistics after recording an error
            self._save_stats()

    def get_token_usage_stats(self):
        """
        Get token usage statistics.

        Returns:
            dict: Token usage statistics
        """
        with self.lock:
            # Calculate time-based metrics
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            elapsed_minutes = elapsed_time / 60

            # Calculate rates
            tokens_per_minute = self.total_tokens / elapsed_minutes if elapsed_minutes > 0 else 0
            requests_per_minute = self.request_count / elapsed_minutes if elapsed_minutes > 0 else 0

            # Calculate current usage percentages
            token_usage_percent = (self.max_tokens_per_minute - self.tokens) / self.max_tokens_per_minute * 100
            request_usage_percent = (self.max_request_tokens - self.request_tokens) / self.max_request_tokens * 100

            return {
                'total_prompt_tokens': self.total_prompt_tokens,
                'total_completion_tokens': self.total_completion_tokens,
                'total_tokens': self.total_tokens,
                'request_count': self.request_count,
                'error_count': self.error_count,
                'tokens_per_minute': tokens_per_minute,
                'requests_per_minute': requests_per_minute,
                'token_usage_percent': token_usage_percent,
                'request_usage_percent': request_usage_percent,
                'model_usage': self.model_usage,
                'elapsed_time': elapsed_time,
                'elapsed_minutes': elapsed_minutes,
                'start_time': self.start_time,
                'current_time': current_time
            }

    def get_usage_history(self):
        """
        Get token usage history.

        Returns:
            list: Token usage history
        """
        with self.lock:
            return self.usage_history.copy()

    def _load_stats(self):
        """
        Load token usage statistics from file if available.
        """
        try:
            if os.path.exists(self.stats_file):
                logger.info(f"Found token usage statistics file at {self.stats_file}")
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)

                    # Load basic statistics
                    self.total_prompt_tokens = stats.get('total_prompt_tokens', 0)
                    self.total_completion_tokens = stats.get('total_completion_tokens', 0)
                    self.total_tokens = stats.get('total_tokens', 0)
                    self.request_count = stats.get('request_count', 0)
                    self.error_count = stats.get('error_count', 0)

                    # Only update start_time if it's older than current
                    saved_start_time = stats.get('start_time', 0)
                    if saved_start_time < self.start_time:
                        self.start_time = saved_start_time

                    # Load model usage
                    self.model_usage = stats.get('model_usage', {})

                    # Load usage history
                    self.usage_history = stats.get('usage_history', [])

                    logger.info(f"Successfully loaded token usage statistics from {self.stats_file}")
                    logger.info(f"Total tokens: {self.total_tokens}, Requests: {self.request_count}, Models: {list(self.model_usage.keys())}")
            else:
                logger.info(f"No token usage statistics file found at {self.stats_file}, starting with empty stats")
        except Exception as e:
            logger.error(f"Error loading token usage statistics: {str(e)}")

    def _save_stats(self):
        """
        Save token usage statistics to file.
        """
        try:
            stats = {
                'total_prompt_tokens': self.total_prompt_tokens,
                'total_completion_tokens': self.total_completion_tokens,
                'total_tokens': self.total_tokens,
                'request_count': self.request_count,
                'error_count': self.error_count,
                'start_time': self.start_time,
                'last_update': time.time(),
                'model_usage': self.model_usage,
                'usage_history': self.usage_history
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)

            logger.info(f"Saved token usage statistics to {self.stats_file} (total tokens: {self.total_tokens}, requests: {self.request_count})")
        except Exception as e:
            logger.error(f"Error saving token usage statistics: {str(e)}")

    def shutdown(self):
        """
        Shutdown the rate limiter.
        """
        # Save statistics before shutting down
        self._save_stats()

        self.running = False
        if self.refill_thread.is_alive():
            self.refill_thread.join(timeout=1)


# Create a global rate limiter instance
_rate_limiter = None

def get_rate_limiter():
    """
    Get the rate limiter instance.

    Returns:
        OpenAIRateLimiter: Rate limiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        # Get rate limits from config or use defaults
        current_config = get_config()
        requests_per_minute = getattr(current_config.openai, 'requests_per_minute', 60)
        max_tokens_per_minute = getattr(current_config.openai, 'max_tokens_per_minute', 90000)

        _rate_limiter = OpenAIRateLimiter(requests_per_minute, max_tokens_per_minute)

    return _rate_limiter


def get_token_usage_stats():
    """
    Get token usage statistics from the rate limiter or directly from the stats file.

    Returns:
        dict: Token usage statistics or None if rate limiter is not initialized and stats file doesn't exist
    """
    # Try to get stats from rate limiter first
    rate_limiter = get_rate_limiter()
    if rate_limiter:
        return rate_limiter.get_token_usage_stats()

    # If rate limiter is not available, try to read stats directly from file
    try:
        stats_file = os.path.join(get_path_manager().logs_dir, 'token_usage_stats.json')
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)

                # Calculate time-based metrics
                current_time = time.time()
                elapsed_time = current_time - stats.get('start_time', current_time)
                elapsed_minutes = elapsed_time / 60

                # Calculate rates
                tokens_per_minute = stats.get('total_tokens', 0) / elapsed_minutes if elapsed_minutes > 0 else 0
                requests_per_minute = stats.get('request_count', 0) / elapsed_minutes if elapsed_minutes > 0 else 0

                # Add calculated metrics to stats
                stats.update({
                    'tokens_per_minute': tokens_per_minute,
                    'requests_per_minute': requests_per_minute,
                    'token_usage_percent': 0.0,  # Not available when reading directly from file
                    'request_usage_percent': 0.0,  # Not available when reading directly from file
                    'elapsed_time': elapsed_time,
                    'elapsed_minutes': elapsed_minutes,
                    'current_time': current_time
                })

                logger.info(f"Loaded token usage statistics directly from {stats_file}")
                return stats
    except Exception as e:
        logger.error(f"Error loading token usage statistics from file: {str(e)}")

    return None


def get_token_usage_history():
    """
    Get token usage history from the rate limiter or directly from the stats file.

    Returns:
        list: Token usage history or empty list if rate limiter is not initialized and stats file doesn't exist
    """
    # Try to get history from rate limiter first
    rate_limiter = get_rate_limiter()
    if rate_limiter:
        return rate_limiter.get_usage_history()

    # If rate limiter is not available, try to read history directly from file
    try:
        stats_file = os.path.join(get_path_manager().logs_dir, 'token_usage_stats.json')
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                history = stats.get('usage_history', [])
                logger.info(f"Loaded token usage history directly from {stats_file}")
                return history
    except Exception as e:
        logger.error(f"Error loading token usage history from file: {str(e)}")

    return []


def load_metadata_schema():
    """
    Load metadata schema from JSON file.

    Returns:
        dict: Metadata schema dictionary
    """
    try:
        schema = load_json_file(METADATA_SCHEMA_FILE)
        logger.info(f"Loaded metadata schema from {METADATA_SCHEMA_FILE}")
        return schema
    except Exception as e:
        logger.error(f"Error loading metadata schema: {str(e)}")
        raise


def prepare_fields_description(schema):
    """
    Prepare field descriptions from the schema.

    Args:
        schema (dict): Metadata schema dictionary

    Returns:
        str: Formatted field descriptions
    """
    try:
        # Extract field descriptions
        fields_description = "SCHEMA DEFINITION (FOLLOW EXACTLY):\n"
        for field in schema.get('fields', []):
            internal_name = field.get('internal_name')
            title = field.get('title')
            field_type = field.get('type')
            required = "Required" if field.get('required') else "Optional"
            description = field.get('description', '')

            # Skip system fields and fields that are not relevant for analysis
            if internal_name in ['FileLeafRef', 'ID', 'Created', 'Modified', 'Author', 'Editor',
                               'ContentType', 'DocIcon', 'ComplianceAssetId']:
                continue

            # Skip preview field but mention it in the description
            if internal_name == 'Vorschau':
                fields_description += f"Field: {title} (SKIP THIS FIELD - will be generated automatically)\n"
                fields_description += f"  Internal Name: {internal_name}\n"
                fields_description += f"  Type: {field_type}\n"
                fields_description += f"  Required: {required}\n\n"
                continue

            fields_description += f"Field: {title}\n"
            fields_description += f"  Internal Name: {internal_name}\n"
            fields_description += f"  Type: {field_type}\n"
            fields_description += f"  Required: {required}\n"

            # Add choices for choice fields with clear formatting
            if field_type in ['Choice', 'MultiChoice'] and 'choices' in field:
                choices = field.get('choices', [])
                if choices:
                    fields_description += "  Valid choices (use EXACTLY these values):\n"
                    for choice in choices:
                        fields_description += f"    - \"{choice}\"\n"

            # Add description if available
            if description:
                fields_description += f"  Description: {description}\n"

            fields_description += "\n"

        return fields_description
    except Exception as e:
        logger.error(f"Error preparing field descriptions: {str(e)}")
        raise


def prepare_openai_prompt(schema):
    """
    Prepare the OpenAI prompt with field descriptions from the schema.

    Args:
        schema (dict): Metadata schema dictionary

    Returns:
        str: Formatted prompt for OpenAI
    """
    try:
        # Get field descriptions
        fields_description = prepare_fields_description(schema)

        # Get current prompt settings
        role, instructions_pre, instructions_post, example = get_openai_prompt_settings()

        # Construct the full prompt
        prompt = f"{role}\n\n{instructions_pre}\n\n{fields_description}\n\n{instructions_post}\n\n{example}"

        return prompt
    except Exception as e:
        logger.error(f"Error preparing OpenAI prompt: {str(e)}")
        raise


def prepare_openai_prompt_with_exif(schema, image_path):
    """
    Prepare the OpenAI prompt with field descriptions from the schema and EXIF metadata.

    Args:
        schema (dict): Metadata schema dictionary
        image_path (str): Path to the image file

    Returns:
        str: Formatted prompt for OpenAI with EXIF data
    """
    try:
        # Get field descriptions
        fields_description = prepare_fields_description(schema)

        # Extract formatted EXIF data
        exif_data = extract_formatted_exif(image_path)

        # Get current prompt settings
        role, instructions_pre, instructions_post, example = get_openai_prompt_settings()

        # Create EXIF section
        exif_section = f"""\nEXIF METADATA FROM THE IMAGE:\n{exif_data}\n\nPlease use this EXIF information to enhance your analysis. Pay special attention to:\n1. Date and time when the photo was taken\n2. GPS coordinates and location information\n3. Camera and lens information that might indicate the quality and type of photography\n4. Any description or copyright information embedded in the image\n\nNow, analyze the image considering both the visual content and the EXIF metadata provided above.\n"""

        # Construct the full prompt with EXIF data
        prompt = f"{role}\n\n{instructions_pre}{exif_section}\n\n{fields_description}\n\n{instructions_post}\n\n{example}"

        return prompt
    except Exception as e:
        logger.error(f"Error preparing OpenAI prompt with EXIF: {str(e)}")
        # Fallback to standard prompt if there's an error
        return prepare_openai_prompt(schema)


def encode_image_to_base64(image_path):
    """
    Encode an image to base64 for OpenAI API.

    Args:
        image_path (str): Path to image file

    Returns:
        str: Base64-encoded image
    """
    try:
        # Open and resize image if needed (to reduce API costs)
        with Image.open(image_path) as img:
            # Check if image needs resizing (max dimension 1024)
            max_dim = max(img.width, img.height)
            if max_dim > 1024:
                scale_factor = 1024 / max_dim
                new_width = int(img.width * scale_factor)
                new_height = int(img.height * scale_factor)
                img = img.resize((new_width, new_height))

            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Save to bytes buffer
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)

            # Encode to base64
            base64_image = base64.b64encode(buffer.read()).decode('utf-8')

        return base64_image
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {str(e)}")
        raise


def analyze_photo_with_openai(image_path, schema, max_retries=3, use_exif=True, use_custom_prompt=False, custom_prompt=None):
    """
    Analyze a photo using OpenAI's API with retry mechanism.

    Args:
        image_path (str): Path to image file
        schema (dict): Metadata schema dictionary
        max_retries (int): Maximum number of retry attempts
        use_exif (bool): Whether to include EXIF data in the prompt
        use_custom_prompt (bool): Whether to use a custom prompt
        custom_prompt (str): Custom prompt to use

    Returns:
        dict: Analysis results
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            logger.info(f"Analyzing photo: {os.path.basename(image_path)} (Attempt {retry_count + 1}/{max_retries})")

            # Determine which prompt to use
            if use_custom_prompt and custom_prompt:
                prompt = custom_prompt
                logger.info(f"Using custom prompt for {os.path.basename(image_path)}")
            elif use_exif:
                prompt = prepare_openai_prompt_with_exif(schema, image_path)
                logger.info(f"Using prompt with EXIF data for {os.path.basename(image_path)}")
            else:
                prompt = prepare_openai_prompt(schema)
                logger.info(f"Using standard prompt for {os.path.basename(image_path)}")

            # Encode image to base64
            base64_image = encode_image_to_base64(image_path)

            # Get model parameters
            model_params = get_model_params()

            # Get rate limiter
            rate_limiter = get_rate_limiter()

            # Estimate tokens needed for this request
            # Base tokens for prompt + estimated tokens for image + response tokens
            prompt_tokens = len(prompt) // 4  # Rough estimate: 4 chars per token
            image_tokens = 1000 if model_params['image_detail'] == 'low' else 3000  # Rough estimate based on detail level
            response_tokens = MAX_TOKENS
            total_tokens_estimate = prompt_tokens + image_tokens + response_tokens

            logger.info(f"Estimated tokens for request: {total_tokens_estimate} (prompt: {prompt_tokens}, image: {image_tokens}, response: {response_tokens})")

            # Wait for capacity before making the request
            if not rate_limiter.wait_for_capacity(total_tokens_estimate):
                raise Exception(f"Timeout waiting for API capacity. Try again later.")

            # Create OpenAI API request
            response = openai.chat.completions.create(
                model=model_params['model_name'],
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze this image in detail. Pay special attention to construction materials, architectural elements, and design features. Provide a comprehensive analysis that captures all relevant aspects of the wooden construction:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": model_params['image_detail']
                                }
                            }
                        ]
                    }
                ],
                max_tokens=MAX_TOKENS,
                temperature=model_params['temperature']
            )

            # Log and track actual token usage
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens

                # Log token usage
                logger.info(f"Actual token usage: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens})")

                # Update token usage statistics
                rate_limiter.update_token_usage(prompt_tokens, completion_tokens, model_params['model_name'])

            # Extract and parse JSON response
            result_text = response.choices[0].message.content

            # Try to parse JSON from the response
            try:
                # Find JSON object in the response (in case there's additional text)
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = json.loads(result_text)

                # If we got a valid JSON, return it
                logger.info(f"Successfully analyzed photo: {os.path.basename(image_path)}")
                return result

            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from OpenAI response: {result_text}")

                # If this is the last retry, return the error
                if retry_count == max_retries - 1:
                    result = {"error": "Failed to parse JSON from response", "raw_response": result_text}
                    return result

                # Otherwise, increment retry count and try again
                retry_count += 1
                logger.info(f"Retrying analysis for {os.path.basename(image_path)}...")

                # Add a small delay before retrying to avoid rate limits
                time.sleep(2)
                continue

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error analyzing photo {os.path.basename(image_path)}: {error_msg}")

            # Record the error in rate limiter statistics
            rate_limiter.record_error(error_type="API Error")

            # Check if this is a rate limit error
            is_rate_limit_error = "rate limit" in error_msg.lower()
            if is_rate_limit_error:
                # Extract wait time from error message if available
                wait_time_match = re.search(r'try again in (\d+\.?\d*)s', error_msg.lower())
                wait_time = float(wait_time_match.group(1)) if wait_time_match else 5

                logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry.")
                time.sleep(wait_time + 1)  # Add 1 second buffer

            # If this is the last retry, return the error
            if retry_count == max_retries - 1:
                return {"error": error_msg}

            # Otherwise, increment retry count and try again
            retry_count += 1
            logger.info(f"Retrying analysis for {os.path.basename(image_path)}... (Attempt {retry_count + 1}/{max_retries})")

            # Add a small delay before retrying to avoid rate limits if not already waiting
            if not is_rate_limit_error:
                time.sleep(2)
            continue

    # This should not be reached, but just in case
    return {"error": "Maximum retry attempts exceeded"}


def save_analysis_to_json(analysis, image_path):
    """
    Save analysis results to a JSON file.

    Args:
        analysis (dict): Analysis results
        image_path (str): Path to image file

    Returns:
        str: Path to JSON file
    """
    try:
        # Create JSON file path with same name as image but .json extension
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        json_path = ANALYSIS_DIR / f"{base_name}_analysis.json"

        # Save analysis to JSON file
        save_json_file(analysis, json_path)

        logger.info(f"Analysis saved to: {json_path}")
        return json_path
    except Exception as e:
        logger.error(f"Error saving analysis to JSON: {str(e)}")
        raise


def process_photo_with_openai(photo_info, schema, max_retries=3):
    """
    Process a photo with OpenAI API.
    Uses context from similar photos to improve analysis quality.
    Implements advanced error handling and retry mechanisms.

    Args:
        photo_info (dict): Photo information dictionary
        schema (dict): Metadata schema dictionary
        max_retries (int): Maximum number of retry attempts for the entire process

    Returns:
        dict: Processed photo information
    """
    retry_count = 0
    last_error = None
    backoff_time = 1  # Initial backoff time in seconds

    while retry_count < max_retries:
        try:
            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count}/{max_retries} for {photo_info['name']} after {backoff_time}s delay")
                time.sleep(backoff_time)
                # Exponential backoff with jitter for retries
                backoff_time = min(30, backoff_time * 2) * (0.8 + 0.4 * random.random())

            # Get context from similar photos
            similar_photos_context = get_similar_photos_context(photo_info['local_path'])
            if similar_photos_context:
                logger.info(f"Using context from similar photos for: {photo_info['name']}")

                # Prepare custom prompt with context
                role, instructions_pre, instructions_post, example = get_openai_prompt_settings()

                # Prepare field descriptions
                fields_description = prepare_fields_description(schema)

                # Add context to instructions
                instructions_pre = f"{instructions_pre}{similar_photos_context}"

                # Create custom prompt
                custom_prompt = f"{role}\n\n{instructions_pre}\n\n{fields_description}\n\n{instructions_post}\n\n{example}"

                # Analyze photo with OpenAI using custom prompt and EXIF data
                analysis = analyze_photo_with_openai(photo_info['local_path'], schema, use_exif=True, use_custom_prompt=True, custom_prompt=custom_prompt)
            else:
                # Analyze photo with OpenAI using EXIF data
                analysis = analyze_photo_with_openai(photo_info['local_path'], schema, use_exif=True)

            # Check if analysis contains an error
            if 'error' in analysis:
                error_msg = analysis.get('error', '')
                logger.error(f"Analysis failed for {photo_info['name']}: {error_msg}")

                # Check if this is a retryable error
                retryable_errors = [
                    "Failed to parse JSON",
                    "rate limit",
                    "timeout",
                    "connection",
                    "network",
                    "server",
                    "capacity"
                ]

                if any(err in error_msg.lower() for err in retryable_errors) and retry_count < max_retries - 1:
                    # This is a retryable error and we have retries left
                    last_error = error_msg
                    retry_count += 1
                    logger.info(f"Retryable error detected, will retry: {error_msg}")
                    continue
                else:
                    # Non-retryable error or out of retries
                    photo_info['error'] = error_msg
                    if 'raw_response' in analysis:
                        photo_info['raw_response'] = analysis['raw_response']
                    return photo_info

            # Save analysis to JSON
            analysis_path = save_analysis_to_json(analysis, photo_info['local_path'])

            # Add analysis to photo info
            photo_info['analysis_path'] = analysis_path
            photo_info['analysis'] = analysis

            # Log completion
            logger.info(f"Completed OpenAI analysis for: {photo_info['name']}")

            return photo_info

        except Exception as e:
            last_error = str(e)
            logger.error(f"Error processing photo {photo_info['name']} with OpenAI: {last_error}")

            # Check if this is a retryable exception
            retryable_exceptions = [
                "rate limit",
                "timeout",
                "connection",
                "network",
                "server",
                "capacity",
                "too many requests"
            ]

            if any(err in last_error.lower() for err in retryable_exceptions) and retry_count < max_retries - 1:
                # This is a retryable exception and we have retries left
                retry_count += 1
                logger.info(f"Retryable exception detected, will retry: {last_error}")
                continue
            else:
                # Non-retryable exception or out of retries
                photo_info['error'] = last_error
                return photo_info

    # If we get here, we've exhausted all retries
    photo_info['error'] = f"Maximum retry attempts ({max_retries}) exceeded. Last error: {last_error}"
    return photo_info


def get_similar_photos_context(photo_path, max_similar=3):
    """
    Find similar photos that have already been analyzed to provide context.

    Args:
        photo_path (str): Path to the current photo
        max_similar (int): Maximum number of similar photos to include

    Returns:
        str: Context from similar photos or empty string if none found
    """
    try:
        # Get the directory containing the photo
        photo_dir = os.path.dirname(photo_path)
        photo_name = os.path.basename(photo_path)

        # Look for analyzed photos in the same directory
        analysis_dir = path_manager.analysis_dir
        context = ""
        similar_count = 0

        # Check if analysis directory exists
        if not os.path.exists(analysis_dir):
            return ""

        # Get all analysis files
        analysis_files = [f for f in os.listdir(analysis_dir) if f.endswith('_analysis.json')]

        # Sort by modification time (newest first)
        analysis_files.sort(key=lambda f: os.path.getmtime(os.path.join(analysis_dir, f)), reverse=True)

        # Get context from up to max_similar recent analyses
        for analysis_file in analysis_files:
            if similar_count >= max_similar:
                break

            analysis_path = os.path.join(analysis_dir, analysis_file)
            try:
                with open(analysis_path, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)

                # Skip if this is the same photo
                if analysis_file == photo_name.replace('.jpg', '_analysis.json').replace('.jpeg', '_analysis.json'):
                    continue

                # Add to context
                if 'Titel' in analysis_data and 'Beschreibung' in analysis_data:
                    context += f"Similar photo: {analysis_data['Titel']}\n"
                    context += f"Description: {analysis_data['Beschreibung']}\n"
                    if 'Material' in analysis_data:
                        materials = analysis_data['Material']
                        if isinstance(materials, list):
                            context += f"Materials: {', '.join(materials)}\n"
                        else:
                            context += f"Materials: {materials}\n"
                    context += "\n"
                    similar_count += 1
            except Exception as e:
                logger.warning(f"Error reading analysis file {analysis_file}: {str(e)}")
                continue

        if context:
            return f"\n\nCONTEXT FROM SIMILAR PHOTOS:\n{context}\nUse this context as reference, but ensure your analysis is specific to the current image."
        return ""
    except Exception as e:
        logger.error(f"Error getting similar photos context: {str(e)}")
        return ""


def process_photos_with_openai(photos, schema):
    """
    Process multiple photos with OpenAI API using thread pool.
    Automatically retries photos that failed due to JSON parsing errors.
    Skips photos that have already been analyzed based on their hash.
    Uses context from similar photos to improve analysis quality.

    Args:
        photos (list): List of photo information dictionaries
        schema (dict): Metadata schema dictionary

    Returns:
        list: List of processed photo information dictionaries
    """
    processed_photos = []
    failed_photos = []
    skipped_photos = []
    photos_to_process = []
    registry = get_registry()

    # First, filter out photos that have already been analyzed
    for photo in photos:
        local_path = photo.get('local_path')
        if not local_path:
            # If no local path, we can't check the hash
            photos_to_process.append(photo)
            continue

        # Check if analysis file already exists
        base_name = os.path.splitext(os.path.basename(local_path))[0]
        analysis_path = ANALYSIS_DIR / f"{base_name}_analysis.json"

        if analysis_path.exists() and registry.is_file_processed_by_hash(local_path):
            logger.info(f"Skipping already analyzed photo: {photo['name']}")

            # Load existing analysis
            try:
                analysis = load_json_file(analysis_path)
                photo['analysis_path'] = analysis_path
                photo['analysis'] = analysis
                skipped_photos.append(photo)
            except Exception as e:
                logger.warning(f"Failed to load existing analysis for {photo['name']}: {str(e)}")
                photos_to_process.append(photo)
        else:
            photos_to_process.append(photo)

    logger.info(f"Found {len(photos)} photos, {len(skipped_photos)} already analyzed, {len(photos_to_process)} to process")

    # If no photos to process, return the skipped ones
    if not photos_to_process:
        return skipped_photos

    # Initialize rate limiter
    rate_limiter = get_rate_limiter()
    logger.info(f"Using rate limiter with {rate_limiter.requests_per_minute} requests/min and {rate_limiter.max_tokens_per_minute} tokens/min")

    # Use ThreadPoolExecutor for concurrent processing with limited concurrency
    with ThreadPoolExecutor(max_workers=OPENAI_CONCURRENCY_LIMIT) as executor:
        # Submit tasks
        future_to_photo = {executor.submit(process_photo_with_openai, photo, schema): photo for photo in photos_to_process}

        # Process results as they complete
        for future in future_to_photo:
            try:
                processed_photo = future.result()

                # Check if the photo has an error
                if 'error' in processed_photo:
                    error_msg = processed_photo.get('error', '')
                    # If the error is related to JSON parsing, add to failed_photos for retry
                    if 'Failed to parse JSON from response' in error_msg:
                        logger.warning(f"Adding {processed_photo['name']} to retry queue due to JSON parsing error")
                        failed_photos.append(processed_photo)
                    else:
                        # For other errors, just add to processed_photos
                        processed_photos.append(processed_photo)
                else:
                    # No error, add to processed_photos and register the hash
                    processed_photos.append(processed_photo)

                    # Register the file hash if analysis was successful
                    if 'local_path' in processed_photo and 'analysis_path' in processed_photo:
                        registry.register_file_hash(processed_photo['local_path'], {
                            'analysis_path': str(processed_photo['analysis_path']),
                            'timestamp': datetime.now().isoformat()
                        })
            except Exception as e:
                photo = future_to_photo[future]
                logger.error(f"Error in OpenAI analysis for {photo['name']}: {str(e)}")
                photo['error'] = str(e)
                processed_photos.append(photo)

    # Retry failed photos (those with JSON parsing errors)
    if failed_photos:
        logger.info(f"Retrying {len(failed_photos)} photos that failed due to JSON parsing errors")

        # Process each failed photo sequentially to maximize chances of success
        for photo in failed_photos:
            # Remove the error before retrying
            if 'error' in photo:
                del photo['error']

            logger.info(f"Retrying analysis for {photo['name']}...")
            processed_photo = process_photo_with_openai(photo, schema)
            processed_photos.append(processed_photo)

            # Register the file hash if retry was successful
            if 'error' not in processed_photo and 'local_path' in processed_photo and 'analysis_path' in processed_photo:
                registry.register_file_hash(processed_photo['local_path'], {
                    'analysis_path': str(processed_photo['analysis_path']),
                    'timestamp': datetime.now().isoformat()
                })

    # Combine processed and skipped photos
    all_photos = processed_photos + skipped_photos
    logger.info(f"Total photos: {len(all_photos)} (processed: {len(processed_photos)}, skipped: {len(skipped_photos)})")
    return all_photos


def cleanup_resources():
    """
    Clean up resources before exiting.
    """
    # Shutdown rate limiter
    if _rate_limiter is not None:
        logger.info("Shutting down rate limiter")
        _rate_limiter.shutdown()

if __name__ == "__main__":
    try:
        # Load metadata schema
        schema = load_metadata_schema()

        # Prepare OpenAI prompt
        prompt = prepare_openai_prompt(schema)
        print("\nPrepared OpenAI prompt:")
        print("------------------------")
        try:
            print(prompt)
        except UnicodeEncodeError:
            print("[Prompt contains Unicode characters that cannot be displayed in the current console]")
        print("------------------------\n")

        # Find all photos in downloads and processed directories
        photos_to_analyze = []
        processed_dir = path_manager.data_dir / "processed"
        processed_dir.mkdir(exist_ok=True)

        # Check downloads directory
        for filename in os.listdir(DOWNLOADS_DIR):
            if os.path.isfile(os.path.join(DOWNLOADS_DIR, filename)):
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    # Add to photos to analyze
                    photos_to_analyze.append({
                        'name': filename,
                        'local_path': os.path.join(DOWNLOADS_DIR, filename)
                    })

        # Check processed directory
        for filename in os.listdir(processed_dir):
            if os.path.isfile(os.path.join(processed_dir, filename)):
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    # Add to photos to analyze
                    photos_to_analyze.append({
                        'name': filename,
                        'local_path': os.path.join(processed_dir, filename)
                    })

        if photos_to_analyze:
            print(f"Found {len(photos_to_analyze)} photos in directories")

            # Process all photos in batches
            batch_size = 10  # Process 10 photos at a time
            total_photos = len(photos_to_analyze)
            processed_photos = []

            for i in range(0, total_photos, batch_size):
                batch_end = min(i + batch_size, total_photos)
                current_batch = photos_to_analyze[i:batch_end]
                print(f"Processing batch {i//batch_size + 1} of {(total_photos + batch_size - 1)//batch_size} ({len(current_batch)} photos)...")

                batch_results = process_photos_with_openai(current_batch, schema)
                processed_photos.extend(batch_results)

                print(f"Completed batch {i//batch_size + 1} ({len(batch_results)} photos processed)")

            logger.info(f"Successfully processed {len(processed_photos)} photos with OpenAI API")
            print(f"\nSuccessfully processed {len(processed_photos)} photos with OpenAI API")
            logger.info(f"Analysis results saved to: {ANALYSIS_DIR}")
            print(f"Analysis results saved to: {ANALYSIS_DIR}")

            # Print sample analysis
            if processed_photos:
                logger.info(f"Sample analysis for first photo: {processed_photos[0].get('analysis', {})}")
                print("\nSample analysis for first photo:")
                print(json.dumps(processed_photos[0].get('analysis', {}), indent=2, ensure_ascii=False))
        else:
            print("No photos found in downloads directory. Please run photo_metadata.py first to download photos.")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        # Clean up resources
        cleanup_resources()
