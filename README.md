# DisasterLense AI 🌍

**Rapid post-disaster change intelligence using satellite data, geospatial analysis, and AI-assisted prioritization.**

DisasterLense AI is a disaster-response decision-support prototype designed to help responders explore potential disaster-affected areas, assess nearby infrastructure and population exposure, and identify candidate routes and response priorities through an interactive geospatial dashboard.

## 🚨 Problem

After floods and other disasters, responders need to understand where potential damage has occurred, which communities and infrastructure may be affected, and how response resources could be prioritized. Incomplete or outdated information can make these decisions harder.

## 💡 Our Solution

DisasterLense AI combines geospatial processing, satellite change-analysis workflows, weather information, risk assessment, and route analysis in one dashboard.

### Key Features

- **Satellite Change Analysis:** Compare pre-event and post-event raster imagery to identify candidate changes.
- **Interactive Disaster Map:** Explore affected-area geometry and relevant geographic information.
- **Risk Assessment:** Analyze potential exposure and supporting evidence for disaster-response decisions.
- **Population and Infrastructure Context:** Examine available population estimates, roads, hospitals, and other mapped features.
- **Route Analysis:** Generate candidate routes using the available local road network.
- **Weather Integration:** Incorporate available weather information into the assessment workflow.
- **AI-Assisted Evidence:** Organize evidence and generate structured analysis to support human decision-making.
- **Response Prioritization:** Rank candidate areas or response needs using configured scoring logic.

## 🛠️ Technology Stack

- **Language:** Python
- **Dashboard:** Streamlit
- **Geospatial Analysis:** Rasterio, GeoPandas, Shapely
- **Mapping:** Folium, Streamlit-Folium
- **Numerical Analysis:** NumPy, Pandas
- **Routing and Graph Analysis:** NetworkX
- **AI-Assisted Analysis:** Project-specific LLM integration
- **Testing:** Pytest

## 🏗️ How It Works

1. **Collect inputs:** Load available satellite imagery, geographic layers, and supporting data.
2. **Analyze changes:** Process compatible raster inputs to identify candidate changes.
3. **Assess exposure:** Examine mapped population and infrastructure information.
4. **Evaluate risk:** Combine available evidence with the project's configured scoring and prioritization logic.
5. **Explore routes:** Generate candidate paths over the available road network.
6. **Review results:** Use the dashboard to inspect findings and support further investigation.

## 🚀 Getting Started

### Prerequisites

- Python 3.11
- Git
- Windows, Linux, or another supported Python environment

### Installation

Clone the repository:

```bash
git clone <https://github.com/mridulcodes15/DisasterLenseAI>
cd DisasterLenseAI
```

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Launch the dashboard:

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit in your browser.

### Run Tests

```powershell
python -m pytest
```

Check installed dependencies:

```powershell
python -m pip check
```

## ⚠️ Data Quality and Limitations

DisasterLense AI is a decision-support prototype, not a certified emergency-response system.

- The bundled flood-extent GeoJSON is **demonstration data** and must not be interpreted as verified satellite-derived flood detection.
- A verified, real pre-event/post-event Sentinel-1 raster pair has not been established for the bundled demonstration. Temporal-analysis tests validate processing behavior, not real-world flood accuracy.
- Population figures are based on an available raster proxy and may not represent the population present during a specific disaster.
- Listed shelters and destinations require independent verification of their existence, accessibility, capacity, and current safety.
- A route generated from a road network does not establish that roads are currently open, passable, or safe.
- AI-generated assessments and risk scores require human review and should not replace official warnings or emergency-service guidance.

## 🔬 Testing

The project includes tests for satellite analysis, temporal raster comparison, routing, interactive mapping, weather handling, and LLM-related functionality.

The latest local test run completed with **51 tests passed**.

## 🎯 Project Goal

To explore how satellite data, geospatial computation, and AI-assisted analysis can help make disaster-response information more accessible and actionable.

**Important:** All operational decisions must be based on current, independently verified information and guidance from the relevant authorities.