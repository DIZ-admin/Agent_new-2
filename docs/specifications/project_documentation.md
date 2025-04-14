# Agent Project Documentation

## 1. Project Overview

Agent is an automated system for transferring photos between SharePoint libraries while enriching their metadata using artificial intelligence. The system is designed to streamline the workflow for managing reference photos, particularly focusing on construction and architectural photography for wooden buildings.

### 1.1 Core Functionalities

- **Automated Transfer:** Moves photos from a source SharePoint library to a destination library
- **Metadata Extraction:** Extracts EXIF data and other metadata from photos
- **AI-Powered Analysis:** Uses OpenAI's GPT-4 Vision to analyze photos and generate relevant metadata
- **Metadata Enrichment:** Combines EXIF data with AI analysis to create comprehensive metadata
- **SharePoint Integration:** Uploads photos with enhanced metadata to the target SharePoint library
- **Verification:** Validates successful transfers and generates reports

### 1.2 Target Audience

- Construction companies and architectural firms using SharePoint for photo management
- Wooden construction specialists who need to organize reference photos
- Marketing departments that need labeled and categorized construction photos

## 2. System Architecture

### 2.1 High-Level Architecture

The system follows a modular pipeline architecture with distinct processing stages:

1. **Configuration & Setup:** Configuration loading and SharePoint authentication
2. **Data Acquisition:** Photo downloading and metadata schema extraction
3. **Analysis & Processing:** AI analysis and metadata generation
4. **Output & Verification:** Photo uploading and transfer verification

### 2.2 Key Components

- **auto_process.py:** Main orchestration script that runs all components in sequence
- **metadata_schema.py:** Extracts metadata schema from SharePoint
- **photo_metadata.py:** Downloads photos and extracts EXIF metadata
- **openai_analyzer.py:** Analyzes photos using OpenAI's GPT-4 Vision API
- **metadata_generator.py:** Combines EXIF and AI-generated metadata
- **sharepoint_uploader.py:** Uploads photos with metadata to SharePoint
- **transfer_verification.py:** Verifies successful transfers

### 2.3 Data Flow

1. Photos are downloaded from the source SharePoint library
2. EXIF metadata is extracted from the photos
3. Photos are analyzed by OpenAI's GPT-4 Vision API
4. EXIF metadata and AI analysis are combined
5. Photos with enriched metadata are uploaded to the target SharePoint library
6. The transfer is verified and a report is generated

## 3. Technical Specifications

### 3.1 Dependencies

- **Python:** 3.8 or higher
- **Office365-REST-Python-Client:** For SharePoint integration
- **Pillow:** For image processing and EXIF extraction
- **OpenAI API:** For AI-powered photo analysis
- **python-dotenv:** For configuration management
- **tqdm:** For progress reporting

### 3.2 Configuration

Configuration is managed through:
- **config.env:** Environment variables for authentication, endpoints, and settings
- **sharepoint_choices.json:** Metadata schema definition for the target SharePoint library

### 3.3 Data Storage

- **downloads/:** Downloaded photos from source SharePoint library
- **metadata/:** Extracted EXIF metadata stored as JSON files
- **analysis/:** OpenAI analysis results stored as JSON files
- **upload/:** Photos prepared for upload with enriched metadata
- **uploaded/:** Successfully uploaded photos
- **reports/:** Transfer verification reports

## 4. AI Integration

### 4.1 OpenAI API Usage

The system uses OpenAI's GPT-4 Vision API to analyze photographs and extract relevant metadata.

### 4.2 Prompt Engineering

The prompt instructs the AI to:
- Act as an expert in wooden house construction
- Analyze the visual content of the image
- Pay special attention to details relevant for wooden construction
- Follow the specified metadata schema structure
- Provide all field values in German
- Return only valid JSON with no additional explanations

### 4.3 Metadata Enrichment Process

1. Photos are encoded to base64 and resized if necessary
2. The OpenAI API is called with the prepared prompt
3. The API response is parsed into a structured JSON format
4. The AI-generated metadata is combined with the EXIF metadata
5. The enriched metadata is validated against the SharePoint schema

## 5. SharePoint Integration

### 5.1 Authentication

The system authenticates with SharePoint using username and password credentials.

### 5.2 Photo Management

- Photos are downloaded from the source library
- Photos are uploaded to the target library with a standardized naming convention
- Metadata is applied to uploaded photos according to the target library's schema

### 5.3 Metadata Schema

The system extracts the metadata schema from the target SharePoint library and ensures all required fields are populated correctly.

## 6. Web Interface

A simple web interface is provided for monitoring and controlling the process:

- View transfer status and progress
- Inspect metadata analysis results
- Configure system settings
- Generate and view reports

## 7. Security Considerations

- SharePoint credentials and OpenAI API keys are stored in the configuration file
- Access to the configuration file should be restricted
- The system does not expose APIs or services to external networks

## 8. Deployment Guide

### 8.1 Prerequisites

- Python 3.8 or higher
- SharePoint access with appropriate permissions
- OpenAI API key with GPT-4 Vision access

### 8.2 Installation Steps

1. Clone the repository
2. Install dependencies using `pip install -r requirements.txt`
3. Configure the application by editing `config/config.env`
4. Create necessary directories if they don't exist

### 8.3 Running the System

- Run the complete process: `python src/auto_process.py`
- Run individual steps as needed (see command reference)

## 9. Command Reference

### 9.1 Main Process

```
python src/auto_process.py
```

### 9.2 Individual Steps

```
python src/metadata_schema.py    # Extract metadata schema
python src/photo_metadata.py     # Download photos and extract metadata
python src/openai_analyzer.py    # Analyze photos with OpenAI
python src/metadata_generator.py # Generate enriched metadata
python src/sharepoint_uploader.py # Upload photos to SharePoint
python src/transfer_verification.py # Verify the transfer
```

## 10. Troubleshooting

### 10.1 Common Issues

- **Authentication Failures:** Check SharePoint credentials
- **API Rate Limiting:** Adjust concurrent API calls in configuration
- **Metadata Validation Errors:** Check for changes in SharePoint schema
- **Failed Photo Analysis:** Check image format and size limitations

### 10.2 Logging

- Log files are stored in the `logs/` directory
- Each component creates timestamped log files
- Log level can be configured in the configuration file

## 11. Future Enhancements

- **Improved AI Analysis:** Fine-tuning the AI model for better wooden construction analysis
- **Batch Processing:** Enhanced batch processing for large photo collections
- **User Interface:** More comprehensive web interface for management
- **Automatic Scheduling:** Periodic execution of the transfer process
