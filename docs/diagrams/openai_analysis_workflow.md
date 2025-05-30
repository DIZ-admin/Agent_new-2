# Рабочий процесс анализа OpenAI

[//]: # (Детальная диаграмма процесса анализа OpenAI)

```mermaid
flowchart TD
    Start([Start Analysis]) --> LoadSchema[Load Metadata Schema]
    LoadSchema --> InitRateLimiter[Initialize OpenAI Rate Limiter]
    InitRateLimiter --> LoadTokenStats[Load Token Usage Statistics]
    LoadTokenStats --> PreparePrompt[Prepare OpenAI Prompt]
    PreparePrompt --> FindPhotos[Find Photos for Analysis]

    FindPhotos --> CheckEmpty{Photos Found?}
    CheckEmpty -->|No| SaveTokenStats[Save Token Usage Statistics]
    SaveTokenStats --> End([End Process])
    CheckEmpty -->|Yes| BatchProcess[Process Photos in Batches]

    subgraph "Batch Processing"
        BatchProcess --> ProcessBatch[Process Photo Batch]
        ProcessBatch --> ProcessPhoto[Process Individual Photo]

        subgraph "Photo Processing"
            ProcessPhoto --> EncodeImage[Encode Image to Base64]
            EncodeImage --> EstimateTokens[Estimate Token Usage]
            EstimateTokens --> CallOpenAI[Call OpenAI API]
            CallOpenAI --> UpdateTokenStats[Update Token Usage Statistics]
            UpdateTokenStats --> ParseJSON[Parse JSON Response]
            ParseJSON --> CheckSuccess{JSON Parsing Success?}
            CheckSuccess -->|Yes| SaveAnalysis[Save Analysis to JSON]
            CheckSuccess -->|No| AddToRetry[Add to Retry Queue]
            SaveAnalysis --> UpdatePhotoInfo[Update Photo Info]
        end

        ProcessBatch --> CheckMoreBatches{More Batches?}
        CheckMoreBatches -->|Yes| ProcessBatch
        CheckMoreBatches -->|No| ProcessRetries[Process Retry Queue]

        ProcessRetries --> RetryEmpty{Retry Queue Empty?}
        RetryEmpty -->|No| RetryPhoto[Retry Failed Photo]
        RetryPhoto --> ProcessPhoto
        RetryEmpty -->|Yes| CompleteProcess[Complete Process]
    end

    CompleteProcess --> GenerateSummary[Generate Summary]
    GenerateSummary --> SaveFinalStats[Save Final Token Usage Statistics]
    SaveFinalStats --> End

    class LoadSchema,PreparePrompt,FindPhotos,BatchProcess,ProcessBatch,EncodeImage,CallOpenAI,ParseJSON,SaveAnalysis,UpdatePhotoInfo,ProcessRetries,RetryPhoto,GenerateSummary,InitRateLimiter,LoadTokenStats,EstimateTokens,UpdateTokenStats,SaveTokenStats,SaveFinalStats functionCall;
    class CheckEmpty,CheckSuccess,CheckMoreBatches,RetryEmpty condition;
    class Start,End terminator;

    classDef functionCall fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;
    classDef condition fill:#fff9c4,stroke:#fbc02d,stroke-width:1px;
    classDef terminator fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;
```

Эта диаграмма детально показывает процесс анализа фотографий с использованием OpenAI API, включая обработку ошибок, повторные попытки и отслеживание использования токенов. Система теперь отслеживает использование токенов OpenAI API и сохраняет статистику в файл `logs/token_usage_stats.json`, что позволяет отслеживать использование токенов даже при запуске скриптов в разных процессах.
