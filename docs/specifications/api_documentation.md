# Agent API Documentation

## 1. Introduction

This document provides API documentation for the Agent system, which automates the transfer of photos between SharePoint libraries with AI-powered metadata enrichment. These APIs enable programmatic interaction with the system's core functionality.

### 1.1 Purpose

This API documentation aims to:
- Define interfaces for interacting with the Agent system
- Provide examples of API usage
- Document parameters, responses, and error handling
- Support integration with other systems

### 1.2 Audience

This documentation is intended for:
- Developers integrating with the Agent system
- System administrators automating workflows
- Technical staff maintaining the system
- API users who need to understand available endpoints

### 1.3 API Overview

The Agent API is structured around these core functionalities:
- SharePoint connectivity and authentication
- Photo management (download, upload, metadata)
- AI analysis integration
- Process management and monitoring
- Reporting and verification

## 2. Authentication

### 2.1 SharePoint Authentication

#### 2.1.1 `authenticate_sharepoint()`

Authenticates with SharePoint and returns a context object.

**Parameters:**
- `site_url` (str): SharePoint site URL
- `username` (str): SharePoint username/email
- `password` (str): SharePoint password
- `timeout` (int, optional): Connection timeout in seconds. Default: 30

**Returns:**
- `context` (object): SharePoint ClientContext object

**Example:**
```python
from utils.sharepoint_auth import authenticate_sharepoint

# Authenticate with SharePoint
context = authenticate_sharepoint(
    site_url="https://company.sharepoint.com/sites/your-site",
    username="user@company.com",
    password="your-password"
)

# Use the context for SharePoint operations
print(f"Authenticated as: {context.user.login_name}")
```

**Errors:**
- `SharePointAuthenticationError`: Authentication failed
- `SharePointConnectionError`: Cannot connect to SharePoint
- `TimeoutError`: Connection timed out

### 2.2 OpenAI Authentication

#### 2.2.1 `initialize_openai()`

Initializes the OpenAI client with the provided API key.

**Parameters:**
- `api_key` (str): OpenAI API key
- `organization` (str, optional): OpenAI organization ID. Default: None

**Returns:**
- `client` (object): Initialized OpenAI client

**Example:**
```python
from utils.api import initialize_openai

# Initialize OpenAI client
client = initialize_openai(
    api_key="your-openai-api-key"
)

# Use the client for OpenAI operations
print("OpenAI client initialized successfully")
```

**Errors:**
- `OpenAIAuthenticationError`: Invalid API key
- `OpenAIConfigurationError`: Configuration error

## 3. SharePoint Operations

### 3.1 Library Management

#### 3.1.1 `get_library()`

Retrieves a SharePoint library by name.

**Parameters:**
- `context` (object): SharePoint context
- `library_name` (str): Name of the library

**Returns:**
- `library` (object): SharePoint library object

**Example:**
```python
from utils.sharepoint_auth import authenticate_sharepoint
from utils.sharepoint import get_library

# Get SharePoint context
context = authenticate_sharepoint(site_url, username, password)

# Get library
library = get_library(context, "PhotoLibrary")
print(f"Found library: {library.properties['Title']}")
```

#### 3.1.2 `get_metadata_schema()`

Retrieves the metadata schema for a SharePoint library.

**Parameters:**
- `context` (object): SharePoint context
- `library_name` (str): Name of the library

**Returns:**
- `schema` (dict): Metadata schema dictionary

**Example:**
```python
from utils.sharepoint import get_metadata_schema

# Get metadata schema
schema = get_metadata_schema(context, "PhotoLibrary")
print(f"Found {len(schema['fields'])} metadata fields")
```

### 3.2 Photo Operations

#### 3.2.1 `list_photos()`

Lists photos in a SharePoint library.

**Parameters:**
- `context` (object): SharePoint context
- `library_name` (str): Name of the library
- `folder_path` (str, optional): Folder path within library. Default: ""
- `file_extension` (list, optional): List of file extensions to filter. Default: [".jpg", ".jpeg", ".png"]

**Returns:**
- `photos` (list): List of photo objects

