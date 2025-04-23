#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to optimize the OpenAI prompt for photo analysis using OpenAI API.
This script is designed to run inside the Docker container.
It takes the sharepoint_choices.json and prompt template files from the config directory,
sends them to OpenAI API for optimization, and saves the optimized prompt to a new file.
"""

import os
import sys
import json
import re
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add the src directory to the path
sys.path.append('/app/src')

# Import application modules
try:
    # Try to import from the correct module path
    from src.utils.config import get_config
    import openai

    # Get OpenAI API key from the application config
    config = get_config()
    if hasattr(config, 'openai') and hasattr(config.openai, 'api_key'):
        openai.api_key = config.openai.api_key
        logger.info("Using OpenAI API key from application config")
    else:
        logger.error("OpenAI API key not found in application config.")
        exit(1)
except ImportError as e:
    logger.error(f"Error importing application modules: {str(e)}")
    exit(1)

def load_json_file(file_path):
    """Load JSON file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        raise

def load_prompt_template(file_path):
    """Load prompt template from .env file and return its components."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract components using regex
        role_match = re.search(r'OPENAI_PROMPT_ROLE="(.+?)"', content, re.DOTALL)
        instructions_pre_match = re.search(r'OPENAI_PROMPT_INSTRUCTIONS_PRE="(.+?)"', content, re.DOTALL)
        instructions_post_match = re.search(r'OPENAI_PROMPT_INSTRUCTIONS_POST="(.+?)"', content, re.DOTALL)
        example_match = re.search(r'OPENAI_PROMPT_EXAMPLE="(.+?)"', content, re.DOTALL)

        role = role_match.group(1) if role_match else ''
        instructions_pre = instructions_pre_match.group(1) if instructions_pre_match else ''
        instructions_post = instructions_post_match.group(1) if instructions_post_match else ''
        example = example_match.group(1) if example_match else ''

        return {
            'role': role,
            'instructions_pre': instructions_pre,
            'instructions_post': instructions_post,
            'example': example
        }
    except Exception as e:
        logger.error(f"Error loading prompt template from {file_path}: {str(e)}")
        raise

def optimize_prompt_with_openai(schema, prompt_template, model="gpt-4o"):
    """
    Use OpenAI API to optimize the prompt based on the schema and template.

    Args:
        schema (dict): The metadata schema from sharepoint_choices.json
        prompt_template (dict): The prompt template components
        model (str): The OpenAI model to use

    Returns:
        dict: The optimized prompt components
    """
    logger.info(f"Optimizing prompt using OpenAI {model} model...")

    # Prepare the system message
    system_message = """
    You are an expert prompt engineer specializing in optimizing prompts for image analysis systems.
    Your task is to create a highly optimized, efficient prompt for an AI system that analyzes architectural photos,
    particularly focusing on wooden buildings and structures.

    The prompt should be optimized for:
    1. Token efficiency - minimize the number of tokens while preserving all necessary information
    2. Clarity - ensure the instructions are clear and unambiguous
    3. Structure - organize the information in a logical, easy-to-process structure
    4. Completeness - ensure all necessary fields and instructions are included

    The prompt will be used with OpenAI's vision models (like GPT-4o) to analyze photos and extract metadata
    according to a specific schema. The output should be a valid JSON object that follows the schema.

    Your response should include four components:
    1. ROLE - The role the AI should assume (keep this concise but effective)
    2. INSTRUCTIONS_PRE - Instructions before the schema definition
    3. INSTRUCTIONS_POST - Instructions after the schema definition
    4. EXAMPLE - A complete example of the expected JSON output

    Each component should be optimized for token efficiency while maintaining clarity and effectiveness.
    """

    # Prepare the user message with the schema and template
    user_message = f"""
    I need to optimize a prompt for an AI system that analyzes architectural photos.

    Here is the current metadata schema (from sharepoint_choices.json):
    ```json
    {json.dumps(schema, indent=2, ensure_ascii=False)}
    ```

    Here are the current prompt components:

    ROLE:
    ```
    {prompt_template['role']}
    ```

    INSTRUCTIONS_PRE:
    ```
    {prompt_template['instructions_pre']}
    ```

    INSTRUCTIONS_POST:
    ```
    {prompt_template['instructions_post']}
    ```

    EXAMPLE:
    ```
    {prompt_template['example']}
    ```

    Please optimize these prompt components to be more token-efficient while maintaining their effectiveness.
    Group related fields together, remove redundancies, and make the instructions clearer and more concise.

    The prompt will be used with OpenAI's vision models to analyze photos of wooden buildings and structures.
    The output should be a valid JSON object that follows the schema defined in sharepoint_choices.json.

    Important requirements:
    1. All text values must be in Swiss German
    2. The Status field must always be set to "Entwurf KI"
    3. All fields must be filled (use "none" for fields where no value can be determined)
    4. Choice fields must exactly match one of the provided options
    5. MultiChoice fields must be arrays with values that exactly match the provided options

    Return the optimized components in the following format:

    ROLE:
    [optimized role text]

    INSTRUCTIONS_PRE:
    [optimized instructions_pre text]

    INSTRUCTIONS_POST:
    [optimized instructions_post text]

    EXAMPLE:
    [optimized example text]
    """

    try:
        # Call OpenAI API
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        # Extract the response content
        content = response.choices[0].message.content

        # Parse the response to extract the optimized components
        role_match = re.search(r'ROLE:\s*(.+?)(?=\n\s*INSTRUCTIONS_PRE:)', content, re.DOTALL)
        instructions_pre_match = re.search(r'INSTRUCTIONS_PRE:\s*(.+?)(?=\n\s*INSTRUCTIONS_POST:)', content, re.DOTALL)
        instructions_post_match = re.search(r'INSTRUCTIONS_POST:\s*(.+?)(?=\n\s*EXAMPLE:)', content, re.DOTALL)
        example_match = re.search(r'EXAMPLE:\s*(.+)', content, re.DOTALL)

        optimized_prompt = {
            'role': role_match.group(1).strip() if role_match else prompt_template['role'],
            'instructions_pre': instructions_pre_match.group(1).strip() if instructions_pre_match else prompt_template['instructions_pre'],
            'instructions_post': instructions_post_match.group(1).strip() if instructions_post_match else prompt_template['instructions_post'],
            'example': example_match.group(1).strip() if example_match else prompt_template['example']
        }

        # Log token usage
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        logger.info(f"Token usage: {total_tokens} total (prompt: {prompt_tokens}, completion: {completion_tokens})")

        return optimized_prompt

    except Exception as e:
        logger.error(f"Error optimizing prompt with OpenAI: {str(e)}")
        raise

def save_optimized_prompt(optimized_prompt, output_file):
    """Save the optimized prompt to a file."""
    try:
        content = f"""# --- OpenAI Optimized Prompt ---
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Роль, которую должна играть модель
OPENAI_PROMPT_ROLE="{optimized_prompt['role']}"

