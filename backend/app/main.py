from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from app.mqtt_worker import start_mqtt_subscriber
from app.storage import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mqtt_client = None


def _mqtt_disabled() -> bool:
    return os.getenv("DISABLE_MQTT", "").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global mqtt_client
    if _mqtt_disabled():
        logger.info("DISABLE_MQTT is set; MQTT subscriber not started")
        yield
        return

    mqtt_client = start_mqtt_subscriber()
    logger.info("MQTT worker started")
    yield
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("MQTT worker stopped")


app = FastAPI(title="IoT Job Starter API", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/devices/{device_id}/latest")
async def get_latest(device_id: str) -> dict[str, object]:
    message = storage.get_latest(device_id)
    if not message:
        raise HTTPException(
            status_code=404, detail=f"Device '{device_id}' has no data"
        )

    return {
        "device_id": message.device_id,
        "payload": message.payload,
    }


@app.get("/devices/{device_id}/recent")
async def get_recent(
    device_id: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, object]:
    items = storage.get_recent(device_id, limit)
    return {
        "device_id": device_id,
        "limit": limit,
        "items": [
            {"device_id": m.device_id, "payload": m.payload} for m in items
        ],
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