**Example:**
```python
from utils.sharepoint import list_photos

# List photos
photos = list_photos(context, "PhotoLibrary", folder_path="Construction/2023")
print(f"Found {len(photos)} photos")
```

#### 3.2.2 `download_photo()`

Downloads a photo from SharePoint.

**Parameters:**
- `context` (object): SharePoint context
- `photo` (object): SharePoint photo object
- `target_path` (str): Local path to save the photo

**Returns:**
- `filepath` (str): Path to the downloaded file

**Example:**
```python
from utils.sharepoint import download_photo

# Download a photo
filepath = download_photo(context, photo, "data/downloads/photo.jpg")
print(f"Downloaded to: {filepath}")
```

#### 3.2.3 `upload_photo()`

Uploads a photo to SharePoint.

**Parameters:**
- `context` (object): SharePoint context
- `library_name` (str): Name of the library
- `filepath` (str): Local path to the photo
- `target_filename` (str): Filename to use in SharePoint
- `folder_path` (str, optional): Folder path within library. Default: ""
- `metadata` (dict, optional): Metadata to apply. Default: None

**Returns:**
- `file_info` (dict): Information about the uploaded file

**Example:**
```python
from utils.sharepoint import upload_photo

# Upload a photo with metadata
metadata = {
    "Title": "Modern Wooden House",
    "Projektkategorie": "Wohnbaute",
    "Material": ["Holz", "Glas"]
}

file_info = upload_photo(
    context, 
    "TargetLibrary", 
    "data/uploads/photo.jpg", 
    "Company_Referenzfoto_001.jpg",
    metadata=metadata
)
print(f"Uploaded: {file_info['Name']}")
```

**Errors:**
- `SharePointUploadError`: Upload failed
- `MetadataValidationError`: Invalid metadata
- `FileNotFoundError`: Local file not found
- `PermissionError`: Insufficient permissions

#### 3.2.4 `apply_metadata()`

Applies metadata to an existing SharePoint file.

**Parameters:**
- `context` (object): SharePoint context
- `file_info` (dict): File information dictionary
- `metadata` (dict): Metadata to apply

**Returns:**
- `success` (bool): True if successful

**Example:**
```python
from utils.sharepoint import apply_metadata

# Apply metadata to an existing file
metadata = {
    "Material": ["Holz", "Glas"],
    "Holzart": ["Lärche"]
}

success = apply_metadata(context, file_info, metadata)
if success:
    print("Metadata applied successfully")
```

## 4. Metadata Operations

### 4.1 EXIF Extraction

#### 4.1.1 `extract_exif_metadata()`

Extracts EXIF metadata from a photo.

**Parameters:**
- `filepath` (str): Path to the photo file

**Returns:**
- `metadata` (dict): Extracted EXIF metadata

**Example:**
```python
from utils.metadata import extract_exif_metadata

# Extract EXIF metadata
exif_data = extract_exif_metadata("data/downloads/photo.jpg")
print(f"Camera model: {exif_data.get('Model', 'Unknown')}")
print(f"Date taken: {exif_data.get('DateTimeOriginal', 'Unknown')}")
```

#### 4.1.2 `save_metadata_to_json()`

Saves metadata to a JSON file.

**Parameters:**
- `metadata` (dict): Metadata dictionary
- `filepath` (str): Path to save JSON file

**Returns:**
- `filepath` (str): Path to the saved file

**Example:**
```python
from utils.metadata import save_metadata_to_json

# Save metadata to JSON
json_path = save_metadata_to_json(exif_data, "data/metadata/photo_exif.json")
print(f"Metadata saved to: {json_path}")
```

### 4.2 Metadata Generation

#### 4.2.1 `generate_enriched_metadata()`

Generates enriched metadata by combining EXIF and AI analysis.

**Parameters:**
- `exif_metadata` (dict): EXIF metadata dictionary
- `ai_analysis` (dict): OpenAI analysis dictionary
- `schema` (dict): SharePoint schema dictionary

**Returns:**
- `metadata` (dict): Enriched metadata dictionary

**Example:**
```python
from utils.metadata import generate_enriched_metadata

# Generate enriched metadata
enriched_metadata = generate_enriched_metadata(
    exif_metadata=exif_data,
    ai_analysis=ai_results,
    schema=schema
)
print(f"Generated {len(enriched_metadata)} metadata fields")
```

