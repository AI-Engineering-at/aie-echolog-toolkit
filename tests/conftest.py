"""Shared pytest fixtures."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aie_echolog_toolkit.tools import ToolkitConfig, reset_config, set_config


@pytest.fixture
def tmp_config(tmp_path: Path) -> ToolkitConfig:
    """Frischer ToolkitConfig im tmp-Pfad mit force_demo=True (offline-safe)."""
    cfg = ToolkitConfig(
        kb_root=tmp_path / "kb",
        honcho_base_url="http://offline.invalid",
        honcho_token=None,
        honcho_workspace="test-workspace",
        notebook_base_url="http://offline.invalid",
        notebook_brand_soul_id="test-nb-id",
        vg_bridge_base_url="http://127.0.0.1:1",
        mattermost_url="http://offline.invalid",
        mattermost_token=None,
        joe_dm_channel=None,
        verify_base_url="https://verify.test.invalid",
        hash_chain_dir=tmp_path / "chains",
        force_demo=True,
        http_timeout_s=1.0,
    )
    set_config(cfg)
    yield cfg
    reset_config()
    if (tmp_path / "kb").exists():
        shutil.rmtree(tmp_path / "kb", ignore_errors=True)
    if (tmp_path / "chains").exists():
        shutil.rmtree(tmp_path / "chains", ignore_errors=True)


@pytest.fixture
def tmp_kb(tmp_config: ToolkitConfig) -> Path:
    """Erzeugt eine minimale kb-Struktur unter tmp_config.kb_root."""
    kb_root = tmp_config.kb_root
    kb_root.mkdir(parents=True, exist_ok=True)
    (kb_root / "STATE.md").write_text(
        "# STATE\nDer KMU braucht Klarheit zu Art. 4 EU AI Act in Burgenland.\n",
        encoding="utf-8",
    )
    (kb_root / "raw").mkdir()
    (kb_root / "raw" / "demo.md").write_text(
        "Joe-Test-Beleg DSGVO Art. 22 — Hash-Chain-Verifikation\n",
        encoding="utf-8",
    )
    return kb_root
