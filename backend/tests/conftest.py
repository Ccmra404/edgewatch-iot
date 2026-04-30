"""Pytest: set env before importing the app (storage singleton)."""

from __future__ import annotations

import os

# Force test-friendly settings (override user shell env for deterministic CI/local runs).
os.environ["DISABLE_MQTT"] = "1"
os.environ["STORAGE_BACKEND"] = "memory"
os.environ["API_KEY"] = "test-api-key"
