from fastapi.testclient import TestClient
from raspberry_pi.dashboard.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime_seconds" in data


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_diagnostics_endpoint():
    response = client.get("/api/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert "system_metrics" in data
    assert "health" in data
    assert "environment" in data
