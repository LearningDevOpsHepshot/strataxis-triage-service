"""Smoke tests for the client-facing API service."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_responds():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_classify_endpoint_returns_a_label():
    response = client.post(
        "/classify",
        json={"text": "This invoice is wrong."},
    )

    assert response.status_code == 200
    assert response.json()["label"] == "billing_dispute"
