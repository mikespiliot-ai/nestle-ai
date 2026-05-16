"""Thread-safe JSON-backed key-value memory store."""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, List, Optional

from config import MEMORY_FILE


class MemoryStore:
    """Persistent, thread-safe key-value store backed by a JSON file."""

    def __init__(self, path: str = MEMORY_FILE):
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self._write({})

    # ── Internal helpers ────────────────────────────────────────────────────

    def _read(self) -> dict:
        try:
            with open(self._path, "r") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict) -> None:
        with open(self._path, "w") as fh:
            json.dump(data, fh, indent=2, default=str)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Public API ──────────────────────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        """Store *value* under *key*, overwriting any previous value."""
        with self._lock:
            data = self._read()
            data[key] = {"value": value, "updated_at": self._now()}
            self._write(data)

    def retrieve(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if not present."""
        with self._lock:
            data = self._read()
            if key in data:
                return data[key]["value"]
            return default

    def append(self, key: str, item: Any) -> None:
        """Append *item* to the list stored at *key* (creates list if needed)."""
        with self._lock:
            data = self._read()
            if key in data and isinstance(data[key]["value"], list):
                data[key]["value"].append(item)
            else:
                data[key] = {"value": [item], "updated_at": self._now()}
            data[key]["updated_at"] = self._now()
            self._write(data)

    def list_keys(self) -> List[str]:
        """Return all keys currently stored."""
        with self._lock:
            return list(self._read().keys())

    def delete(self, key: str) -> bool:
        """Delete *key*. Returns True if the key existed."""
        with self._lock:
            data = self._read()
            if key in data:
                del data[key]
                self._write(data)
                return True
            return False

    def get_updated_at(self, key: str) -> Optional[str]:
        """Return the ISO-8601 timestamp of the last update for *key*."""
        with self._lock:
            data = self._read()
            if key in data:
                return data[key].get("updated_at")
            return None


# ── Module-level singleton ──────────────────────────────────────────────────

_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


# ── Convenience wrappers ────────────────────────────────────────────────────

def memory_store(key: str, value: Any) -> None:
    get_store().store(key, value)


def memory_retrieve(key: str, default: Any = None) -> Any:
    return get_store().retrieve(key, default)


def memory_append(key: str, item: Any) -> None:
    get_store().append(key, item)
