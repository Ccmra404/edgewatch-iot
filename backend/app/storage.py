from __future__ import annotations

import json
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DeviceMessage:
    device_id: str
    payload: dict[str, Any]


class StorageBackend(ABC):
    """Telemetry persistence: latest + bounded recent history per device."""

    @abstractmethod
    def save(self, device_id: str, payload: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_latest(self, device_id: str) -> DeviceMessage | None:
        pass

    @abstractmethod
    def get_recent(self, device_id: str, limit: int) -> list[DeviceMessage]:
        """Return up to `limit` messages, newest first."""
        pass


# Max rows kept per device in memory / default cap for SQLite table pruning
_MAX_HISTORY_PER_DEVICE = int(os.getenv("MAX_TELEMETRY_PER_DEVICE", "1000"))


class InMemoryStorage(StorageBackend):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, DeviceMessage] = {}
        self._history: dict[str, deque[DeviceMessage]] = defaultdict(
            lambda: deque(maxlen=_MAX_HISTORY_PER_DEVICE)
        )

    def save(self, device_id: str, payload: dict[str, Any]) -> None:
        message = DeviceMessage(device_id=device_id, payload=payload)
        with self._lock:
            self._latest[device_id] = message
            self._history[device_id].append(message)

    def get_latest(self, device_id: str) -> DeviceMessage | None:
        with self._lock:
            return self._latest.get(device_id)

    def get_recent(self, device_id: str, limit: int) -> list[DeviceMessage]:
        if limit <= 0:
            return []
        with self._lock:
            dq = self._history.get(device_id)
            if not dq:
                return []
            # deque oldest->newest; return newest first
            tail = list(dq)[-limit:]
            return list(reversed(tail))


class SqliteStorage(StorageBackend):
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS telemetry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at REAL DEFAULT (strftime('%s','now'))
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_telemetry_device_id "
                    "ON telemetry (device_id, id)"
                )
                conn.commit()
            finally:
                conn.close()

    def save(self, device_id: str, payload: dict[str, Any]) -> None:
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO telemetry (device_id, payload_json) VALUES (?, ?)",
                    (device_id, payload_json),
                )
                conn.commit()
                self._prune_locked(conn, device_id)
            finally:
                conn.close()

    def _prune_locked(self, conn: sqlite3.Connection, device_id: str) -> None:
        """Keep at most _MAX_HISTORY_PER_DEVICE rows per device."""
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM telemetry WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        count = int(row["c"]) if row else 0
        excess = count - _MAX_HISTORY_PER_DEVICE
        if excess <= 0:
            return
        conn.execute(
            """
            DELETE FROM telemetry
            WHERE device_id = ?
              AND id IN (
                SELECT id FROM telemetry
                WHERE device_id = ?
                ORDER BY id ASC
                LIMIT ?
              )
            """,
            (device_id, device_id, excess),
        )
        conn.commit()

    def get_latest(self, device_id: str) -> DeviceMessage | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT device_id, payload_json
                    FROM telemetry
                    WHERE device_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (device_id,),
                ).fetchone()
            finally:
                conn.close()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        return DeviceMessage(device_id=row["device_id"], payload=payload)

    def get_recent(self, device_id: str, limit: int) -> list[DeviceMessage]:
        if limit <= 0:
            return []
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT device_id, payload_json
                    FROM telemetry
                    WHERE device_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (device_id, limit),
                ).fetchall()
            finally:
                conn.close()
        out: list[DeviceMessage] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            out.append(DeviceMessage(device_id=row["device_id"], payload=payload))
        return out


def _create_storage() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "memory").strip().lower()
    if backend == "sqlite":
        path = os.getenv("SQLITE_PATH", "/app/data/telemetry.db")
        return SqliteStorage(path)
    if backend != "memory":
        raise ValueError(
            f"Unknown STORAGE_BACKEND={backend!r}; use 'memory' or 'sqlite'."
        )
    return InMemoryStorage()


storage: StorageBackend = _create_storage()
