"""Tests für Tool 7: system_status_summary."""
from __future__ import annotations

from aie_echolog_toolkit.tools import system_status_summary


def test_system_status_summary_force_demo(tmp_config):
    out = system_status_summary()
    assert out["is_demo"] is True
    assert out["summary"]["reachable_count"] == 0
    assert out["summary"]["total"] == len(out["probes"])
    names = {p["name"] for p in out["probes"]}
    assert {"vg_bridge", "honcho", "notebook", "mattermost", "verify_surface"} == names


def test_system_status_includes_ts(tmp_config):
    out = system_status_summary()
    assert "ts_utc" in out
    assert "T" in out["ts_utc"]
