# Архитектура системы Agent

[//]: # (Диаграмма архитектуры системы)

```mermaid
flowchart TD
    subgraph "Sources"
        SP1[SharePoint Source Library] --> |Download Photos| A1[Photo Download]
    end
    
    subgraph "Data Processing"
        A1 --> |Image Files| A2[EXIF Extraction]
        A2 --> |Metadata JSON| A3[AI Analysis]
        A3 --> |Analysis Results| A4[Metadata Generation]
    end
    
    subgraph "Target"
        A4 --> |Enriched Metadata| A5[SharePoint Upload]
        A5 --> SP2[SharePoint Target Library]
    end
    
    subgraph "Verification"
        SP2 --> A6[Transfer Verification]
        A6 --> |Reports| Report[Verification Reports]
    end
    
    subgraph "Configuration"
        Config[Configuration Files] --> A1
        Config --> A3
        Config --> A5
        Schema[Metadata Schema] --> A4
    end
    
    subgraph "AI Services"
        OpenAI[OpenAI GPT-4 Vision] --> A3
    end

style Sources fill:#f9f9f9,stroke:#333,stroke-width:1px
style "Data Processing" fill:#f0f8ff,stroke:#333,stroke-width:1px
style Target fill:#f5f5dc,stroke:#333,stroke-width:1px
style Verification fill:#e6ffe6,stroke:#333,stroke-width:1px
style Configuration fill:#fff0f5,stroke:#333,stroke-width:1px
style "AI Services" fill:#f0e6ff,stroke:#333,stroke-width:1px
```

Эта диаграмма представляет высокоуровневую архитектуру системы Agent, показывая основные компоненты и потоки данных между ними.
