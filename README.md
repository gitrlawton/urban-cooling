# ShadePlan

> AI-powered urban heat zone identification and cooling strategy planning

ShadePlan is a multi-agent AI system that identifies the hottest areas in cities and recommends tree-based cooling interventions. Users input a city name or zip code and receive an interactive map highlighting critical heat zones where strategic tree planting would have the greatest cooling impact.

---

## Problem Statement

Cities worldwide struggle with **extreme urban heat**, which causes health risks, increased energy costs, and reduced quality of life. But cities face multiple barriers to addressing it:

- No unified system to **identify and prioritize** the hottest, most vulnerable areas
- Planners lack data-driven insights to target cooling interventions effectively
- City leaders need **quantifiable justification** to allocate limited budgets for urban cooling

Current approaches to urban heat mitigation are **manual, fragmented, and reactive**.

---

## Solution

ShadePlan uses AI agents powered by Google's Agent Development Kit (ADK) and Gemini to analyze satellite thermal imagery, identify critical heat zones, and recommend where tree-based cooling strategies would be most effective.

**How it works:**

1. User enters a city name or zip code
2. The AI agent fetches LANDSAT thermal imagery via Google Earth Engine
3. Land use data is retrieved from OpenStreetMap
4. Heat zones are scored and filtered for plantable areas
5. Results are displayed on an interactive map

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Next.js Frontend (localhost:3000)      │
│  ├─ React + TypeScript                  │
│  ├─ Leaflet Map Visualization           │
│  └─ API Route → Backend                 │
└──────────────────┬──────────────────────┘
                   │ HTTP
                   ↓
┌─────────────────────────────────────────┐
│  Python Backend (localhost:8080)        │
│  ├─ FastAPI                             │
│  ├─ Google ADK Agent                    │
│  │   └─ Urban Cooling Analyst           │
│  └─ Tools                               │
│      ├─ Geocoding (Nominatim)           │
│      ├─ Heat Data (Earth Engine)        │
│      ├─ Land Use (OpenStreetMap)        │
│      └─ Analysis (Grid Processing)      │
└─────────────────────────────────────────┘
```

### Agent Tools

| Tool                     | Purpose                            | Data Source                       |
| ------------------------ | ---------------------------------- | --------------------------------- |
| `geocode_location`       | Convert city/zip to coordinates    | OpenStreetMap Nominatim           |
| `fetch_heat_data`        | Get thermal satellite imagery      | Google Earth Engine (LANDSAT 8/9) |
| `fetch_land_use_data`    | Get buildings, parks, water bodies | OpenStreetMap Overpass API        |
| `process_heat_raster`    | Convert thermal data to grid       | Local computation                 |
| `calculate_heat_scores`  | Score zones by heat intensity      | Local computation                 |
| `filter_plantable_areas` | Remove non-plantable zones         | Local computation                 |

---

## Tech Stack

**Backend:**

- Python 3.11+
- Google ADK (Agent Development Kit)
- Gemini 2.0 Flash (LLM)
- FastAPI
- Google Earth Engine API

**Frontend:**

- Next.js 15
- TypeScript
- Tailwind CSS
- Leaflet / React-Leaflet

**Current Status:** Local development / demo

---

## Project Structure

```
urban-cooling/
├── backend/
│   ├── agents/
│   │   └── urban_cooling_analyst.py    # Main AI agent
│   ├── api/
│   │   └── main.py                     # FastAPI endpoints
│   ├── tools/
│   │   ├── geocoding.py                # Location → coordinates
│   │   ├── heat_data.py                # LANDSAT thermal data
│   │   ├── land_use.py                 # OpenStreetMap data
│   │   └── analysis.py                 # Heat scoring & filtering
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── api/analyze-heat/route.ts   # API proxy
│   │   ├── components/
│   │   │   ├── SearchForm.tsx
│   │   │   ├── MapView.tsx
│   │   │   ├── HeatZoneLayer.tsx
│   │   │   └── Legend.tsx
│   │   ├── types/index.ts
│   │   └── page.tsx
│   └── package.json
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud Platform account
- Google Earth Engine access ([sign up here](https://earthengine.google.com/signup/))

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - GCP_PROJECT_ID
# - GOOGLE_API_KEY (Gemini API key)
# - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)

# Authenticate Earth Engine
earthengine authenticate
earthengine set_project YOUR_PROJECT_ID

# Run the backend
python -m api.main
```

Backend runs at `http://localhost:8080`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
echo "BACKEND_URL=http://localhost:8080" > .env.local

# Run the frontend
npm run dev
```

Frontend runs at `http://localhost:3000`

---

## Usage

1. Open `http://localhost:3000` in your browser
2. Enter a US city name (e.g., "Los Angeles, CA") or zip code (e.g., "90210")
3. Click "Analyze"
4. Wait 2-3 minutes for analysis to complete
5. View heat zones on the interactive map
6. Click zones to see details (temperature, heat score, priority)

---

## Heat Score Interpretation

Heat zones are scored on a relative 0-100 scale:

| Score  | Priority | Meaning                                       |
| ------ | -------- | --------------------------------------------- |
| 80-100 | High     | Hottest 20% of the area - critical heat zones |
| 60-79  | Medium   | Above average heat                            |
| 40-59  | Low      | Around average temperature for the area       |

Scores are relative to the analyzed area, not absolute temperatures.

---

## API Reference

### `POST /analyze`

Analyze heat zones for a location.

**Request:**

```json
{
  "location": "San Francisco, CA"
}
```

**Response:**

```json
{
  "location": "San Francisco, CA",
  "analysis_date": "2025-11-30",
  "heat_zones": [
    {
      "id": 1,
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "heat_score": 87.5,
      "temp_celsius": 32.4,
      "priority": "high",
      "area_sqm": 10000
    }
  ],
  "metadata": {
    "total_zones_analyzed": 500,
    "data_source": "LANDSAT-8/9 Collection 2"
  }
}
```

---

## Deployment (Future)

The project includes a Dockerfile for future cloud deployment. Currently running in local development mode.

**Planned deployment targets:**

- Backend: Google Cloud Run
- Frontend: Vercel

---

## Future Roadmap

- **Phase 2**: Shade simulation with time-of-day shadows
- **Phase 3**: Tree species recommendations
- **Phase 4**: Equity analysis for vulnerable communities
- **Phase 5**: ROI calculator for cooling benefits
- **Phase 6**: Comprehensive planting plan generator

---

## Data Sources

- **Thermal Imagery**: [LANDSAT 8/9 Collection 2](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2) via Google Earth Engine
- **Geocoding**: [OpenStreetMap Nominatim](https://nominatim.org/)
- **Land Use**: [OpenStreetMap Overpass API](https://overpass-api.de/)

---

## License

This project is released under the MIT License.

---

## Acknowledgments

- Google Agent Development Kit (ADK) team
- Google Earth Engine team
- OpenStreetMap contributors
