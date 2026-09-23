# AI Smart Irrigation Digital Twin

Production-grade AI-powered smart irrigation system for Raspberry Pi 4, Arduino UNO nodes, LoRa SX1278 communication, weather integration, AI prediction, digital twin, analytics, safety controls, and dashboard operation.

## Features

### Core
- LoRa-based sensor/pump node communication with ACK, retries, and CRC validation
- SQLite database with connection pooling, transactions, and backups
- Weather integration (OpenWeatherMap)
- AI prediction (soil moisture, irrigation recommendations)
- Digital twin simulation
- Advanced analytics engine
- Decision engine with safety controls
- Real-time dashboard (React + Vite)

### Production Features (New)
- **Docker & Docker Compose** for easy deployment
- **Environment Variables & Configuration Profiles** (dev/staging/prod)
- **Structured Logging** with rotation
- **Backup & Restore System** (full system and database-only)
- **OTA Update Management**
- **Remote Configuration**
- **Health Monitoring & System Diagnostics**
- **CI/CD Pipeline** (GitHub Actions)
- **Automated Testing** (pytest)
- **Continuous Learning** (model drift, data drift, sensor drift, champion-challenger models)

## Fixed Hardware

- Gateway: Raspberry Pi 4
- Communication: LoRa SX1278 Gateway
- Sensor Node: Arduino UNO, LoRa SX1278 V1.0, Soil Moisture Sensor, DHT22, Battery Monitoring
- NPK Node: Arduino UNO, LoRa SX1278 V1.0, RS485 TTL, 7 in 1 NPK Sensor, Battery Monitoring
- Pump Controller: Arduino UNO, LoRa SX1278 V1.2, Relay, Manual Switch, Pump Feedback

The hardware above is fixed and must not be replaced unless explicitly instructed.

## Quick Start

For detailed deployment instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Docker (Recommended)

```bash
git clone <repo-url>
cd AI-Smart-Irrigation-Digital-Twin
cp .env.example .env
# Edit .env to set your configuration
docker-compose up -d
```

Access the application at:
- Frontend: http://localhost
- Backend API Docs: http://localhost:8000/docs

### Local Development

See [docs/DEVELOPER.md](docs/DEVELOPER.md) for detailed setup instructions.

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md)
- [User Manual](docs/USER_MANUAL.md)
- [Developer Manual](docs/DEVELOPER.md)
- [Maintenance Manual](docs/MAINTENANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Communication Protocol](docs/COMMUNICATION_PROTOCOL.md)
- [Database Layer](docs/DATABASE_LAYER.md)

## Project Structure

```
AI-Smart-Irrigation-Digital-Twin/
├── configs/              # Configuration profiles (dev/staging/prod)
├── data/                 # Data directory (sqlite, backups, weather cache)
├── docs/                 # Documentation
├── frontend/             # React + Vite frontend
├── raspberry_pi/         # Backend application
│   ├── ai/               # AI models and data pipeline
│   ├── ai_engine/        # OTA, remote config, health monitor
│   ├── analytics/        # Analytics engine
│   ├── backup/           # Backup/restore system
│   ├── communication/    # LoRa communication
│   ├── configuration_manager/  # Config management
│   ├── continuous_learning/    # Drift detection, champion-challenger, retraining
│   ├── dashboard/        # FastAPI backend
│   ├── database/         # Database layer
│   ├── decision_engine/  # Decision making
│   ├── digital_twin/     # Digital twin simulation
│   └── tests/            # Backend tests
├── firmware/             # Arduino firmware
└── logs/                 # Log files
```

## Contributing

See [docs/DEVELOPER.md](docs/DEVELOPER.md) for contributing guidelines.

## License

Proprietary - For authorized use only.
