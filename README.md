<div align="center">
  <img src="https://img.icons8.com/color/120/000000/sprout.png" alt="Smart Irrigation Logo"/>
  <h1>AI Smart Irrigation Digital Twin 🌾💧</h1>
  <p><strong>Next-Gen Agritech Platform powered by AI, LoRa RF, and IoT</strong></p>
  
  [![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=flat&logo=react)](https://reactjs.org/)
  [![TailwindCSS](https://img.shields.io/badge/Styling-Tailwind-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)
  [![PyTorch](https://img.shields.io/badge/AI-PyTorch-EE4C2C?style=flat&logo=pytorch)](https://pytorch.org/)
  [![LoRa](https://img.shields.io/badge/Comm-LoRa_SX1278-FF9900?style=flat)](https://lora-alliance.org/)
  [![Localization](https://img.shields.io/badge/Language-English_%7C_Hindi-4CAF50?style=flat)](#)
</div>

---

## 📖 Overview

The **AI Smart Irrigation Digital Twin** is an enterprise-grade IoT platform designed for precision agriculture. This repository contains the complete software stack (Sensors ➔ LoRa RF ➔ Raspberry Pi ➔ FastAPI ➔ React Dashboard), offering real-time field monitoring, AI-driven irrigation forecasting, and advanced crop diagnostics (Plant Disease & Pest Detection).

Built specifically for rugged environments, it guarantees connectivity via **LoRa SX1278 module** allowing communication up to 10 kilometers without reliance on Wi-Fi or cellular networks.

---

## 🌟 Core Features

### 🚜 1. Hardware Integration (LoRa IoT)
- **Edge Devices**: Arduino Nano/ESP8266 nodes equipped with Soil Moisture, Temperature, Humidity, and NPK sensors.
- **Communication Protocol**: Long-Range LoRa (SX1278) via SPI.
- **Controller Hub**: Raspberry Pi 4 operating as the central orchestrator and Decision Engine.

### 🧠 2. AI Decision Engine & Models
- **Hybrid TCN-LSTM Architecture**: Powerful continuous-learning model that predicts soil moisture horizons across 24/48 hours based on telemetry and weather history.
- **Rule-based & AI-driven Modes**: Swap effortlessly between manual threshold (rule-based) irrigation and full AI autonomous irrigation.
- **Rain Yield Integration**: Uses external Weather API (OpenMeteo) and internal rain gauges to suppress pump activation intelligently when rain is expected.

### 🐞 3. AI Computer Vision Modules
- **🌿 Plant Disease Detection**: Drag/Drop or camera capture of plant leaves to identify diseases (e.g., Late Blight) using deep learning classifiers. Provides management strategies.
- **🐛 Pest Detection**: Identify crop pests using bounding box annotations (Object Detection), providing pest count data and IPM (Integrated Pest Management) suggestions.

### 📊 4. Advanced Frontend Dashboard (React + Vite)
- **Bilingual Interface**: Native support for **English** and **Hindi (हिंदी)** via `react-i18next`.
- **Real-time Digital Twin**: Replicates field states with fluid animations and responsive widget design.
- **Analytics & Water Saving**: View exactly how many liters of water were saved using AI vs traditional scheduled irrigation.
- **Crop Lifecycle Tracker**: Track Phenological stages of crops (GDD - Growing Degree Days calculation).
- **Responsive Dark/Light Mode**: Full theme customization built entirely with Tailwind CSS utility classes.

---

## 🧱 Architecture Diagram

```mermaid
graph TD;
    subgraph Edge Nodes (Field)
        S1[Sensor Node 1 - Arduino] -->|LoRa SX1278| Gateway
        S2[Sensor Node 2 - ESP8266] -->|LoRa SX1278| Gateway
        P1[Pump Controller] <-- LoRa SX1278 --> Gateway
    end
    
    subgraph Central Hub (Raspberry Pi 4)
        Gateway[LoRa Interface module] <--> O[System Orchestrator]
        O <--> DB[(SQLite DB)]
        O <--> AI[AI Engine / Models]
        O <--> W[Weather Service]
        O <--> API[FastAPI Server]
    end
    
    subgraph User Interface
        API <--> UI[React Vite Dashboard]
    end
```

---

## 🛠️ Tech Stack

**Frontend**:
- Vite + React (v18)
- Tailwind CSS
- chart.js / react-chartjs-2
- lucide-react (Icons)
- i18next (Localization)

**Backend**:
- Python (FastAPI)
- Uvicorn (ASGI Server)
- PyTorch (TCN-LSTM continuous learning base)
- SQLite3 (Async Database via Pydantic/Dataclasses)

**Hardware Support Libraries**:
- `spidev` (Raspberry Pi SPI wrapper)
- `LoRaRF` (Python library for SX1278 interface)

---

## 🚀 Getting Started

### 1. Requirements
* Raspberry Pi Board (3B+ or 4) with SPI enabled (`sudo raspi-config`)
* Python 3.9+
* Node.js v18+ 
* Installed LoRa SX1278 Module connected to RPi GPIO pins.

### 2. Backend Setup
```bash
# Navigate to project root
cd Smart_Irrigation_System_Agritech

# Create virtual environment 
python3 -m venv venv
source venv/bin/activate

# Install dependencies (ensure PyTorch is compatible with your architecture)
pip install fastapi uvicorn torch pydantic requests spidev
# Note: For production on ARM64, install torch via pre-compiled wheels if needed.

# Run the FastAPI server in development mode
cd raspberry_pi
uvicorn dashboard.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
# Navigate to frontend package
cd frontend

# Install node modules
npm install

# Start the Vite dev server
npm run dev
```

The frontend can be accessed simultaneously at `http://localhost:5173`.

---

## 📷 Screenshots

| Dashboard (English) | Plant Disease (Hindi) |
| :---: | :---: |
| <img src="docs/screens/dashboard.png" width="400"/> | <img src="docs/screens/disease_hi.png" width="400"/> |

| Pest Detection & Bounding Boxes | Analytics & Water Saving |
| :---: | :---: |
| <img src="docs/screens/pest.png" width="400"/> | <img src="docs/screens/analytics.png" width="400"/> |

*(Note: Add screenshot assets to `docs/screens/` directory to enable images).*

---

## 🤝 Contribution Guidelines
This system forms the foundational backbone of a modern Digital Twin architecture for agriculture.
* To add new AI vision models: Place `.onnx` or `.pt` files inside `raspberry_pi/ai/models/` and modify `dashboard/main.py`.
* To add translations: Update `frontend/src/locales/en/translation.json` and `/hi/translation.json`.

---

<div align="center">
  <p>Built with ❤️ for precision agriculture, sustainable farming, and water conservation.</p>
</div>
