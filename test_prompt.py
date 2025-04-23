#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to generate and display a complete OpenAI prompt
"""

import os
import sys
import json
import logging

# Add src directory to path
sys.path.append('src')

# Import functions from openai_analyzer
from openai_analyzer import (
    prepare_openai_prompt,
    prepare_openai_prompt_with_exif,
    get_prompt_type,
    get_openai_prompt_settings,
    prepare_fields_description
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Generate and display a complete OpenAI prompt
    """
    # Load metadata schema
    schema_path = 'config/sharepoint_choices.json'
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found: {schema_path}")
        return
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except Exception as e:
        logger.error(f"Error loading schema: {str(e)}")
        return
    
    # Get prompt type
    prompt_type = get_prompt_type()
    logger.info(f"Using prompt type: {prompt_type}")
    
    # Generate standard prompt
    standard_prompt = prepare_openai_prompt(schema)
    
    # Print complete prompt
    logger.info("Complete standard prompt:")
    print("\n" + "="*80)
    print(standard_prompt)
    print("="*80 + "\n")
    
    # Get prompt components
    role, instructions_pre, instructions_post, example = get_openai_prompt_settings()
    fields_description = prepare_fields_description(schema)
    
    # Print prompt components
    logger.info("Prompt components:")
    print("\n" + "-"*40 + " ROLE " + "-"*40)
    print(role)
    
    print("\n" + "-"*40 + " INSTRUCTIONS PRE " + "-"*40)
    print(instructions_pre)
    
    print("\n" + "-"*40 + " FIELDS DESCRIPTION " + "-"*40)
    print(fields_description)
    
    print("\n" + "-"*40 + " INSTRUCTIONS POST " + "-"*40)
    print(instructions_post)
    
    print("\n" + "-"*40 + " EXAMPLE " + "-"*40)
    print(example)
    
    # Try to generate a prompt with EXIF data if a sample image is available
    sample_images_dir = 'data/downloads'
    if os.path.exists(sample_images_dir):
        image_files = [f for f in os.listdir(sample_images_dir) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if image_files:
            sample_image = os.path.join(sample_images_dir, image_files[0])
            logger.info(f"Generating prompt with EXIF data from sample image: {sample_image}")
            
            try:
                exif_prompt = prepare_openai_prompt_with_exif(schema, sample_image)
                print("\n" + "="*80)
                print("PROMPT WITH EXIF DATA:")
                print(exif_prompt)
                print("="*80)
            except Exception as e:
                logger.error(f"Error generating prompt with EXIF data: {str(e)}")
        else:
            logger.info("No sample images found to generate prompt with EXIF data")

if __name__ == "__main__":
    main()
