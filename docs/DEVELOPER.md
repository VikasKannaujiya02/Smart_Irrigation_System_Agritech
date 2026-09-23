# Developer Manual

## Project Structure

```
AI-Smart-Irrigation-Digital-Twin/
├── configs/              # Configuration profiles
├── data/                 # Data directory (sqlite, backups)
├── docs/                 # Documentation
├── frontend/             # React + Vite frontend
├── raspberry_pi/         # Backend application
│   ├── ai/               # AI models and data pipeline
│   ├── ai_engine/        # OTA, remote config, health monitor
│   ├── analytics/        # Analytics engine
│   ├── backup/           # Backup/restore system
│   ├── communication/    # LoRa communication
│   ├── configuration_manager/  # Config management
│   ├── continuous_learning/    # Drift detection, champion-challenger
│   ├── dashboard/        # FastAPI backend
│   ├── database/         # Database layer
│   ├── decision_engine/  # Decision making
│   └── digital_twin/     # Digital twin simulation
├── firmware/             # Arduino firmware
└── logs/                 # Log files
```

## Development Setup

### Backend
1. Create virtual environment
   ```bash
   cd raspberry_pi
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate   # Windows
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```
3. Run dev server
   ```bash
   uvicorn dashboard.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend
1. Install dependencies
   ```bash
   cd frontend
   npm install
   ```
2. Run dev server
   ```bash
   npm run dev
   ```

## Running Tests

```bash
cd raspberry_pi
pytest tests/
```

## Coding Standards

- Follow PEP 8 for Python
- Use type hints
- Write docstrings for functions
- Run `black` and `isort` for formatting
- Run `flake8` for linting

## Adding New Features

### New API Endpoint
1. Add endpoint in `raspberry_pi/dashboard/main.py`
2. Update or add schemas in `schemas.py` if needed
3. Write tests in `tests/` directory

### New AI Model
1. Add model in `raspberry_pi/ai/models/`
2. Register model in model registry
3. Update trainer and predictor classes

## CI/CD Pipeline

The project uses GitHub Actions for CI/CD:
- Runs tests on every push
- Lints code with flake8
- Builds Docker images on main branch pushes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Create pull request
