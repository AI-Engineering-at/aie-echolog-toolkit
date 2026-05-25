"""Tests für Tool 10: verify_url_build."""
from __future__ import annotations

import urllib.parse

import pytest

from aie_echolog_toolkit.tools import verify_url_build


def test_verify_url_basic(tmp_config):
    payload = {
        "client_id": "echo_log",
        "entry_id": "abc123",
        "entry_hash": "deadbeef" * 8,
    }
    out = verify_url_build(payload)
    assert out["url"].startswith("https://verify.test.invalid/v?")
    parsed = urllib.parse.urlparse(out["url"])
    params = urllib.parse.parse_qs(parsed.query)
    assert params["c"] == ["echo_log"]
    assert params["e"] == ["abc123"]
    assert params["h"] == ["deadbeef" * 8]
    assert "canonical_hash" in out


def test_verify_url_with_proof(tmp_config):
    payload = {
        "client_id": "kunde-a",
        "entry_id": "e-1",
        "entry_hash": "h-1",
        "proof_b64": "AAAA",
    }
    out = verify_url_build(payload)
    assert "p=AAAA" in out["url"]


def test_verify_url_missing_keys(tmp_config):
    with pytest.raises(ValueError):
        verify_url_build({"client_id": "x"})


def test_verify_url_wrong_type(tmp_config):
    with pytest.raises(TypeError):
        verify_url_build("not-a-dict")  # type: ignore[arg-type]


def test_canonical_hash_deterministic(tmp_config):
    p = {"client_id": "c", "entry_id": "e", "entry_hash": "h"}
    a = verify_url_build(p)["canonical_hash"]
    b = verify_url_build(p)["canonical_hash"]
    assert a == b
