"""Tests für Tool 1: voice_check."""
from __future__ import annotations

import pytest

from aie_echolog_toolkit.tools import voice_check


def test_on_brand_text_classified_on_brand(tmp_config):
    text = (
        "Joe, der KMU in Burgenland braucht Klarheit zu Art. 4 EU AI Act. "
        "Ich sehe das Marktversagen und vermittle es als Schulung. "
        "Beleg: ~/kb/raw/2026-05-25-demo.md."
    )
    out = voice_check(text)
    assert out["label"] in {"on_brand", "drift"}  # Heuristik darf nicht off_brand sein
    assert 0.0 <= out["score"] <= 1.0
    assert "dimensions" in out and len(out["dimensions"]) == 7


def test_buzzword_heavy_text_drifts(tmp_config):
    text = (
        "We deliver next-gen, world-class, seamless, AI-powered, "
        "compliance-ready solutions for stakeholders. End-to-end synergy."
    )
    out = voice_check(text)
    assert out["label"] in {"drift", "off_brand"}
    assert out["score"] < 0.6
    assert "rewrite_hint" in out


def test_empty_text_returns_unknown(tmp_config):
    out = voice_check("")
    assert out["label"] == "unknown"
    assert out["score"] == 0.0


def test_voice_check_type_error_for_non_string(tmp_config):
    with pytest.raises(TypeError):
        voice_check(12345)  # type: ignore[arg-type]


def test_sycophancy_marker_detected(tmp_config):
    text = "Absolut! Exzellente Frage. Wir bieten großartige Lösungen für den Kunden."
    out = voice_check(text)
    assert out["label"] in {"drift", "off_brand"}
    assert any("sycophancy" in f or "english" in f or "generic" in f for f in out["findings"])
