#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Временный скрипт для проверки всех доступных свойств полей в SharePoint
"""

import os
import sys
import json
from dotenv import load_dotenv

# Adjust import path for local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sharepoint_auth import get_sharepoint_context, get_library

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.env'))

# SharePoint settings
SITE_URL = os.getenv('SHAREPOINT_SITE_URL')
TARGET_LIBRARY_TITLE = os.getenv('SHAREPOINT_LIBRARY')

def check_field_properties():
    """
    Check all available properties of fields in SharePoint library
    """
    try:
        # Get SharePoint context and library
        ctx = get_sharepoint_context()
        library = get_library(ctx, TARGET_LIBRARY_TITLE)
        
        # Get all fields
        fields = library.fields
        ctx.load(fields)
        ctx.execute_query()
        
        # Print all fields
        print(f"Found {len(fields)} fields in library {TARGET_LIBRARY_TITLE}")
        
        # Check fields with 'KI' in name
        for field in fields:
            if 'KI' in field.internal_name:
                print(f"\nField: {field.internal_name}")
                
                # Get all properties
                ctx.load(field)
                ctx.execute_query()
                
                # Print all properties
                print("Properties:")
                for prop_name in dir(field):
                    if not prop_name.startswith('_') and prop_name not in ['execute_query_retryable', 'from_json', 'get_property', 'set_property']:
                        try:
                            prop_value = getattr(field, prop_name)
                            if not callable(prop_value):
                                print(f"  {prop_name}: {prop_value}")
                        except Exception as e:
                            print(f"  {prop_name}: Error - {str(e)}")
                
                # Get properties dictionary
                print("\nProperties dictionary:")
                for prop_name, prop_value in field.properties.items():
                    print(f"  {prop_name}: {prop_value}")
                
                break
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_field_properties()
