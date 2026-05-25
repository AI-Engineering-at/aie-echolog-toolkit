"""Tests für Tool 9: audit_log_decision."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aie_echolog_toolkit.tools import audit_log_decision


def test_audit_appends_entry(tmp_config):
    out = audit_log_decision(
        decision="Joe-DM W20-B Live-Pilot OK",
        evidence="~/kb/raw/2026-05-25-w20-b-d2-live.md",
        kategorie="geprüft",
        client_id="echo_log-test",
    )
    assert out["entry_id"]
    assert out["entry_hash"]
    assert out["client_id"] == "echo_log-test"
    chain_path = Path(out["chain_path"])
    assert chain_path.exists()
    data = json.loads(chain_path.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 1


def test_audit_chains_entries(tmp_config):
    a = audit_log_decision("Erste Entscheidung", client_id="echo_log-chain")
    b = audit_log_decision("Zweite Entscheidung", client_id="echo_log-chain")
    assert a["entry_hash"] == b["prev_hash"]
    chain_path = Path(b["chain_path"])
    data = json.loads(chain_path.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 2


def test_audit_requires_decision(tmp_config):
    with pytest.raises(ValueError):
        audit_log_decision("")


def test_audit_invalid_kategorie(tmp_config):
    with pytest.raises(ValueError):
        audit_log_decision("Test", kategorie="invalid-kat")


def test_audit_accepts_geprueft_alias(tmp_config):
    out = audit_log_decision("Test", kategorie="geprueft", client_id="alias-client")
    # Hash-Chain or fallback both must succeed
    assert out["entry_id"]
