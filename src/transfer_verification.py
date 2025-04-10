#!/usr/bin/env python3
"""
Transfer Verification and Report Generator

This module verifies the transfer of photos to SharePoint and generates a report.
"""

import os
import json
import logging
import datetime
from dotenv import load_dotenv
from sharepoint_auth import get_sharepoint_context, get_library

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sharepoint_connector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('transfer_verification')

# Load environment variables
load_dotenv('config.env')

# SharePoint settings
TARGET_LIBRARY_TITLE = os.getenv('SHAREPOINT_LIBRARY')

# Directories
UPLOADED_DIR = os.path.join(os.getcwd(), 'uploaded')
REPORTS_DIR = os.path.join(os.getcwd(), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def get_uploaded_files():
    """
    Get list of uploaded files.
    
    Returns:
        list: List of uploaded file information dictionaries
    """
    try:
        uploaded_files = []
        
        # Check for files in uploaded directory
        for filename in os.listdir(UPLOADED_DIR):
            if os.path.isfile(os.path.join(UPLOADED_DIR, filename)):
                # Skip metadata files
                if filename.endswith('.json'):
                    continue
                    
                # Check if metadata exists
                base_name = os.path.splitext(filename)[0]
                metadata_path = os.path.join(UPLOADED_DIR, f"{base_name}.json")
                
                if os.path.exists(metadata_path):
                    # Load metadata
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        
                    # Add to uploaded files
                    uploaded_files.append({
                        'name': filename,
                        'path': os.path.join(UPLOADED_DIR, filename),
                        'metadata_path': metadata_path,
                        'metadata': metadata
                    })
        
        logger.info(f"Found {len(uploaded_files)} uploaded files")
        return uploaded_files
    except Exception as e:
        logger.error(f"Error getting uploaded files: {str(e)}")
        raise


def verify_files_in_sharepoint(ctx, library, uploaded_files):
    """
    Verify that files exist in SharePoint library.
    
    Args:
        ctx (ClientContext): SharePoint client context
        library: SharePoint library object
        uploaded_files (list): List of uploaded file information dictionaries
        
    Returns:
        tuple: (verified_files, missing_files)
    """
    try:
        # Get all items in the library
        items = library.items
        ctx.load(items)
        ctx.execute_query()
        
        # Get filenames in library
        library_files = {}
        for item in items:
            filename = item.properties.get('FileLeafRef', '')
            if filename:
                library_files[filename] = item.properties
        
        # Verify each uploaded file
        verified_files = []
        missing_files = []
        
        for file_info in uploaded_files:
            filename = file_info['name']
            
            if filename in library_files:
                # File exists in library
                file_info['sharepoint_properties'] = library_files[filename]
                verified_files.append(file_info)
            else:
                # File not found in library
                missing_files.append(file_info)
        
        logger.info(f"Verified {len(verified_files)} files in SharePoint")
        logger.info(f"Found {len(missing_files)} files missing from SharePoint")
        
        return verified_files, missing_files
    except Exception as e:
        logger.error(f"Error verifying files in SharePoint: {str(e)}")
        raise


def verify_metadata_in_sharepoint(verified_files):
    """
    Verify that metadata was correctly applied in SharePoint.
    
    Args:
        verified_files (list): List of verified file information dictionaries
        
    Returns:
        tuple: (correct_metadata, incorrect_metadata)
    """
    try:
        correct_metadata = []
        incorrect_metadata = []
        
        for file_info in verified_files:
            filename = file_info['name']
            local_metadata = file_info['metadata']
            sharepoint_properties = file_info.get('sharepoint_properties', {})
            
            # Check each metadata field
            metadata_issues = []
            
            for field_name, local_value in local_metadata.items():
                # Skip filename field as it's handled differently
                if field_name == 'FileLeafRef':
                    continue
                
                # Get SharePoint value
                sp_value = sharepoint_properties.get(field_name)
                
                # Compare values
                if sp_value != local_value:
                    metadata_issues.append({
                        'field': field_name,
                        'local_value': local_value,
                        'sharepoint_value': sp_value
                    })
            
            # Add to appropriate list
            if metadata_issues:
                file_info['metadata_issues'] = metadata_issues
                incorrect_metadata.append(file_info)
            else:
                correct_metadata.append(file_info)
        
        logger.info(f"Found {len(correct_metadata)} files with correct metadata")
        logger.info(f"Found {len(incorrect_metadata)} files with metadata issues")
        
        return correct_metadata, incorrect_metadata
    except Exception as e:
        logger.error(f"Error verifying metadata in SharePoint: {str(e)}")
        raise


def generate_report(uploaded_files, verified_files, missing_files, correct_metadata, incorrect_metadata):
    """
    Generate a report on the transfer results.
    
    Args:
        uploaded_files (list): List of uploaded file information dictionaries
        verified_files (list): List of verified file information dictionaries
        missing_files (list): List of missing file information dictionaries
        correct_metadata (list): List of files with correct metadata
        incorrect_metadata (list): List of files with metadata issues
        
    Returns:
        str: Path to report file
    """
    try:
        # Create report filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"transfer_report_{timestamp}.txt"
        report_path = os.path.join(REPORTS_DIR, report_filename)
        
        # Generate report content
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=== Отчет о переносе фотографий в SharePoint ===\n\n")
            f.write(f"Дата и время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("=== Общая статистика ===\n")
            f.write(f"Всего загружено файлов: {len(uploaded_files)}\n")
            f.write(f"Подтверждено в SharePoint: {len(verified_files)}\n")
            f.write(f"Отсутствует в SharePoint: {len(missing_files)}\n")
            f.write(f"Корректные метаданные: {len(correct_metadata)}\n")
            f.write(f"Проблемы с метаданными: {len(incorrect_metadata)}\n\n")
            
            # List verified files
            f.write("=== Успешно перенесенные файлы ===\n")
            for file_info in correct_metadata:
                f.write(f"- {file_info['name']}\n")
            f.write("\n")
            
            # List missing files
            if missing_files:
                f.write("=== Отсутствующие файлы ===\n")
                for file_info in missing_files:
                    f.write(f"- {file_info['name']}\n")
                f.write("\n")
            
            # List metadata issues
            if incorrect_metadata:
                f.write("=== Файлы с проблемами метаданных ===\n")
                for file_info in incorrect_metadata:
                    f.write(f"Файл: {file_info['name']}\n")
                    for issue in file_info.get('metadata_issues', []):
                        f.write(f"  - Поле: {issue['field']}\n")
                        f.write(f"    Локальное значение: {issue['local_value']}\n")
                        f.write(f"    Значение в SharePoint: {issue['sharepoint_value']}\n")
                    f.write("\n")
            
            f.write("=== Конец отчета ===\n")
        
        logger.info(f"Generated report: {report_path}")
        return report_path
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise


def generate_summary_json(uploaded_files, verified_files, missing_files, correct_metadata, incorrect_metadata):
    """
    Generate a JSON summary of the transfer results.
    
    Args:
        uploaded_files (list): List of uploaded file information dictionaries
        verified_files (list): List of verified file information dictionaries
        missing_files (list): List of missing file information dictionaries
        correct_metadata (list): List of files with correct metadata
        incorrect_metadata (list): List of files with metadata issues
        
    Returns:
        str: Path to JSON file
    """
    try:
        # Create summary filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"transfer_summary_{timestamp}.json"
        summary_path = os.path.join(REPORTS_DIR, summary_filename)
        
        # Generate summary content
        summary = {
            'timestamp': datetime.datetime.now().isoformat(),
            'statistics': {
                'total_uploaded': len(uploaded_files),
                'verified_in_sharepoint': len(verified_files),
                'missing_in_sharepoint': len(missing_files),
                'correct_metadata': len(correct_metadata),
                'incorrect_metadata': len(incorrect_metadata)
            },
            'successful_files': [file_info['name'] for file_info in correct_metadata],
            'missing_files': [file_info['name'] for file_info in missing_files],
            'metadata_issues': [{
                'filename': file_info['name'],
                'issues': file_info.get('metadata_issues', [])
            } for file_info in incorrect_metadata]
        }
        
        # Save summary to JSON file
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Generated summary JSON: {summary_path}")
        return summary_path
    except Exception as e:
        logger.error(f"Error generating summary JSON: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        # Get uploaded files
        uploaded_files = get_uploaded_files()
        
        if uploaded_files:
            print(f"\nFound {len(uploaded_files)} uploaded files")
            
            # Get SharePoint context
            ctx = get_sharepoint_context()
            
            # Get target library
            target_library = get_library(ctx, TARGET_LIBRARY_TITLE)
            if not target_library:
                logger.error(f"Target library not found: {TARGET_LIBRARY_TITLE}")
                exit(1)
            
            # Verify files in SharePoint
            verified_files, missing_files = verify_files_in_sharepoint(ctx, target_library, uploaded_files)
            
            # Verify metadata
            correct_metadata, incorrect_metadata = verify_metadata_in_sharepoint(verified_files)
            
            # Generate report
            report_path = generate_report(uploaded_files, verified_files, missing_files, correct_metadata, incorrect_metadata)
            
            # Generate summary JSON
            summary_path = generate_summary_json(uploaded_files, verified_files, missing_files, correct_metadata, incorrect_metadata)
            
            # Print summary
            print("\n=== Результаты переноса ===")
            print(f"Всего загружено файлов: {len(uploaded_files)}")
            print(f"Подтверждено в SharePoint: {len(verified_files)}")
            print(f"Отсутствует в SharePoint: {len(missing_files)}")
            print(f"Корректные метаданные: {len(correct_metadata)}")
            print(f"Проблемы с метаданными: {len(incorrect_metadata)}")
            
            print(f"\nОтчет сохранен в: {report_path}")
            print(f"JSON-сводка сохранена в: {summary_path}")
        else:
            print("Не найдено загруженных файлов. Сначала запустите sharepoint_uploader.py.")
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        print(f"Error: {str(e)}")
