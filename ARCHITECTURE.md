# DisasterLense AI — System Architecture

## Overview

DisasterLense AI is a disaster-response decision-support prototype that combines geospatial analysis, change detection, risk assessment, impact forecasting, and route evaluation to help identify and prioritize areas requiring attention.

## Architecture Diagram

```mermaid
flowchart TB
    U["User"] --> APP["Streamlit Application<br/>app.py"]

    subgraph DATA["1. Data and Inputs"]
        SAT["Satellite / Temporal Imagery"]
        WEATHER["Weather Data"]
        GEO["Geospatial Data"]
        INFRA["Population and Infrastructure Data"]
    end

    subgraph ANALYSIS["2. Analysis Services"]
        CHANGE["Change Detection<br/>src/change_detection"]
        LIVE["Live Risk Assessment<br/>src/future/live_risk.py"]
        IMPACT["Impact Analysis<br/>src/future/impact.py"]
        FORECAST["Future Impact Forecasting<br/>src/future/forecast.py"]
    end

    subgraph ENGINE["3. Decision-Support Engine"]
        MODELS["Core Data Models<br/>src/core/models.py"]
        PRIORITY["Priority Scoring and Zone Ranking<br/>src/priority"]
        ROUTING["Route Risk and Candidate Ranking<br/>src/routing"]
        LLM["AI Evidence Analysis<br/>src/llm"]
    end

    subgraph PRESENTATION["4. User Interface"]
        DASH["Disaster Dashboard<br/>src/ui/disaster_dashboard.py"]
        MAP["Interactive Map<br/>src/ui/interactive_map.py"]
        RESULTS["Risk Insights and Response Recommendations"]
    end

    SAT --> CHANGE
    GEO --> CHANGE
    WEATHER --> LIVE
    GEO --> IMPACT
    INFRA --> IMPACT

    CHANGE --> MODELS
    LIVE --> MODELS
    IMPACT --> FORECAST
    MODELS --> PRIORITY
    MODELS --> ROUTING
    MODELS --> LLM

    PRIORITY --> DASH
    ROUTING --> MAP
    LLM --> DASH
    FORECAST --> DASH
    DASH --> RESULTS
    MAP --> RESULTS

    APP --> DASH

    classDef input fill:#E8F1FA,stroke:#4778A8,color:#172B4D
    classDef analysis fill:#E5F3E8,stroke:#4F8A60,color:#173D25
    classDef engine fill:#FFF1D6,stroke:#B88932,color:#513B12
    classDef ui fill:#F0E8FA,stroke:#8261A8,color:#34204D

    class SAT,WEATHER,GEO,INFRA input
    class CHANGE,LIVE,IMPACT,FORECAST analysis
    class MODELS,PRIORITY,ROUTING,LLM engine
    class APP,DASH,MAP,RESULTS ui
```

## Main Components

| Component | Responsibility |
|---|---|
| Streamlit application | Application entry point and user-facing workflow |
| Change detection | Analyzes temporal imagery and changes between observations |
| Live risk assessment | Evaluates available weather and risk information |
| Impact analysis | Examines potential effects on people and infrastructure |
| Forecasting | Estimates possible future impacts |
| Priority engine | Scores and ranks areas for response attention |
| Routing engine | Evaluates route candidates and associated risks |
| LLM evidence analysis | Produces AI-assisted analysis grounded in supplied evidence |
| Interactive dashboard | Presents maps, metrics, risk information, and results |

## Data Flow

1. The application receives or loads available disaster-related data.
2. Analysis services process relevant imagery, weather, and geospatial information.
3. Impact and risk outputs feed into prioritization, route evaluation, and AI-assisted evidence analysis.
4. The dashboard presents the resulting information for human review and decision support.

## Important Limitations

- Results depend on the availability, quality, and freshness of the input data.
- Demo datasets and proxy values must not be interpreted as verified real-time disaster measurements.
- Route risk estimates do not independently confirm that a road is currently passable or safe.
- AI-generated analysis should be checked against its supporting evidence.
- The architecture illustrates the intended relationships between project modules; actual execution paths may differ as the implementation evolves.

DisasterLense AI is a decision-support prototype, not a replacement for emergency services or verified official disaster-response systems.
