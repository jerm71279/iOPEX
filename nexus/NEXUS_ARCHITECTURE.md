# iOPEX x NEXUS-CORE Architecture (v2)

This version provides a highly legible, landscape-oriented architectural view designed for clarity and spatial efficiency.

## Overview

The Nexus-Core infrastructure is a modular, agentic ecosystem centered around the Model Context Protocol (MCP). It partitions logic into five distinct horizontal tiers: **Access/Ingress**, **Orchestration**, **Execution**, **Intelligence (RAG)**, and **Persistence**.

## Landscape Architecture Diagram

```mermaid
flowchart LR
    %% Styles
    classDef external fill:#f9f,stroke:#333,stroke-width:2px;
    classDef network fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef core fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef execute fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px;
    classDef intelligence fill:#d1c4e9,stroke:#512da8,stroke-width:2px;
    classDef database fill:#ffccbc,stroke:#bf360c,stroke-width:2px;

    %% 1. ACCESS & INGRESS TIER (Far Left)
    subgraph Tier1["1. ACCESS & SECURITY"]
        direction TB
        Ext_API["Anthropic/OpenAI APIs"]:::external
        ZT["Cloudflare Zero Trust"]:::network
        TG["Twingate Connector"]:::network
        Adm["Adminer :8080"]:::network
    end

    %% 2. ORCHESTRATION TIER (Center Left)
    subgraph Tier2["2. CORE ORCHESTRATION"]
        direction TB
        NexusMCP["NEXUS-CORE MCP :7777\n(Brain / Task Tracker)"]:::core
        
        subgraph AgentPool["Specialized Agent Pool"]
            direction TB
            PMO["PMO (Claude Opus)"]:::core
            SHIFT["SHIFT (Claude Sonnet)"]:::core
            NEXUS["NEXUS (Tooling)"]:::core
            REPORT["REPORT (Output)"]:::core
        end
    end

    %% 3. EXECUTION TIER (Center Right)
    subgraph Tier3["3. EXECUTION & APIS"]
        direction TB
        ShiftAPI["jit-shift-api :8000\n(Core Services)"]:::execute
        AgentAPI["jit-iopex-agent :8001\n(Agent Runtime)"]:::execute
        
        subgraph MCPHub["MCP Tooling Hub :8010"]
            direction TB
            ShiftTools["shift_tools.py"]:::execute
            IopexTools["iopex_tools.py"]:::execute
            PamTools["pam_tools.py"]:::execute
        end
        
        IngestWorker["jit-ingest-worker\n(Background Processing)"]:::execute
    end

    %% 4. INTELLIGENCE TIER (Far Right / Top)
    subgraph Tier4["4. INTELLIGENCE & RAG"]
        direction TB
        DigitalExpert["Digital Expert\n(Telegram / LangGraph)"]:::intelligence
        Embeddings["HuggingFace\n(Local Vectorization)"]:::intelligence
        Mem0["Mem0\n(Long-term Memory)"]:::intelligence
    end

    %% 5. DATA PERSISTENCE TIER (Bottom)
    subgraph Tier5["5. DATA PERSISTENCE LAYER"]
        direction LR
        Postgres[(PostgreSQL :5432\nRelational State)]:::database
        Redis[(Redis :6379\nBroker/Cache)]:::database
        Qdrant[(Qdrant :6333\nVector Store)]:::database
    end

    %% CORE WIRING (Simplified/Condensed)
    
    %% Ingress to Orchestration/Execution
    ZT --> ShiftAPI
    TG --> AgentAPI
    Ext_API -.-> NexusMCP
    
    %% Orchestration to Execution
    NexusMCP <--> AgentPool
    AgentPool --> MCPHub
    AgentPool --> ShiftAPI
    
    %% Intelligence to Data
    DigitalExpert --> Embeddings
    Embeddings --> Qdrant
    DigitalExpert --> Postgres
    
    %% Execution to Data
    ShiftAPI --> Postgres
    AgentAPI --> Qdrant
    IngestWorker --> Redis
    
    %% Memory link
    NexusMCP -.-> Mem0
```

## Detailed Component Breakdown

### **1. Access & Security**
- **Cloudflare Zero Trust / Twingate**: Secure tunneling for remote access without exposing ports to the public internet.
- **Adminer**: Web UI for database management.

### **2. Core Orchestration**
- **Nexus-Core MCP (7777)**: The central "state machine." Tracks task lifecycles, ledger entries, and cross-agent coordination.
- **Agent Pool**: Functional roles powered by specific Claude models (Opus for high-level planning, Sonnet for code/technical execution).

### **3. Execution & APIs**
- **jit-shift-api (8000)**: The primary REST interface for internal platform operations.
- **jit-iopex-agent (8001)**: The runtime environment where agents actually execute their logic.
- **MCP Hub (8010)**: A centralized tool repository that exposes Python scripts as standardized capabilities (tools) to any connecting agent.

### **4. Intelligence & RAG**
- **Digital Expert**: A complex workflow using **LangGraph** to handle multi-step reasoning.
- **HuggingFace**: Runs local embedding models to avoid sending raw data to external providers for vectorization.
- **Mem0**: A persistence layer for user preferences and past interaction memory.

### **5. Data Persistence**
- **PostgreSQL**: The source of truth for all relational data (users, tasks, logs).
- **Redis**: Facilitates fast communication between the API and background workers (Celery).
- **Qdrant**: High-performance vector database for retrieving contextually relevant documents and information.
