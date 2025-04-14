# Интеграция веб-интерфейса

[//]: # (Диаграмма интеграции веб-интерфейса с компонентами Agent)

```mermaid
graph TD
    subgraph "Web Interface"
        HomePage["Home Page"]
        AnalysisPage["Analysis Page"]
        SettingsPage["Settings Page"]
        ReportsPage["Reports Page"]
        
        PageClient["page.client.tsx"]
        ProgressBar["AnalysisProgressBar.tsx"]
        ResultsTable["AnalysisResultsTable.tsx"]
        ResultModal["AnalysisResultModal.tsx"]
        SettingsPanel["AnalysisSettingsPanel.tsx"]
        PhotoCard["PhotoAnalysisCard.tsx"]
        MetadataEditor["MetadataEditor.tsx"]
        
        HomePage --> PageClient
        AnalysisPage --> PageClient
        SettingsPage --> SettingsPanel
        ReportsPage --> ResultsTable
        
        PageClient --> ProgressBar
        PageClient --> PhotoCard
        PhotoCard --> ResultModal
        ResultModal --> MetadataEditor
    end
    
    subgraph "Services"
        SharePointService["sharepoint.ts"]
        OpenAIService["openai.ts"]
        ReportsService["reports.ts"]
    end
    
    subgraph "Agent Backend"
        AutoProcess["auto_process.py"]
        
        subgraph "Core Modules"
            MetadataSchema["metadata_schema.py"]
            PhotoMetadata["photo_metadata.py"]
            OpenAIAnalyzer["openai_analyzer.py"]
            MetadataGen["metadata_generator.py"]
            SPUploader["sharepoint_uploader.py"]
            Verification["transfer_verification.py"]
        end
        
        subgraph "Data Storage"
            Downloads["downloads/"]
            Metadata["metadata/"]
            Analysis["analysis/"]
            Upload["upload/"]
            Reports["reports/"]
        end
        
        AutoProcess --> MetadataSchema
        AutoProcess --> PhotoMetadata
        AutoProcess --> OpenAIAnalyzer
        AutoProcess --> MetadataGen
        AutoProcess --> SPUploader
        AutoProcess --> Verification
        
        MetadataSchema --> Metadata
        PhotoMetadata --> Downloads
        OpenAIAnalyzer --> Analysis
        MetadataGen --> Upload
        Verification --> Reports
    end
    
    SharePointService <--> |API| SPUploader
    SharePointService <--> |API| PhotoMetadata
    SharePointService <--> |API| MetadataSchema
    OpenAIService <--> |API| OpenAIAnalyzer
    ReportsService <--> |API| Reports
    
    PageClient <--> SharePointService
    PageClient <--> OpenAIService
    ResultsTable <--> ReportsService
    SettingsPanel <--> SharePointService
    MetadataEditor <--> SharePointService
    
    PhotoCard <--> Downloads
    ResultModal <--> Analysis
    MetadataEditor <--> Metadata
    ProgressBar <--> AutoProcess
    
    classDef webComponents fill:#ffecb3,stroke:#ff6f00,stroke-width:1px
    classDef services fill:#e1bee7,stroke:#8e24aa,stroke-width:1px
    classDef coreModules fill:#c8e6c9,stroke:#388e3c,stroke-width:1px
    classDef dataStorage fill:#bbdefb,stroke:#1976d2,stroke-width:1px
    classDef pages fill:#ffcdd2,stroke:#d32f2f,stroke-width:1px
    
    class PhotoCard,ProgressBar,ResultsTable,ResultModal,SettingsPanel,MetadataEditor,PageClient webComponents
    class SharePointService,OpenAIService,ReportsService services
    class MetadataSchema,PhotoMetadata,OpenAIAnalyzer,MetadataGen,SPUploader,Verification,AutoProcess coreModules
    class Downloads,Metadata,Analysis,Upload,Reports dataStorage
    class HomePage,AnalysisPage,SettingsPage,ReportsPage pages
```

Эта диаграмма показывает интеграцию веб-интерфейса с основными компонентами системы Agent, включая взаимодействие между фронтендом и бэкендом.
