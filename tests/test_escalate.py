"""Tests für Tool 8: human_in_loop_escalate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aie_echolog_toolkit.tools import human_in_loop_escalate


def test_escalate_persists_local_in_demo(tmp_config):
    out = human_in_loop_escalate("Konflikt: Voice-Drift in art4-tutor")
    assert out["sent"] is False
    assert out["transport"] == "file_only"
    local = Path(out["local_path"])
    assert local.exists()
    data = json.loads(local.read_text(encoding="utf-8"))
    assert "Voice-Drift" in data["reason"]


def test_escalate_requires_reason(tmp_config):
    with pytest.raises(ValueError):
        human_in_loop_escalate("")


def test_escalate_custom_channel(tmp_config):
    out = human_in_loop_escalate("Test", channel="custom-channel-id")
    data = json.loads(Path(out["local_path"]).read_text(encoding="utf-8"))
    assert data["channel"] == "custom-channel-id"
