# AtmosWatch — Distributed Air Quality Risk & Forecasting Platform

**Team:** Shiva Sriram

## Project Overview
AtmosWatch is a distributed cloud-based platform that predicts air quality risk and forecasts pollutant levels using machine learning. It exposes a REST API backed by Redis caching and PostgreSQL logging, containerized with Docker.

## Cloud Technologies Used
| Technology | Role |
|---|---|
| GCP Compute Engine | Hosts the application VM |
| GCP Cloud Storage | Stores model files and datasets |
| Redis (GCP Memorystore) | Caches frequent predictions |
| PostgreSQL (GCP Cloud SQL) | Logs all predictions |

## API Endpoints
| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/predict_aqi` | POST | Classify AQI health risk category |
| `/forecast` | POST | Forecast PM2.5 for next 6 hours |
| `/stats` | GET | System stats and connection status |

## How to Run

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+

### 1. Clone the repo
```bash
git clone https://github.com/ShivaSriram222/atmoswatch.git
cd atmoswatch
```

### 2. Start all services
```bash
docker compose up -d
```
This starts 3 containers:
- Flask API on port 5000
- Redis on port 6379
- PostgreSQL on port 5433

### 3. Test the API
```bash
# Health check
curl http://localhost:5000/health

# Predict AQI
curl -s -X POST http://localhost:5000/predict_aqi \
  -H "Content-Type: application/json" \
  -d '{"city":"Los Angeles","hour":8,"month":1,"pm25_recent":[20,22,25,23,21,24]}'

# Forecast next 6 hours
curl -s -X POST http://localhost:5000/forecast \
  -H "Content-Type: application/json" \
  -d '{"city":"Chicago","hour":14,"month":6,"pm25_recent":[12,13,11,14,13,12]}'

# System stats
curl http://localhost:5000/stats
```

### 4. Retrain models (optional)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 train.py
```

## Architecture


## Architecture
Client (curl / browser)
|
v
Flask REST API (Docker container - port 5000)
|
|-- checks Redis cache first (Docker container - port 6379)
|       cache hit  -> return instantly
|       cache miss -> run ML model
|
|-- logs result to PostgreSQL (Docker container - port 5433)
|
v
ML Models (loaded from disk at startup)

AQI Classifier (Random Forest) -> category + confidence
PM2.5 Forecaster (Random Forest) -> 6-hour prediction
## ML Models
| Model | Algorithm | Performance |
|---|---|---|
| AQI Classifier | Random Forest | 99.1% accuracy |
| PM2.5 Forecaster | Random Forest | RMSE 4.85 ug/m3 |

## Debugging
- Check container logs: `docker compose logs api`
- Check Redis: `docker compose logs redis`
- Check Postgres: `docker compose logs postgres`
- All predictions logged to PostgreSQL `predictions` table
- Redis cache TTL: 10 minutes

## GCP Deployment
Services are designed to run on:
- GCP Compute Engine (e2-medium VM)
- GCP Memorystore for Redis
- GCP Cloud SQL for PostgreSQL
- GCP Cloud Storage for model files
