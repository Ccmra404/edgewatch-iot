from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import storage


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_latest_404(client: TestClient) -> None:
    r = client.get("/devices/unknown-device/latest")
    assert r.status_code == 404


def test_latest_and_recent_after_save(client: TestClient) -> None:
    storage.save("demo-device", {"temperature": 22.0, "seq": 1})
    storage.save("demo-device", {"temperature": 23.0, "seq": 2})

    r = client.get("/devices/demo-device/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["device_id"] == "demo-device"
    assert body["payload"]["temperature"] == 23.0

    r2 = client.get("/devices/demo-device/recent?limit=5")
    assert r2.status_code == 200
    data = r2.json()
    assert data["device_id"] == "demo-device"
    assert len(data["items"]) == 2
    assert data["items"][0]["payload"]["seq"] == 2
    assert data["items"][1]["payload"]["seq"] == 1


def test_recent_empty(client: TestClient) -> None:
    r = client.get("/devices/no-such-device/recent?limit=3")
    assert r.status_code == 200
    assert r.json()["items"] == []
