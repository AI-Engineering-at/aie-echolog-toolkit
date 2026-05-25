"""Tests für Tools 5+6: peer_memory_read + peer_memory_write."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aie_echolog_toolkit.tools import peer_memory_read, peer_memory_write


def test_peer_memory_read_demo(tmp_config):
    out = peer_memory_read("joe", limit=5)
    assert out["is_demo"] is True
    assert out["peer_id"] == "joe"
    assert isinstance(out["items"], list)
    assert out["total"] == len(out["items"])


def test_peer_memory_read_requires_peer_id(tmp_config):
    with pytest.raises(ValueError):
        peer_memory_read("")


def test_peer_memory_write_persists_locally(tmp_config):
    out = peer_memory_write("echo_log", "Test-Eintrag W20-B")
    assert out["is_demo"] is True
    assert out["backend_reachable"] is False
    local_path = Path(out["local_path"])
    assert local_path.exists()
    data = json.loads(local_path.read_text(encoding="utf-8"))
    assert data["content"] == "Test-Eintrag W20-B"
    assert data["peer_id"] == "echo_log"


def test_peer_memory_write_with_metadata(tmp_config):
    out = peer_memory_write("echo_log", "Mit Meta", metadata={"bot": "echo_log", "topic": "test"})
    local_path = Path(out["local_path"])
    data = json.loads(local_path.read_text(encoding="utf-8"))
    assert data["metadata"]["bot"] == "echo_log"


def test_peer_memory_write_requires_content(tmp_config):
    with pytest.raises(ValueError):
        peer_memory_write("joe", "")
