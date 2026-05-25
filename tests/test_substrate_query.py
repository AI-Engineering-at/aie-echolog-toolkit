"""Tests für Tool 3: substrate_query."""
from __future__ import annotations

import pytest

from aie_echolog_toolkit.tools import substrate_query


def test_substrate_query_finds_match(tmp_config, tmp_kb):
    out = substrate_query("Art. 4")
    assert out["total"] >= 1
    assert any("STATE.md" in h["path"] for h in out["hits"])
    assert out["backend_reachable"] is True


def test_substrate_query_with_scope(tmp_config, tmp_kb):
    out = substrate_query("DSGVO", scope="raw")
    assert out["total"] >= 1
    assert all(h["path"].startswith("raw/") for h in out["hits"])


def test_substrate_query_no_match(tmp_config, tmp_kb):
    out = substrate_query("ZZZ_keine_match_string_xyz")
    assert out["total"] == 0
    assert out["hits"] == []


def test_substrate_query_empty_raises(tmp_config, tmp_kb):
    with pytest.raises(ValueError):
        substrate_query("")


def test_substrate_query_path_escape_blocked(tmp_config, tmp_kb):
    with pytest.raises(ValueError):
        substrate_query("test", scope="../../etc")


def test_substrate_query_missing_kb_root(tmp_config):
    # kb_root existiert nicht (kein tmp_kb-Fixture)
    out = substrate_query("anything")
    assert out["backend_reachable"] is False
    assert out["total"] == 0