#### 4.2.2 `validate_metadata()`

Validates metadata against a SharePoint schema.

**Parameters:**
- `metadata` (dict): Metadata dictionary
- `schema` (dict): SharePoint schema dictionary

**Returns:**
- `valid` (bool): True if valid
- `errors` (list): List of validation errors

**Example:**
```python
from utils.metadata import validate_metadata

# Validate metadata against schema
valid, errors = validate_metadata(enriched_metadata, schema)
if valid:
    print("Metadata is valid")
else:
    print("Validation errors:")
    for error in errors:
        print(f"- {error}")
```

## 5. OpenAI Integration

### 5.1 Photo Analysis

#### 5.1.1 `analyze_photo_with_openai()`

Analyzes a photo using OpenAI's GPT-4 Vision API.

**Parameters:**
- `filepath` (str): Path to the photo file
- `prompt` (str): Prompt for OpenAI
- `max_tokens` (int, optional): Maximum tokens for response. Default: 1000

**Returns:**
- `analysis` (dict): Analysis results

**Example:**
```python
from utils.openai_analyzer import analyze_photo_with_openai

# Prepare prompt
prompt = "Analyze this wooden construction photo and describe key elements..."

# Analyze photo
analysis = analyze_photo_with_openai(
    "data/downloads/photo.jpg",
    prompt,
    max_tokens=1500
)
print("Analysis complete")
```

#### 5.1.2 `prepare_openai_prompt()`

Prepares a prompt for OpenAI based on the metadata schema.

**Parameters:**
- `schema` (dict): SharePoint schema dictionary
- `role` (str, optional): Role instruction for AI. Default from config
- `instructions_pre` (str, optional): Instructions before schema. Default from config
- `instructions_post` (str, optional): Instructions after schema. Default from config

**Returns:**
- `prompt` (str): Formatted prompt for OpenAI

**Example:**
```python
from utils.openai_analyzer import prepare_openai_prompt

# Prepare OpenAI prompt with schema
prompt = prepare_openai_prompt(
    schema,
    role="Act as an expert in wooden construction..."
)
print(f"Prompt length: {len(prompt)} characters")
```

## 6. Process Management

### 6.1 Orchestration

#### 6.1.1 `run_complete_process()`

Runs the complete photo processing workflow.

**Parameters:**
- `config` (dict): Configuration dictionary
- `monitor` (bool, optional): Enable progress monitoring. Default: False

**Returns:**
- `results` (dict): Process results and statistics

**Example:**
```python
from auto_process import run_complete_process
from utils.config import get_config

# Get configuration
config = get_config()

# Run complete process
results = run_complete_process(config, monitor=True)
print(f"Processed {results['total']} photos")
print(f"Success rate: {results['success_rate']*100:.1f}%")
```

#### 6.1.2 `run_specific_step()`

Runs a specific step in the process.

**Parameters:**
- `step_name` (str): Name of the step to run
- `config` (dict): Configuration dictionary
- `input_data` (dict, optional): Input data for the step. Default: None

**Returns:**
- `results` (dict): Step results

**Example:**
```python
from auto_process import run_specific_step
from utils.config import get_config

# Get configuration
config = get_config()

# Run specific step
results = run_specific_step(
    "openai_analyzer",
    config,
    input_data={"photo_paths": ["data/downloads/photo1.jpg", "data/downloads/photo2.jpg"]}
)
print(f"Analyzed {len(results['analyzed_photos'])} photos")
```

### 6.2 Monitoring

#### 6.2.1 `get_process_status()`

Gets the status of a running or completed process.

**Parameters:**
- `process_id` (str): Process identifier

**Returns:**
- `status` (dict): Process status information

**Example:**
```python
from utils.monitoring import get_process_status

# Get process status
status = get_process_status("process_20230615_123045")
print(f"Process status: {status['status']}")
print(f"Progress: {status['progress']}%")
print(f"Completed steps: {', '.join(status['completed_steps'])}")
```

## 7. Reporting and Verification

