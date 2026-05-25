"""Tests für Tool 2: pattern_learn."""
from __future__ import annotations

import json
from pathlib import Path

from aie_echolog_toolkit.tools import pattern_learn


def test_pattern_learn_persists_local(tmp_config):
    text = (
        "Joe, ich sehe das Marktversagen: 78% KMU ohne Compliance-Coach. "
        "Ich vermittle Art. 4 EU AI Act im DACH-Kontext. Beleg: ~/kb/raw/123.md."
    )
    out = pattern_learn(text, source_label="echo_log", append_to_notebook=False)
    assert out["pattern_id"]
    assert out["local_path"]
    local_path = Path(out["local_path"])
    assert local_path.exists()
    data = json.loads(local_path.read_text(encoding="utf-8"))
    assert data["text"] == text
    assert data["source_label"] == "echo_log"
    assert "signals" in data


def test_pattern_learn_voice_score_present(tmp_config):
    out = pattern_learn("Joe in Burgenland: Art. 4 EU AI Act — Beleg raw/9.md", append_to_notebook=False)
    assert "voice_score" in out
    assert "voice_label" in out
    assert 0.0 <= out["voice_score"] <= 1.0


def test_pattern_learn_demo_mode_does_not_call_notebook(tmp_config):
    out = pattern_learn("Test", append_to_notebook=True)
    # force_demo=True via tmp_config → backend never tried.
    assert out["is_demo"] is True
    assert out["notebook_appended"] is False
