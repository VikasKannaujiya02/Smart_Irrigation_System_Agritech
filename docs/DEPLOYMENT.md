# Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10+ (for local development)
- OpenWeatherMap API key (for weather data)

## Quick Start with Docker Compose

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd AI-Smart-Irrigation-Digital-Twin
   ```

2. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit environment variables** in `.env`:
   ```env
   ENVIRONMENT=production
   WEATHER_API_KEY=your_actual_api_key
   WEATHER_LATITUDE=0.0
   WEATHER_LONGITUDE=0.0
   ```

4. **Start the application**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Configuration Profiles

Three configuration profiles are available:

- **development**: For local development with debug logging
- **staging**: For pre-production testing
- **production**: For live deployment (default)

Set the active profile via the `ENVIRONMENT` environment variable.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `WEATHER_API_KEY` | OpenWeatherMap API key | |
| `WEATHER_LATITUDE` | Field location latitude | 0.0 |
| `WEATHER_LONGITUDE` | Field location longitude | 0.0 |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## Manual Deployment (Without Docker)

### Backend Setup

1. **Install dependencies**
   ```bash
   cd raspberry_pi
   pip install -r requirements.txt
   ```

2. **Run the backend**
   ```bash
   uvicorn dashboard.main:app --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Build for production**
   ```bash
   npm run build
   ```

3. **Serve with Nginx or your preferred web server**

## Updating the Application

### Docker Deployment
```bash
docker-compose pull
docker-compose up -d
```

### OTA Updates
The system supports OTA updates. Configure OTA settings in `configs/production.yaml`.

## Health Checks

Monitor application health via:
- `/health` endpoint
- Docker health checks (configured in `docker-compose.yml`)
