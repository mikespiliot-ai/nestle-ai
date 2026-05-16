"""Tests for MemoryStore."""

import os
import tempfile

import pytest

from memory.claude_flow_store import MemoryStore


@pytest.fixture
def store(tmp_path):
    path = str(tmp_path / "test_state.json")
    return MemoryStore(path=path)


class TestMemoryStore:

    def test_store_and_retrieve(self, store):
        store.store("key1", "value1")
        assert store.retrieve("key1") == "value1"

    def test_retrieve_default(self, store):
        assert store.retrieve("nonexistent", default=42) == 42

    def test_retrieve_default_none(self, store):
        assert store.retrieve("missing") is None

    def test_append_creates_list(self, store):
        store.append("mylist", "a")
        assert store.retrieve("mylist") == ["a"]

    def test_append_extends_list(self, store):
        store.append("mylist", "a")
        store.append("mylist", "b")
        assert store.retrieve("mylist") == ["a", "b"]

    def test_store_overwrites(self, store):
        store.store("k", 1)
        store.store("k", 2)
        assert store.retrieve("k") == 2

    def test_delete_existing(self, store):
        store.store("del_me", "x")
        result = store.delete("del_me")
        assert result is True
        assert store.retrieve("del_me") is None

    def test_delete_nonexistent(self, store):
        result = store.delete("not_there")
        assert result is False

    def test_list_keys(self, store):
        store.store("a", 1)
        store.store("b", 2)
        keys = store.list_keys()
        assert "a" in keys
        assert "b" in keys

    def test_get_updated_at(self, store):
        store.store("ts_key", "val")
        ts = store.get_updated_at("ts_key")
        assert ts is not None
        assert "T" in ts  # ISO format

    def test_get_updated_at_missing(self, store):
        assert store.get_updated_at("not_there") is None

    def test_store_complex_value(self, store):
        data = {"a": [1, 2, 3], "b": {"nested": True}}
        store.store("complex", data)
        retrieved = store.retrieve("complex")
        assert retrieved == data

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "persist.json")
        s1 = MemoryStore(path=path)
        s1.store("persistent_key", "persistent_value")

        s2 = MemoryStore(path=path)
        assert s2.retrieve("persistent_key") == "persistent_value"