# Инструкции перед списком полей
OPENAI_PROMPT_INSTRUCTIONS_PRE="{optimized_prompt['instructions_pre']}"

# Инструкции после списка полей
OPENAI_PROMPT_INSTRUCTIONS_POST="{optimized_prompt['instructions_post']}"

# Пример формата JSON
OPENAI_PROMPT_EXAMPLE="{optimized_prompt['example']}"
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Optimized prompt saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving optimized prompt to {output_file}: {str(e)}")
        raise

def main():
    """Main function to optimize the prompt."""
    parser = argparse.ArgumentParser(description='Optimize OpenAI prompt for photo analysis')
    parser.add_argument('--schema', type=str, default='/app/config/sharepoint_choices.json',
                        help='Path to the sharepoint_choices.json file')
    parser.add_argument('--template', type=str, default='/app/config/default_prompt.env',
                        help='Path to the prompt template file')
    parser.add_argument('--output', type=str, default='/app/config/optimized_prompt.env',
                        help='Path to save the optimized prompt')
    parser.add_argument('--model', type=str, default='gpt-4o',
                        help='OpenAI model to use for optimization')

    args = parser.parse_args()

    try:
        # Load schema and template
        logger.info(f"Loading schema from {args.schema}")
        schema = load_json_file(args.schema)

        logger.info(f"Loading prompt template from {args.template}")
        prompt_template = load_prompt_template(args.template)

        # Optimize prompt
        optimized_prompt = optimize_prompt_with_openai(schema, prompt_template, args.model)

        # Save optimized prompt
        save_optimized_prompt(optimized_prompt, args.output)

        logger.info("Prompt optimization completed successfully")

    except Exception as e:
        logger.error(f"Error in prompt optimization: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