### 7.1 Transfer Verification

#### 7.1.1 `verify_transfer()`

Verifies that photos were successfully transferred with correct metadata.

**Parameters:**
- `context` (object): SharePoint context
- `source_info` (dict): Source information
- `target_info` (dict): Target information

**Returns:**
- `verification` (dict): Verification results

**Example:**
```python
from utils.verification import verify_transfer

# Verify transfer
verification = verify_transfer(context, source_info, target_info)
print(f"Verified {verification['total']} transfers")
print(f"Successful: {verification['successful']}")
print(f"Failed: {verification['failed']}")
```

### 7.2 Report Generation

#### 7.2.1 `generate_report()`

Generates a report of the transfer process.

**Parameters:**
- `verification` (dict): Verification results
- `format` (str, optional): Report format ('html', 'csv', 'json'). Default: 'html'
- `output_path` (str, optional): Path to save report. Default: 'data/reports/'

**Returns:**
- `filepath` (str): Path to the generated report

**Example:**
```python
from utils.reporting import generate_report

# Generate HTML report
report_path = generate_report(
    verification,
    format='html',
    output_path='data/reports/'
)
print(f"Report generated: {report_path}")
```

## 8. Utility Functions

### 8.1 Configuration Management

#### 8.1.1 `get_config()`

Gets the configuration from environment variables and config files.

**Parameters:**
- `config_path` (str, optional): Path to config file. Default: 'config/config.env'

**Returns:**
- `config` (object): Configuration object

**Example:**
```python
from utils.config import get_config

# Get configuration
config = get_config()
print(f"SharePoint URL: {config.sharepoint.site_url}")
print(f"Source library: {config.sharepoint.source_library}")
```

### 8.2 Path Management

#### 8.2.1 `get_path_manager()`

Gets a path manager for working with project directories.

**Parameters:**
- `base_dir` (str, optional): Base directory. Default: project root

**Returns:**
- `path_manager` (object): Path manager object

**Example:**
```python
from utils.paths import get_path_manager

# Get path manager
path_manager = get_path_manager()

# Use path manager
downloads_dir = path_manager.downloads_dir
metadata_dir = path_manager.metadata_dir
print(f"Downloads directory: {downloads_dir}")
```

### 8.3 Error Handling

#### 8.3.1 `handle_exceptions()`

Decorator for handling exceptions in functions.

**Usage:**
```python
from utils import handle_exceptions

@handle_exceptions
def my_function():
    # Function code that might raise exceptions
    pass
```

#### 8.3.2 `retry()`

Decorator for retrying functions on failure.

**Parameters:**
- `max_attempts` (int, optional): Maximum retry attempts. Default: 3
- `retry_delay` (int, optional): Delay between retries in seconds. Default: 1
- `backoff_factor` (float, optional): Exponential backoff factor. Default: 2.0

**Usage:**
```python
from utils import retry

@retry(max_attempts=5, retry_delay=2)
def my_function():
    # Function code that might fail temporarily
    pass
```

## 9. Error Codes and Exceptions

| Exception | Error Code | Description |
|-----------|------------|-------------|
| `SharePointAuthenticationError` | SP001 | SharePoint authentication failed |
| `SharePointConnectionError` | SP002 | Cannot connect to SharePoint |
| `SharePointLibraryError` | SP003 | Library not found or inaccessible |
| `SharePointUploadError` | SP004 | Failed to upload file to SharePoint |
| `OpenAIAuthenticationError` | AI001 | OpenAI API authentication failed |
| `OpenAIRequestError` | AI002 | Error in OpenAI API request |
| `OpenAIResponseError` | AI003 | Error in OpenAI API response |
| `MetadataExtractionError` | MD001 | Failed to extract metadata |
| `MetadataValidationError` | MD002 | Metadata validation failed |
| `ConfigurationError` | CFG001 | Configuration error |
| `FileOperationError` | IO001 | File operation failed |

## 10. API Limitations

### 10.1 Rate Limiting

- **SharePoint API**: Limited by tenant settings (typically 600 requests/minute)
- **OpenAI API**: Rate limited based on API plan (typically 10,000 tokens/minute)

