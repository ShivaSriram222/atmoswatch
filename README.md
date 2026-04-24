# AtmosWatch — Distributed Air Quality Risk & Forecasting Platform

**Team:** Shiva Sriram (solo)

---

## Project Overview

AtmosWatch is a distributed cloud-based platform that predicts air quality health risk and forecasts PM2.5 pollutant levels for three US cities — Los Angeles, Chicago, and Denver. It exposes a Flask REST API backed by Redis caching and PostgreSQL logging, containerized with Docker, and designed to run on GCP.

---

## Cloud Technologies Used

| Technology | GCP Service | Role |
|---|---|---|
| Cloud Compute | Compute Engine (e2-medium) | Hosts Flask API and all Docker containers |
| In-Memory Cache | Memorystore (Redis 7) | Caches predictions with 10-min TTL |
| Managed Database | Cloud SQL (PostgreSQL 15) | Logs all predictions persistently |
| Object Storage | Cloud Storage (GCS) | Stores serialized .pkl model files |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Web dashboard |
| `/health` | GET | Health check — confirms API and models are loaded |
| `/predict_aqi` | POST | Classify AQI health risk category + confidence score |
| `/forecast` | POST | Forecast PM2.5 for next 6 hours + trend direction |
| `/stats` | GET | System stats — cache count, DB count, connection status |

---

## How to Run

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ (for retraining only)

### 1. Clone the repo
```bash
git clone https://github.com/ShivaSriram222/atmoswatch.git
cd atmoswatch
```

### 2. Start all services
```bash
docker compose up -d
```

This starts 3 containers automatically:
- **Flask API** on port 5000
- **Redis** on port 6379
- **PostgreSQL** on port 5433

### 3. Open the dashboard
Go to `http://localhost:5000` in your browser.

### 4. Test the API with curl
```bash
# Health check
curl http://localhost:5000/health

# Predict AQI (first call — runs model)
curl -s -X POST http://localhost:5000/predict_aqi \
  -H "Content-Type: application/json" \
  -d '{"city":"Los Angeles","hour":8,"month":1,"pm25_recent":[20,22,25,23,21,24]}'

# Predict AQI (second call — served from Redis cache)
curl -s -X POST http://localhost:5000/predict_aqi \
  -H "Content-Type: application/json" \
  -d '{"city":"Los Angeles","hour":8,"month":1,"pm25_recent":[20,22,25,23,21,24]}'

# Forecast next 6 hours
curl -s -X POST http://localhost:5000/forecast \
  -H "Content-Type: application/json" \
  -d '{"city":"Chicago","hour":14,"month":6,"pm25_recent":[12,13,11,14,13,12]}'

# System stats — verify all 4 technologies connected
curl -s http://localhost:5000/stats
```

### 5. Retrain models (optional)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 train.py
```

---

## Architecture

```
Client (browser / curl / Locust)
        |
        v
Flask REST API  (Docker — port 5000)
        |
        |-- check Redis cache first (Docker — port 6379)
        |       cache hit  -> return in <5ms
        |       cache miss -> run ML model (50-150ms)
        |                     -> cache result (10 min TTL)
        |                     -> log to PostgreSQL
        v
PostgreSQL  (Docker — port 5433)
ML Models loaded from disk at startup
```

---

## ML Models

| Model | Algorithm | Performance |
|---|---|---|
| AQI Classifier | Random Forest (100 trees) | 99.1% accuracy |
| PM2.5 Forecaster | Random Forest (100 trees) | RMSE 4.85 ug/m3 |

Both models trained on 6,000 synthetic hourly air quality records with realistic rush-hour and seasonal patterns. Temporal hold-out split (last 20% by date) used to prevent data leakage.

---

## Debugging

```bash
# Check all containers are running
docker compose ps

# See Flask API logs in real time
docker compose logs api

# See Redis logs
docker compose logs redis

# See PostgreSQL logs
docker compose logs postgres

# Verify all 4 services connected
curl -s http://localhost:5000/stats
```

---

## Project Structure

```
atmoswatch/
├── api/
│   ├── app.py              # Flask REST API
│   └── static/
│       └── dashboard.html  # Web dashboard
├── models/
│   ├── aqi_classifier.pkl  # Trained classifier
│   ├── pm25_forecaster.pkl # Trained forecaster
│   └── features.json       # Feature names
├── data/
│   └── air_quality.csv     # Training data
├── train.py                # Full training pipeline
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-service orchestration
└── requirements.txt        # Python dependencies
```

---

## GCP Deployment (intended)

The system is designed to deploy on:
- **GCP Compute Engine** e2-medium VM running Ubuntu 22.04
- **GCP Memorystore** for managed Redis
- **GCP Cloud SQL** for managed PostgreSQL
- **GCP Cloud Storage** for model file storage

```bash
# On the GCP VM after cloning:
docker compose up -d
```

---

*AtmosWatch | Shiva Sriram | Distributed Systems & Cloud Computing*
