import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_predict_endpoint(client):
    """Test predict endpoint"""
    response = client.get("/api/predict")
    assert response.status_code in [200, 500]  # 500 is expected 5% of time

    if response.status_code == 200:
        data = response.get_json()
        assert "prediction" in data
        assert "confidence" in data
        assert data["prediction"] in ["normal", "anomaly"]


def test_predict_endpoint_returns_json(client):
    """Test that predict returns valid JSON"""
    response = client.get("/api/predict")
    assert response.content_type == "application/json"
