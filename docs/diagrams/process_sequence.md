# Диаграмма последовательности процессов Agent

[//]: # (Диаграмма последовательности процессов)

```mermaid
sequenceDiagram
    participant User
    participant AutoProcess as auto_process.py
    participant MetadataSchema as metadata_schema.py
    participant PhotoMetadata as photo_metadata.py
    participant OpenAIAnalyzer as openai_analyzer.py
    participant MetadataGenerator as metadata_generator.py
    participant SPUploader as sharepoint_uploader.py
    participant Verification as transfer_verification.py
    participant SharePoint
    participant OpenAI
    
    User->>AutoProcess: Start automatic processing
    AutoProcess->>MetadataSchema: Extract metadata schema
    MetadataSchema->>SharePoint: Request schema structure
    SharePoint-->>MetadataSchema: Return schema JSON
    MetadataSchema-->>AutoProcess: Schema extracted
    
    AutoProcess->>PhotoMetadata: Download photos from source
    PhotoMetadata->>SharePoint: Request photos from source library
    SharePoint-->>PhotoMetadata: Return photos
    PhotoMetadata->>PhotoMetadata: Extract EXIF metadata
    PhotoMetadata-->>AutoProcess: Photos downloaded & metadata extracted
    
    AutoProcess->>OpenAIAnalyzer: Analyze photos with AI
    OpenAIAnalyzer->>OpenAI: Send photos for analysis
    OpenAI-->>OpenAIAnalyzer: Return AI-generated metadata
    OpenAIAnalyzer-->>AutoProcess: Photos analyzed
    
    AutoProcess->>MetadataGenerator: Generate enriched metadata
    MetadataGenerator->>MetadataGenerator: Combine EXIF & AI metadata
    MetadataGenerator-->>AutoProcess: Metadata generated
    
    AutoProcess->>SPUploader: Upload photos to target
    SPUploader->>SharePoint: Upload photos with metadata
    SharePoint-->>SPUploader: Confirm upload
    SPUploader-->>AutoProcess: Photos uploaded
    
    AutoProcess->>Verification: Verify transfer
    Verification->>SharePoint: Verify uploaded files
    SharePoint-->>Verification: Verification data
    Verification->>Verification: Generate verification report
    Verification-->>AutoProcess: Transfer verified
    AutoProcess-->>User: Process completed
```

Эта диаграмма показывает последовательность взаимодействия между различными компонентами системы Agent при выполнении полного процесса обработки фотографий.
