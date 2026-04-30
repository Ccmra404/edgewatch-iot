from __future__ import annotations

import json
import logging
import os

import paho.mqtt.client as mqtt

from app.storage import storage

logger = logging.getLogger(__name__)


def _resolve_topic(message_topic: str) -> str | None:
    parts = message_topic.split("/")
    if len(parts) >= 3 and parts[0] == "iot" and parts[1] == "devices":
        return parts[2]
    return None


def start_mqtt_subscriber() -> mqtt.Client:
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", "iot/devices/+/telemetry")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(
        _client: mqtt.Client,
        _userdata: object,
        _flags: dict[str, int],
        reason_code: int,
        _properties: object = None,
    ) -> None:
        if reason_code == 0:
            logger.info("Connected to MQTT: %s:%d", mqtt_host, mqtt_port)
            _client.subscribe(mqtt_topic)
            logger.info("Subscribed topic: %s", mqtt_topic)
        else:
            logger.error("MQTT connect failed. reason_code=%s", reason_code)

    def on_message(
        _client: mqtt.Client,
        _userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        device_id = _resolve_topic(msg.topic)
        if not device_id:
            return

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON payload from topic %s", msg.topic)
            return

        if not isinstance(payload, dict):
            logger.warning("Payload is not JSON object: %s", msg.topic)
            return

        storage.save(device_id, payload)
        logger.info("Saved telemetry for device=%s payload=%s", device_id, payload)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_host, mqtt_port, keepalive=60)
    client.loop_start()
    return client
