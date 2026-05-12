"""
Memory interface for agent state persistence.
Provides a simple key-value store backed by a JSON file, mimicking
the claude-flow memory API (store / retrieve / list).
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Optional

from config import MEMORY_FILE


class MemoryStore:
    _lock = threading.Lock()

    def __init__(self, path: str = MEMORY_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self._write({})

    # ── public API ──────────────────────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._read()
            data[key] = {"value": value, "updated_at": datetime.utcnow().isoformat()}
            self._write(data)

    def retrieve(self, key: str, default: Any = None) -> Any:
        with self._lock:
            data = self._read()
            entry = data.get(key)
            return entry["value"] if entry else default

    def append(self, key: str, item: Any) -> None:
        """Append item to a list stored at key."""
        with self._lock:
            data = self._read()
            existing = data.get(key, {}).get("value", [])
            if not isinstance(existing, list):
                existing = []
            existing.append(item)
            data[key] = {"value": existing, "updated_at": datetime.utcnow().isoformat()}
            self._write(data)

    def list_keys(self) -> list:
        with self._lock:
            return list(self._read().keys())

    def delete(self, key: str) -> None:
        with self._lock:
            data = self._read()
            data.pop(key, None)
            self._write(data)

    def get_updated_at(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._read().get(key)
            return entry["updated_at"] if entry else None

    # ── internal ────────────────────────────────────────────────────────────

    def _read(self) -> dict:
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, data: dict) -> None:
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2, default=str)


# Module-level singleton
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


# Convenience wrappers matching claude-flow CLI semantics
def memory_store(key: str, value: Any) -> None:
    get_store().store(key, value)


def memory_retrieve(key: str, default: Any = None) -> Any:
    return get_store().retrieve(key, default)


def memory_append(key: str, item: Any) -> None:
    get_store().append(key, item)
