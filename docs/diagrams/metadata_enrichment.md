# Процесс обогащения метаданных

[//]: # (Диаграмма процесса обогащения метаданных)

```mermaid
flowchart TD
    Start([Start Metadata Generation]) --> LoadSchema[Load Metadata Schema]
    LoadSchema --> FindPhotos[Find Photos for Processing]
    
    FindPhotos --> CheckFound{Photos Found?}
    CheckFound -->|No| End([End Process])
    CheckFound -->|Yes| Process[Process Photos]
    
    subgraph "Metadata Processing"
        Process --> |For Each Photo| LoadEXIF[Load EXIF Metadata]
        LoadEXIF --> LoadAI[Load AI Analysis Results]
        
        LoadAI --> CheckAI{AI Analysis Exists?}
        CheckAI -->|No| SkipPhoto[Skip Photo and Log Error]
        CheckAI -->|Yes| CombineData[Combine EXIF and AI Data]
        
        CombineData --> ApplyRules[Apply Business Rules]
        ApplyRules --> ValidateMetadata[Validate Against Schema]
        
        ValidateMetadata --> CheckValid{Metadata Valid?}
        CheckValid -->|No| FixMetadata[Fix Metadata Issues]
        FixMetadata --> ValidateMetadata
        
        CheckValid -->|Yes| FormatMetadata[Format for SharePoint]
        FormatMetadata --> SaveMetadata[Save Metadata JSON]
    end
    
    SaveMetadata --> PrepareUpload[Prepare for Upload]
    PrepareUpload --> End
    
    SkipPhoto --> CheckMorePhotos{More Photos?}
    CheckMorePhotos -->|Yes| Process
    CheckMorePhotos -->|No| End
    
    classDef process fill:#e8eaf6,stroke:#3949ab,stroke-width:1px;
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:1px;
    classDef terminator fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;
    
    class LoadSchema,FindPhotos,Process,LoadEXIF,LoadAI,CombineData,ApplyRules,ValidateMetadata,FixMetadata,FormatMetadata,SaveMetadata,PrepareUpload,SkipPhoto process;
    class CheckFound,CheckAI,CheckValid,CheckMorePhotos decision;
    class Start,End terminator;
```

Эта диаграмма показывает процесс обогащения метаданных, объединяя данные EXIF и результаты анализа OpenAI для создания полного набора метаданных для SharePoint.
