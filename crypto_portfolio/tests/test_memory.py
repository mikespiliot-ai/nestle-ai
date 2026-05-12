"""Unit tests for the memory store."""

import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from memory.claude_flow_store import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(path=str(tmp_path / "state.json"))


def test_store_and_retrieve(store):
    store.store("my_key", {"value": 42})
    assert store.retrieve("my_key") == {"value": 42}


def test_retrieve_default(store):
    assert store.retrieve("missing", default="fallback") == "fallback"


def test_append(store):
    store.append("events", {"type": "test"})
    store.append("events", {"type": "test2"})
    events = store.retrieve("events")
    assert len(events) == 2


def test_overwrite(store):
    store.store("x", 1)
    store.store("x", 2)
    assert store.retrieve("x") == 2


def test_delete(store):
    store.store("temp", "value")
    store.delete("temp")
    assert store.retrieve("temp") is None
