"""Tests für Tool 4: notebook_recall.

W41-ECHO-LOG-FIX (2026-05-26): erweitert um Surrogat-Pfad-Tests (A33).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from aie_echolog_toolkit import tools as tools_mod
from aie_echolog_toolkit.tools import notebook_recall


# ---------------------------------------------------------------------------
# Demo-Pfad (force_demo=True) — synthetische Snippets sind hier ERLAUBT
# weil explizit als is_demo:True markiert.
# ---------------------------------------------------------------------------
def test_notebook_recall_demo_returns_sources(tmp_config):
    out = notebook_recall()
    assert out["is_demo"] is True
    assert out["backend_reachable"] is False
    assert len(out["sources"]) >= 1
    assert out["notebook_id"] == "test-nb-id"


def test_notebook_recall_query_filter(tmp_config):
    out = notebook_recall(query="IDENTITY")
    titles = [s["title"] for s in out["sources"]]
    assert any("IDENTITY" in t for t in titles)


def test_notebook_recall_limit(tmp_config):
    out = notebook_recall(limit=1)
    assert len(out["sources"]) <= 1


def test_notebook_recall_no_match(tmp_config):
    out = notebook_recall(query="zzz-nicht-vorhanden-xyz")
    assert out["sources"] == []


# ---------------------------------------------------------------------------
# Surrogat-Pfad (reachable=True, REST instabil) — W41-ECHO-LOG-FIX
# A33 KEIN-MOCK: keine synthetischen Snippets, nur echte kb-Datei-Suche.
# ---------------------------------------------------------------------------
@pytest.fixture
def reachable_notebook(tmp_config, monkeypatch):
    """Simuliert: notebook_base_url ist erreichbar (REST-Probe ok)."""
    # tmp_config hat force_demo=True; setze auf False für reachable-Pfad-Test.
    tmp_config.force_demo = False
    monkeypatch.setattr(tools_mod, "_http_probe", lambda url, timeout, headers=None: True)
    return tmp_config


def test_notebook_recall_surrogate_finds_kb_match(reachable_notebook):
    """Surrogat-Pfad: kb-Files existieren + Query matched → echte Sources."""
    kb_root = reachable_notebook.kb_root
    (kb_root / "projects").mkdir(parents=True, exist_ok=True)
    (kb_root / "projects" / "echo-log-evolution.md").write_text(
        "# echo-log-evolution\n\n"
        "## §3 — Voice-Pattern Substanz\n"
        "Jede Aussage traegt einen Beleg-Link. Behauptung ohne Quelle = Drift.\n",
        encoding="utf-8",
    )
    out = notebook_recall(query="Beleg-Link")
    assert out["backend_reachable"] is True
    assert out["is_demo"] is False
    assert out["surrogate_path"] is True
    assert len(out["sources"]) >= 1
    assert any("Voice-Pattern" in s["title"] for s in out["sources"])
    # echte Source-Path-Markierung (NICHT synthetisch)
    assert any(s["source_path"].endswith("echo-log-evolution.md") for s in out["sources"])


def test_notebook_recall_surrogate_honest_empty_when_no_match(reachable_notebook):
    """A33: kb existiert + Query matched NICHT → sources: [] (ehrlich, kein Mock)."""
    kb_root = reachable_notebook.kb_root
    (kb_root / "projects").mkdir(parents=True, exist_ok=True)
    (kb_root / "projects" / "echo-log-evolution.md").write_text(
        "# echo-log-evolution\n\n## §1\nNur ein Eintrag.\n",
        encoding="utf-8",
    )
    out = notebook_recall(query="zzz-garantiert-kein-match-xyz")
    assert out["backend_reachable"] is True
    assert out["is_demo"] is False
    assert out["surrogate_path"] is True
    assert out["sources"] == []
    # Garantie: keine synthetischen Demo-Sources eingeschleust
    assert "Sehen vs Vermitteln" not in str(out)
    assert "Burgenland-zentriert" not in str(out)


def test_notebook_recall_surrogate_honest_empty_when_kb_files_missing(reachable_notebook):
    """A33: kb-Files fehlen → sources: [] (ehrlich, kein Demo-Fallback)."""
    # Kein kb/projects/echo-log-evolution.md angelegt.
    out = notebook_recall(query="irgendwas")
    assert out["backend_reachable"] is True
    assert out["is_demo"] is False
    assert out["surrogate_path"] is True
    assert out["sources"] == []


def test_notebook_recall_surrogate_path_marker_explicit(reachable_notebook):
    """Surrogat-Pfad muss explizit als surrogate_path:True markiert sein."""
    out = notebook_recall()
    assert out.get("surrogate_path") is True
    assert "surrogate_files" in out
    assert "echo-log-evolution.md" in str(out["surrogate_files"])
    assert "instabil" in out["note"].lower() or "surrogat" in out["note"].lower()


def test_notebook_recall_unreachable_marks_is_demo(tmp_config, monkeypatch):
    """Backend nicht erreichbar → is_demo:True, _demo_brand_soul_sources OK."""
    tmp_config.force_demo = False
    monkeypatch.setattr(tools_mod, "_http_probe", lambda url, timeout, headers=None: False)
    out = notebook_recall()
    assert out["backend_reachable"] is False
    assert out["is_demo"] is True  # = klare Markierung
    # In diesem Pfad sind Demo-Snippets OK weil is_demo:True
    assert len(out["sources"]) >= 1
    assert "mock-only" in out["note"].lower() or "nicht erreichbar" in out["note"].lower()


def test_notebook_recall_surrogate_limit_respected(reachable_notebook):
    """Surrogat-Pfad respektiert limit-Parameter."""
    kb_root = reachable_notebook.kb_root
    (kb_root / "projects").mkdir(parents=True, exist_ok=True)
    content = "# evo\n\n" + "\n\n".join(
        f"## Section {i}\nKeyword match content {i}.\n" for i in range(10)
    )
    (kb_root / "projects" / "echo-log-evolution.md").write_text(content, encoding="utf-8")
    out = notebook_recall(query="Keyword", limit=3)
    assert len(out["sources"]) <= 3