### 10.2 Performance Considerations

- Large photo collections should be processed in batches
- Concurrent API calls should be limited (OpenAI concurrency limit: 5 by default)
- Allow sufficient time for API responses (timeout settings configurable)

### 10.3 Security Constraints

- API credentials should be stored securely
- SharePoint permissions must be appropriate for operations
- OpenAI API key should have usage limits configured

## 11. API Versioning

The API version is indicated in the module imports. Current version: 1.0.0

### 11.1 Version History

| Version | Release Date | Changes |
|---------|--------------|---------|
| 1.0.0 | 2023-06-01 | Initial release |
| 0.9.0 | 2023-05-15 | Beta release |
| 0.8.0 | 2023-04-20 | Alpha release |

### 11.2 Deprecation Policy

- APIs will be supported for at least 12 months after deprecation notice
- Deprecated methods will raise warnings but continue to function
- Breaking changes will only occur in major version updates

## 12. Appendices

### 12.1 Sample Code

Complete sample for downloading, analyzing, and uploading a photo:

```python
from utils.sharepoint_auth import authenticate_sharepoint
from utils.sharepoint import get_library, download_photo, upload_photo
from utils.metadata import extract_exif_metadata
from utils.openai_analyzer import analyze_photo_with_openai, prepare_openai_prompt
from utils.metadata import generate_enriched_metadata
from utils.config import get_config

# Get configuration
config = get_config()

# Authenticate with SharePoint
context = authenticate_sharepoint(
    config.sharepoint.site_url,
    config.sharepoint.username,
    config.sharepoint.password
)

# Get source library
source_library = get_library(context, config.sharepoint.source_library)

# Download a photo
photo = source_library.items[0]  # Get first photo
filepath = download_photo(context, photo, "data/downloads/photo.jpg")

# Extract EXIF metadata
exif_data = extract_exif_metadata(filepath)

# Prepare OpenAI prompt
prompt = prepare_openai_prompt(schema)

# Analyze photo with OpenAI
analysis = analyze_photo_with_openai(filepath, prompt)

# Generate enriched metadata
enriched_metadata = generate_enriched_metadata(exif_data, analysis, schema)

# Upload photo with metadata
file_info = upload_photo(
    context,
    config.sharepoint.target_library,
    filepath,
    "Company_Referenzfoto_001.jpg",
    metadata=enriched_metadata
)

print(f"Photo processed and uploaded: {file_info['Name']}")
```

### 12.2 Data Schemas

#### 12.2.1 Metadata Schema

```json
{
  "library_title": "TargetLibrary",
  "fields": [
    {
      "internal_name": "Title",
      "title": "Titel",
      "type": "Text",
      "required": false
    },
    {
      "internal_name": "Projektkategorie",
      "title": "Projektkategorie",
      "type": "Choice",
      "required": false,
      "choices": [
        "Landwirtschaft",
        "Wohnbaute",
        "Industrie / Gewerbe",
        "Umbau / Sanierung",
        "Aufstockung / Erweiterung"
      ]
    }
  ]
}
```

#### 12.2.2 EXIF Metadata

```json
{
  "Make": "Canon",
  "Model": "Canon EOS 5D Mark IV",
  "DateTimeOriginal": "2023:05:10 14:30:45",
  "ExposureTime": "1/125",
  "FNumber": "8.0",
  "ISOSpeedRatings": "100",
  "FocalLength": "24mm",
  "GPSLatitude": "47.379287",
  "GPSLongitude": "8.534691"
}
```

#### 12.2.3 OpenAI Analysis

```json
{
  "Titel": "Modernes Holzhaus mit vertikaler Fassade",
  "Projektkategorie": "Wohnbaute",
  "Material": ["Holz", "Glas"],
  "Holzart": ["Lärche"],
  "Beschreibung": "Ein modernes Wohnhaus mit vertikaler Holzfassade und großen Fenstern.",
  "Ansicht": "Aussenaufnahme",
  "Sparte / Kategorie": ["Holzbau"],
  "Fassade": ["Holzfassade vertikal"],
  "Bauteil": ["Fenster", "Fassade"],
  "Status": "Entwurf KI"
}
```
