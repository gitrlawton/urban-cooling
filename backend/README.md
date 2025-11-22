# ShadePlan Backend

Python backend service for ShadePlan using Google ADK (Agent Development Kit), FastAPI, and Google Earth Engine.

## Overview

This backend provides an AI agent that analyzes urban heat zones using LANDSAT thermal imagery and identifies the hottest areas that would benefit most from tree planting.

## Architecture

- **Framework**: FastAPI
- **AI Agent**: Google ADK with Gemini
- **Data Source**: Google Earth Engine (LANDSAT thermal imagery)
- **Deployment**: Google Cloud Run

## Project Structure

```
backend/
├── agents/              # AI agents
│   └── urban_cooling_analyst.py
├── tools/               # Agent tools
│   ├── geocoding.py     # Convert locations to coordinates
│   ├── heat_data.py     # Fetch LANDSAT thermal data
│   ├── land_use.py      # Fetch land use data (OSM)
│   └── analysis.py      # Heat zone analysis
├── api/                 # FastAPI endpoints
│   └── main.py
├── config/              # Configuration
│   └── settings.py
├── tests/               # Unit tests
└── .env                 # Environment variables (not in git)
```

## Setup

### Prerequisites

- Python 3.11+
- Google Cloud Project with Earth Engine access
- Gemini API key

### Installation

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Authenticate Earth Engine:
   ```bash
   earthengine authenticate
   earthengine set_project shadeplan
   ```

### Running Locally

```bash
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### `GET /health`
Health check endpoint.

**Response:**
```json
{"status": "healthy"}
```

### `POST /analyze`
Analyze heat zones for a given location.

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
  "analysis_date": "2024-01-01",
  "heat_zones": [
    {
      "id": 1,
      "geometry": {...},
      "heat_score": 85.5,
      "temp_celsius": 32.4,
      "priority": "high",
      "area_sqm": 5000
    }
  ],
  "metadata": {
    "total_zones_analyzed": 50,
    "data_source": "LANDSAT-8/9"
  }
}
```

## Environment Variables

See `.env.example` for all required variables:

- `GCP_PROJECT_ID`: Google Cloud project ID
- `GEMINI_API_KEY`: Gemini API key
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key
- `DEBUG`: Enable debug mode

## Testing

Run tests:
```bash
pytest tests/
```

## Deployment

### Docker

Build image:
```bash
docker build -t shadeplan-backend .
```

Run container:
```bash
docker run -p 8080:8080 --env-file .env shadeplan-backend
```

### Google Cloud Run

Deploy:
```bash
gcloud run deploy shadeplan-backend \
  --source . \
  --region us-west1 \
  --allow-unauthenticated
```

## License

MIT
