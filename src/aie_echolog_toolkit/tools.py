"""Toolset für echo_log-Persona — 10 Tools die der FastMCP-Server registriert.

Cross-Integration:
  1. aie-kb-reader      — substrate_query
  2. aie-honcho-sync    — peer_memory_read / peer_memory_write
  3. aie-hash-chain     — audit_log_decision (via canonical-hash-recompute)
  4. aie-verify         — verify_url_build (Surface-URL-Konstruktion)
  5. aie-echo-bridge    — human_in_loop_escalate (MM-DM Joe)
  6. aie-vg-mcp-bridge  — system_status_summary (VG-Bridge-Probe)

Anti-Slop-Regeln (Anlass M40):
  - Wenn Backend nicht erreichbar → `is_demo: True` + `backend_reachable: False`
    + `note: "mock-only — Hermes/echo_log nicht erreichbar"` ist Pflicht.
  - Keine Behauptung „verifiziert" wenn nur Mock-Path durchlaufen wurde.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .personality_helpers import extract_pattern_signals, voice_classify


# --------------------------------------------------------------------------- #
# Config — env-driven, never hardcoded                                        #
# --------------------------------------------------------------------------- #
@dataclass
class ToolkitConfig:
    """Toolkit-Konfiguration via ENV — alle Endpoints konfigurierbar."""

    # kb-reader: Mac-lokaler stdio-MCP (in-process call via Python)
    kb_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AIE_KB_ROOT", str(Path.home() / "kb"))
        )
    )

    # Honcho — Cross-Surface-Memory
    honcho_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "HONCHO_BASE_URL", "http://10.40.10.82:8055"
        ).rstrip("/")
    )
    honcho_token: str | None = field(
        default_factory=lambda: os.environ.get("HONCHO_TOKEN") or None
    )
    honcho_workspace: str = field(
        default_factory=lambda: os.environ.get(
            "HONCHO_WORKSPACE", "ai-engineering"
        )
    )

    # Open-Notebook — Brand-Soul (49 Sources + 11 Evolution-Notes)
    notebook_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "OPEN_NOTEBOOK_URL", "http://10.40.10.82:5055"
        ).rstrip("/")
    )
    notebook_brand_soul_id: str = field(
        default_factory=lambda: os.environ.get(
            "BRAND_SOUL_NOTEBOOK_ID", "jkbjq4ndpqmo5nxkfhit"
        )
    )

    # VG-MCP-Bridge — Voice-Gateway Persona-Reload + Probe
    vg_bridge_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "VG_BRIDGE_URL", "http://127.0.0.1:8765"
        ).rstrip("/")
    )

    # Echo-Bridge — Mattermost-DM Joe
    mattermost_url: str = field(
        default_factory=lambda: os.environ.get(
            "MATTERMOST_URL", "https://mm.ai-engineering.at"
        ).rstrip("/")
    )
    mattermost_token: str | None = field(
        default_factory=lambda: os.environ.get("MATTERMOST_TOKEN") or None
    )
    joe_dm_channel: str | None = field(
        default_factory=lambda: os.environ.get("JOE_DM_CHANNEL") or None
    )

    # Verify-Surface — verify.ai-engineering.at
    verify_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "AIE_VERIFY_URL", "https://verify.ai-engineering.at"
        ).rstrip("/")
    )

    # Hash-Chain — wo Chain-Files persistiert werden (Mac-lokal)
    hash_chain_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "AIE_HASH_CHAIN_DIR",
                str(Path.home() / ".aie" / "echolog-chains"),
            )
        )
    )

    # Demo-Mode: erzwingt Mock-only Pfad (für Tests + offline-Smoke)
    force_demo: bool = field(
        default_factory=lambda: os.environ.get("AIE_ECHOLOG_DEMO", "") == "1"
    )

    # HTTP-Timeouts (Mac-lokal kurz halten)
    http_timeout_s: float = 5.0


# Singleton (kann in Tests via set_config überschrieben werden).
_CONFIG: ToolkitConfig | None = None


def get_config() -> ToolkitConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = ToolkitConfig()
    return _CONFIG


def set_config(cfg: ToolkitConfig) -> None:
    """Erlaubt Tests den Config-Singleton zu overriden."""
    global _CONFIG
    _CONFIG = cfg


def reset_config() -> None:
    """Reset Singleton (Test-Cleanup)."""
    global _CONFIG
    _CONFIG = None


# --------------------------------------------------------------------------- #
# Helper: Probe-Backends                                                      #
# --------------------------------------------------------------------------- #
def _http_probe(url: str, timeout: float, headers: dict | None = None) -> bool:
    """Probe ob URL erreichbar (status<500). Bei Exception → False."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers or {})
        return resp.status_code < 500
    except (httpx.HTTPError, OSError):
        return False


def _post_json(
    url: str, body: dict, timeout: float, headers: dict | None = None
) -> tuple[bool, dict | str]:
    """POST JSON, return (ok, json_or_error)."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=body, headers=headers or {})
    except (httpx.HTTPError, OSError) as e:
        return False, f"http-error: {e}"
    if resp.status_code >= 400:
        return False, f"http-{resp.status_code}: {resp.text[:200]}"
    try:
        return True, resp.json()
    except ValueError as e:
        return False, f"json-decode: {e}"


# --------------------------------------------------------------------------- #
# Tool 1: voice_check                                                         #
# --------------------------------------------------------------------------- #
def voice_check(text: str) -> dict:
    """Prüft Text gegen brand-voice-watcher 7-Dimensionen-Profil (Mac-lokal).

    Args:
        text: Bot-Output (Mattermost-Post, Hub-Content, etc.) der vor
              Publish geprüft werden soll.

    Returns:
        {
          label: "on_brand" | "drift" | "off_brand" | "unknown",
          score: 0.0..1.0,
          dimensions: {tonalitaet, anrede, ...},
          findings: [str, ...],
          rewrite_hint: str  # nur bei label != "on_brand"
        }
    """
    if not isinstance(text, str):
        raise TypeError("voice_check: text must be str")

    vs = voice_classify(text)
    out = vs.to_dict()

    if vs.label != "on_brand":
        # Generiere kurzen Rewrite-Hinweis basierend auf Findings.
        hints: list[str] = []
        if any("english-buzzword" in f for f in vs.findings):
            hints.append("Englische Buzzwords durch deutsche Konkretisierung ersetzen.")
        if any("generic-anrede" in f for f in vs.findings):
            hints.append("Konkrete Anrede statt 'Wir/Kunde/User' — z.B. 'Joe', 'der KMU', 'die Schulung'.")
        if any("generic-compliance" in f for f in vs.findings):
            hints.append("Compliance-Anker konkret: 'Art. 4 EU AI Act' / 'DSGVO Art. 22' statt 'compliance-ready'.")
        if any("region-anchor-abstrakt" in f for f in vs.findings):
            hints.append("Regional konkret: 'Burgenland/DACH/Österreich' statt 'global/weltweit'.")
        if any("wir-anbieten" in f for f in vs.findings):
            hints.append("Selbstpositionierung: 'Ich sehe X, vermittele Y' (D1-D5) statt 'Wir bieten Z'.")
        if not any("evidence-marker" in f for f in vs.findings):
            hints.append("Beleg/Stand/Quelle/raw-Link mitschicken (sonst Substanz-Drift).")
        out["rewrite_hint"] = " ".join(hints) or "Voice-Profil drift — siehe Dimensionen + findings."
    return out


# --------------------------------------------------------------------------- #
# Tool 2: pattern_learn                                                       #
# --------------------------------------------------------------------------- #
def pattern_learn(
    success_pattern: str,
    source_label: str = "echo_log",
    append_to_notebook: bool = True,
) -> dict:
    """Lernt einen erfolgreichen Voice-Pattern (operationalisiert voice-pattern-keeper).

    Args:
        success_pattern: On-Brand-Output, der als Pattern-Beispiel
                         persistiert werden soll.
        source_label: Bot-ID die den Pattern erzeugt hat (echo_log/Hermes/...).
        append_to_notebook: Wenn True und Notebook erreichbar → an Evolution-Notes
                            anhängen. Wenn False → nur lokal speichern + return.

    Returns:
        {
          pattern_id: uuid-str,
          signals: {...extract_pattern_signals output...},
          voice_score: float,
          notebook_appended: bool,
          backend_reachable: bool,
          is_demo: bool,
          local_path: str  # immer geschrieben (Audit-Pflicht)
        }
    """
    cfg = get_config()
    pattern_id = uuid.uuid4().hex
    signals = extract_pattern_signals(success_pattern)
    vs = voice_classify(success_pattern)

    # Pflicht-Local-Write zuerst (Audit-Anker, auch wenn Notebook down).
    local_dir = cfg.hash_chain_dir / "patterns"
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / f"pattern-{pattern_id}.json"
    payload = {
        "pattern_id": pattern_id,
        "source_label": source_label,
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "text": success_pattern,
        "signals": signals,
        "voice_label": vs.label,
        "voice_score": round(vs.score, 3),
    }
    local_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    notebook_appended = False
    backend_reachable = False
    is_demo = cfg.force_demo

    if append_to_notebook and not is_demo:
        # Probe Notebook-Backend
        backend_reachable = _http_probe(
            f"{cfg.notebook_base_url}/api/health",
            cfg.http_timeout_s,
        )
        if backend_reachable:
            # Open-Notebook hat eine REST-API für note-append; ohne live-Auth-Test
            # markieren wir hier als „skipped" und überlassen den Live-Append
            # dem voice-pattern-keeper-Skill (LLM-gesteuert).
            # Im MCP-Tool-Layer dokumentieren wir nur die Bereitschaft.
            notebook_appended = False  # ehrlich: kein blind-fire-and-forget

    return {
        "pattern_id": pattern_id,
        "signals": signals,
        "voice_label": vs.label,
        "voice_score": round(vs.score, 3),
        "notebook_appended": notebook_appended,
        "backend_reachable": backend_reachable,
        "is_demo": is_demo,
        "local_path": str(local_path),
        "note": (
            "Pattern persistiert lokal; Notebook-Append delegiert an "
            "voice-pattern-keeper-Skill (LLM-gesteuert)."
            if backend_reachable and not is_demo
            else "Pattern persistiert lokal; Notebook nicht erreichbar — Append wird beim nächsten Online-Lauf vom voice-pattern-keeper nachgezogen."
        ),
    }


# --------------------------------------------------------------------------- #
# Tool 3: substrate_query — via aie-kb-reader Search                          #
# --------------------------------------------------------------------------- #
def substrate_query(query: str, scope: str = "") -> dict:
    """kb-Substrat-Suche via in-process aie-kb-reader-Search.

    Args:
        query: Suchbegriff (literal, case-insensitive).
        scope: Pfad-Präfix innerhalb ~/kb/ ("" = ganz kb).

    Returns:
        {
          hits: [{path, line_number, snippet}, ...],
          total: int,
          kb_root: str,
          backend_reachable: bool,
        }
    """
    cfg = get_config()
    if not isinstance(query, str) or not query.strip():
        raise ValueError("substrate_query: query muss non-empty string sein")

    kb_root = cfg.kb_root
    if not kb_root.exists():
        return {
            "hits": [],
            "total": 0,
            "kb_root": str(kb_root),
            "backend_reachable": False,
            "error": "kb-root nicht gefunden",
        }

    # Inline-Search (lightweight, gleich-Algo wie aie-kb-reader.search_kb_impl)
    q = query.lower()
    hits: list[dict] = []
    max_hits = 50
    scope_root = kb_root
    if scope:
        # Pfad-Eskalations-Schutz
        candidate = (kb_root / scope).resolve()
        if not str(candidate).startswith(str(kb_root.resolve())):
            raise ValueError("substrate_query: scope-path-escape verboten")
        scope_root = candidate
    if not scope_root.exists() or not scope_root.is_dir():
        return {
            "hits": [],
            "total": 0,
            "kb_root": str(kb_root),
            "backend_reachable": True,
            "error": f"scope nicht gefunden: {scope!r}",
        }

    for p in scope_root.rglob("*"):
        if len(hits) >= max_hits:
            break
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".md", ".txt", ".yaml", ".yml", ".json"}:
            continue
        try:
            with p.open("r", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, start=1):
                    if q in line.lower():
                        hits.append({
                            "path": str(p.relative_to(kb_root)),
                            "line_number": i,
                            "snippet": line.strip()[:200],
                        })
                        if len(hits) >= max_hits:
                            break
        except OSError:
            continue

    return {
        "hits": hits,
        "total": len(hits),
        "kb_root": str(kb_root),
        "backend_reachable": True,
        "scope": scope or "",
    }


# --------------------------------------------------------------------------- #
# Tool 4: notebook_recall                                                     #
# --------------------------------------------------------------------------- #
def notebook_recall(
    notebook_id: str | None = None,
    query: str = "",
    limit: int = 10,
) -> dict:
    """Holt Brand-Soul-Sources / Evolution-Notes aus Open-Notebook.

    Args:
        notebook_id: Notebook-ID (default = BRAND_SOUL_NOTEBOOK_ID).
        query: Suchbegriff für Source-Filter (case-insensitive substring).
        limit: Max. Sources.

    Returns:
        {
          notebook_id: str,
          sources: [{title, content_preview, source_id}, ...],
          backend_reachable: bool,
          is_demo: bool,
          note: str
        }
    """
    cfg = get_config()
    nb_id = notebook_id or cfg.notebook_brand_soul_id

    if cfg.force_demo:
        return {
            "notebook_id": nb_id,
            "sources": _demo_brand_soul_sources(query, limit),
            "backend_reachable": False,
            "is_demo": True,
            "note": "demo-mode: synthetische Brand-Soul-Snippets (force_demo=1)",
        }

    reachable = _http_probe(
        f"{cfg.notebook_base_url}/api/health",
        cfg.http_timeout_s,
    )
    if not reachable:
        return {
            "notebook_id": nb_id,
            "sources": _demo_brand_soul_sources(query, limit),
            "backend_reachable": False,
            "is_demo": True,
            "note": "mock-only — Open-Notebook nicht erreichbar; Demo-Snippets aus kb/raw verwendet",
        }

    # Live-Backend: Open-Notebook v0.x hat aktuell KEINE stabile REST-Suche.
    # A33 KEIN-MOCK: KEINE synthetischen Brand-Soul-Snippets im reachable-Pfad.
    # Stattdessen: ECHTE Surrogat-Suche in kb/projects/echo-log-evolution.md
    # + kb/company/IDENTITY.md + kb/company/NORDSTERN.md. Wenn diese Files
    # fehlen ODER kein Match: ehrliche `sources: []` + Hinweis-Note.
    # W41-ECHO-LOG-FIX (raw/2026-05-26-welle-41-echo-log-fix.md): Surrogat-
    # Pfad explizit dokumentiert + getestet.
    surrogate_sources = _surrogate_search_kb(cfg.kb_root, query, limit)
    return {
        "notebook_id": nb_id,
        "sources": surrogate_sources,
        "surrogate_path": True,
        "surrogate_files": [
            "projects/echo-log-evolution.md",
            "company/IDENTITY.md",
            "company/NORDSTERN.md",
        ],
        "backend_reachable": True,
        "is_demo": False,
        "note": (
            "Notebook erreichbar; REST-Search-API instabil → ECHTE Surrogat-"
            "Suche in kb/projects/echo-log-evolution.md + kb/company/*.md. "
            "Keine synthetischen Snippets (A33). Wenn sources:[] → kb-Files "
            "fehlen oder kein Match — kein Mock-Fallback."
        ),
    }


def _surrogate_search_kb(kb_root: Path, query: str, limit: int) -> list[dict]:
    """ECHTE Surrogat-Suche im kb-Substrat (A33 KEIN-MOCK).

    Liest die kanonischen Brand-Soul-Spiegel-Files (echo-log-evolution.md,
    IDENTITY.md, NORDSTERN.md) und gibt Markdown-Sections zurück, die den
    Query (case-insensitive substring) treffen. Wenn kb-Files fehlen ODER
    kein Match: leere Liste (ehrlich), KEIN Demo-Fallback.

    Args:
        kb_root: ~/kb root path.
        query: case-insensitive substring filter ("" = top-N sections).
        limit: max sources to return (1..50).

    Returns:
        Liste von {title, content_preview, source_id, source_path}.
    """
    surrogate_files = [
        ("projects/echo-log-evolution.md", "echolog-evo"),
        ("company/IDENTITY.md", "identity"),
        ("company/NORDSTERN.md", "nordstern"),
    ]
    out: list[dict] = []
    bounded_limit = max(1, min(limit, 50))
    q = query.lower().strip() if query else ""

    for rel_path, prefix in surrogate_files:
        if len(out) >= bounded_limit:
            break
        p = kb_root / rel_path
        if not p.exists() or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Sections by markdown headers (## or ###)
        sections = _split_md_sections(text)
        for idx, (heading, body) in enumerate(sections):
            if len(out) >= bounded_limit:
                break
            blob = (heading + "\n" + body).lower()
            if q and q not in blob:
                continue
            preview = body.strip().splitlines()
            preview_text = " ".join(line.strip() for line in preview if line.strip())[:280]
            out.append({
                "title": heading.strip("# ").strip() or rel_path,
                "content_preview": preview_text,
                "source_id": f"{prefix}-{idx}",
                "source_path": rel_path,
            })
    return out


def _split_md_sections(text: str) -> list[tuple[str, str]]:
    """Splittet Markdown-Text in (heading, body)-Paare bei ##/### Headers.

    Erste Section (vor erstem ##) wird ignoriert. Wenn keine ##-Headers
    vorhanden: gesamter Text als eine ('', text)-Section.
    """
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## ") or line.startswith("### "):
            if current_heading or current_body:
                sections.append((current_heading, current_body))
            current_heading = line
            current_body = []
        else:
            current_body.append(line)
    if current_heading or current_body:
        sections.append((current_heading, current_body))
    if not sections:
        return [("", text)]
    # Filter erste leere Pre-Heading-Section weg falls Heading-leer
    result = [(h, "\n".join(b)) for h, b in sections if h or b]
    return result or [("", text)]


def _demo_brand_soul_sources(query: str, limit: int) -> list[dict]:
    """Synthetische Brand-Soul-Snippets — NUR fuer force_demo / unreachable-Pfad.

    A33-Konformitaet (W41-ECHO-LOG-FIX): Diese Funktion wird ausschliesslich
    in zwei Faellen aufgerufen:
      1. `force_demo=True` (Test-Setup, explizit demo)
      2. `backend_reachable=False` (Open-Notebook nicht erreichbar) — als
         Demo-Marker (`is_demo=True`) damit der Caller klar weiss: keine
         echten Daten.

    Im **reachable-Pfad** (Backend lebt, REST-Suche instabil) wird stattdessen
    `_surrogate_search_kb()` mit echter kb-Datei-Suche verwendet — keine
    synthetischen Snippets, ehrlich `sources: []` wenn kein Match.

    Spiegelt typische echo_log-Voice-Pattern aus
    `~/kb/projects/echo-log-evolution.md` + `~/kb/company/IDENTITY.md`.
    """
    seed = [
        {
            "title": "IDENTITY §1a — Sehen vs Vermitteln",
            "content_preview": (
                "Ich sehe das Marktversagen direkt; ich vermittle es als "
                "verständliches Bauteil. Sehen = D1-D5 (Substrat-Lesung); "
                "Vermitteln = Schulung + Hub-Content."
            ),
            "source_id": "identity-1a",
        },
        {
            "title": "NORDSTERN §8a — DACH-konkret",
            "content_preview": (
                "Burgenland-zentriert, nicht generisch europäisch. "
                "Der KMU vor Ort hat Namen, der EU-AI-Act hat einen Artikel."
            ),
            "source_id": "nordstern-8a",
        },
        {
            "title": "echo-log-evolution §3 — Voice-Pattern Substanz",
            "content_preview": (
                "Jede Aussage trägt einen Beleg-Link (raw/<N>, M<n>, "
                "DEC-<n>, GAP-<n>). Behauptung ohne Quelle = Drift."
            ),
            "source_id": "echolog-3",
        },
        {
            "title": "raw/g1-Selbst-Audit — Anti-Sycophancy",
            "content_preview": (
                "Kein 'absolut', kein 'exzellente Frage', kein "
                "'großartige Idee'. Direkt, präzise, deutsch."
            ),
            "source_id": "raw-g1",
        },
    ]
    if query:
        q = query.lower()
        seed = [s for s in seed if q in s["title"].lower() or q in s["content_preview"].lower()]
    return seed[: max(1, min(limit, 50))]


# --------------------------------------------------------------------------- #
# Tool 5+6: peer_memory_read / peer_memory_write (Honcho)                     #
# --------------------------------------------------------------------------- #
def peer_memory_read(
    peer_id: str,
    since: str | None = None,
    limit: int = 50,
) -> dict:
    """Liest die letzten N Conclusions des Peers aus Honcho-Workspace.

    Args:
        peer_id: Honcho-Peer-ID (joe / echo_log / hermes / ...).
        since: Optional ISO-Datum (clientseitiges Filter, falls Honcho liefert).
        limit: Max. Entries.

    Returns:
        {items: [...], total: int, workspace: str, peer_id: str,
         backend_reachable: bool, is_demo: bool}
    """
    cfg = get_config()
    if not peer_id or not isinstance(peer_id, str):
        raise ValueError("peer_memory_read: peer_id required")

    is_demo = cfg.force_demo
    if is_demo:
        items = _demo_peer_memory(peer_id, limit)
        return {
            "items": items,
            "total": len(items),
            "workspace": cfg.honcho_workspace,
            "peer_id": peer_id,
            "backend_reachable": False,
            "is_demo": True,
            "note": "demo-mode",
        }

    body = {
        "filters": {"observer_id": peer_id},
        "page": 1,
        "size": max(1, min(limit, 200)),
    }
    headers = {}
    if cfg.honcho_token:
        headers["Authorization"] = f"Bearer {cfg.honcho_token}"
    url = (
        f"{cfg.honcho_base_url}/v3/workspaces/"
        f"{urllib.parse.quote(cfg.honcho_workspace)}/conclusions/list"
    )
    ok, data = _post_json(url, body, cfg.http_timeout_s, headers)
    if not ok:
        items = _demo_peer_memory(peer_id, limit)
        return {
            "items": items,
            "total": len(items),
            "workspace": cfg.honcho_workspace,
            "peer_id": peer_id,
            "backend_reachable": False,
            "is_demo": True,
            "note": f"mock-only — Honcho nicht erreichbar ({data})",
        }
    assert isinstance(data, dict)
    items = list(data.get("items", []))
    if since:
        items = [it for it in items if (it.get("created_at") or "") >= since]
    return {
        "items": items,
        "total": len(items),
        "workspace": cfg.honcho_workspace,
        "peer_id": peer_id,
        "backend_reachable": True,
        "is_demo": False,
    }


def peer_memory_write(
    peer_id: str,
    content: str,
    metadata: dict | None = None,
) -> dict:
    """Schreibt eine neue Conclusion in den Honcho-Workspace.

    Args:
        peer_id: Honcho-Peer-ID.
        content: Memory-Eintrag (string).
        metadata: Optional dict (bot_id, source_label, etc.).

    Returns:
        {entry_id: str, backend_reachable: bool, is_demo: bool, ...}
    """
    cfg = get_config()
    if not peer_id or not isinstance(peer_id, str):
        raise ValueError("peer_memory_write: peer_id required")
    if not content or not isinstance(content, str):
        raise ValueError("peer_memory_write: content required")

    is_demo = cfg.force_demo
    entry_id = uuid.uuid4().hex

    # Pflicht-Local-Mirror: Schreibe Memory-Entry IMMER auch in lokale Datei
    # (Audit-Pflicht — auch wenn Honcho-Backend dann ausfällt).
    local_dir = cfg.hash_chain_dir / "peer-memory"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": entry_id,
        "peer_id": peer_id,
        "content": content,
        "metadata": metadata or {},
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workspace": cfg.honcho_workspace,
    }
    local_path = local_dir / f"mem-{entry_id}.json"
    local_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if is_demo:
        return {
            "entry_id": entry_id,
            "backend_reachable": False,
            "is_demo": True,
            "local_path": str(local_path),
            "note": "demo-mode: Eintrag nur lokal",
        }

    body: dict[str, Any] = {
        "content": content,
        "observer_id": peer_id,
        "observed_id": peer_id,
    }
    if metadata:
        body["metadata"] = metadata
    headers = {}
    if cfg.honcho_token:
        headers["Authorization"] = f"Bearer {cfg.honcho_token}"
    url = (
        f"{cfg.honcho_base_url}/v3/workspaces/"
        f"{urllib.parse.quote(cfg.honcho_workspace)}/conclusions"
    )
    ok, data = _post_json(url, body, cfg.http_timeout_s, headers)
    if not ok:
        return {
            "entry_id": entry_id,
            "backend_reachable": False,
            "is_demo": True,
            "local_path": str(local_path),
            "note": f"mock-only — Honcho nicht erreichbar ({data})",
        }
    return {
        "entry_id": entry_id,
        "backend_reachable": True,
        "is_demo": False,
        "local_path": str(local_path),
        "honcho_response": data,
    }


def _demo_peer_memory(peer_id: str, limit: int) -> list[dict]:
    base = [
        {
            "id": f"demo-{peer_id}-1",
            "content": f"[{peer_id}] Joe-DM letzter Stand: Welle-20 D2 läuft.",
            "observer_id": peer_id,
            "observed_id": peer_id,
            "created_at": "2026-05-25T05:00:00Z",
            "metadata": {"demo": True},
        },
        {
            "id": f"demo-{peer_id}-2",
            "content": f"[{peer_id}] kb/STATE.md zuletzt 2026-05-25 03:35 aktualisiert.",
            "observer_id": peer_id,
            "observed_id": peer_id,
            "created_at": "2026-05-25T04:30:00Z",
            "metadata": {"demo": True},
        },
    ]
    return base[: max(1, min(limit, len(base)))]


# --------------------------------------------------------------------------- #
# Tool 7: system_status_summary                                               #
# --------------------------------------------------------------------------- #
def system_status_summary() -> dict:
    """Composite-Status der wichtigsten echo_log-Surfaces.

    Probes (alle parallel über serielle httpx-Calls, jeweils kurzer Timeout):
      - VG-Bridge (Mac-lokal)
      - Honcho (.82)
      - Open-Notebook (.82)
      - Mattermost (mm.ai-engineering.at)

    Returns:
        {
          probes: [{name, url, reachable, latency_ms}, ...],
          summary: {reachable_count, total},
          ts_utc: str
        }
    """
    cfg = get_config()
    probes: list[dict] = []

    targets = [
        ("vg_bridge", f"{cfg.vg_bridge_base_url}/health"),
        ("honcho", f"{cfg.honcho_base_url}/v3/workspaces/list"),
        ("notebook", f"{cfg.notebook_base_url}/api/health"),
        ("mattermost", f"{cfg.mattermost_url}/api/v4/system/ping"),
        ("verify_surface", f"{cfg.verify_base_url}/"),
    ]

    for name, url in targets:
        t0 = time.perf_counter()
        if cfg.force_demo:
            probes.append({
                "name": name, "url": url, "reachable": False,
                "latency_ms": 0, "note": "force_demo",
            })
            continue
        try:
            with httpx.Client(timeout=cfg.http_timeout_s) as client:
                # GET ist generisch; manche Endpoints brauchen POST,
                # für Status-Smoke reicht „ist HTTP-Server da?".
                resp = client.get(url)
            reachable = resp.status_code < 500
            note = f"http-{resp.status_code}"
        except (httpx.HTTPError, OSError) as e:
            reachable = False
            note = f"unreachable: {type(e).__name__}"
        dt_ms = int((time.perf_counter() - t0) * 1000)
        probes.append({
            "name": name,
            "url": url,
            "reachable": reachable,
            "latency_ms": dt_ms,
            "note": note,
        })

    reachable_count = sum(1 for p in probes if p["reachable"])
    return {
        "probes": probes,
        "summary": {
            "reachable_count": reachable_count,
            "total": len(probes),
        },
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "is_demo": cfg.force_demo,
    }


# --------------------------------------------------------------------------- #
# Tool 8: human_in_loop_escalate (Joe-DM via Mattermost)                      #
# --------------------------------------------------------------------------- #
def human_in_loop_escalate(reason: str, channel: str | None = None) -> dict:
    """Eskaliert eine Entscheidung an Joe via Mattermost-DM.

    Args:
        reason: Klartext warum eskaliert wird (Pflicht).
        channel: Optional MM-Channel-ID; default = JOE_DM_CHANNEL.

    Returns:
        {escalation_id: str, sent: bool, transport: str, backend_reachable: bool,
         local_path: str (immer)}.
    """
    cfg = get_config()
    if not reason or not isinstance(reason, str):
        raise ValueError("human_in_loop_escalate: reason required")
    esc_id = uuid.uuid4().hex
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    target_channel = channel or cfg.joe_dm_channel

    # Pflicht-Local-Mirror (Audit-Anker auch wenn MM down)
    local_dir = cfg.hash_chain_dir / "escalations"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": esc_id,
        "reason": reason,
        "ts_utc": ts,
        "channel": target_channel,
    }
    local_path = local_dir / f"esc-{esc_id}.json"
    local_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if cfg.force_demo or not cfg.mattermost_token or not target_channel:
        return {
            "escalation_id": esc_id,
            "sent": False,
            "transport": "file_only",
            "backend_reachable": False,
            "is_demo": cfg.force_demo,
            "local_path": str(local_path),
            "note": (
                "demo-mode" if cfg.force_demo else
                "mock-only — MATTERMOST_TOKEN oder JOE_DM_CHANNEL fehlt"
            ),
        }

    url = f"{cfg.mattermost_url}/api/v4/posts"
    body = {
        "channel_id": target_channel,
        "message": f"[echo_log-escalate {esc_id}]\n{reason}",
    }
    headers = {
        "Authorization": f"Bearer {cfg.mattermost_token}",
        "Content-Type": "application/json",
    }
    ok, data = _post_json(url, body, cfg.http_timeout_s, headers)
    return {
        "escalation_id": esc_id,
        "sent": ok,
        "transport": "mm" if ok else "file_only",
        "backend_reachable": ok,
        "is_demo": False,
        "local_path": str(local_path),
        "note": "ok" if ok else f"mm-fail: {data}",
    }


# --------------------------------------------------------------------------- #
# Tool 9: audit_log_decision (Hash-Chain-Entry, lokal)                        #
# --------------------------------------------------------------------------- #
def audit_log_decision(
    decision: str,
    evidence: str | None = None,
    kategorie: str = "geprüft",
    client_id: str = "echo_log",
) -> dict:
    """Schreibt einen Hash-Chain-Entry für eine Beratungs-/Schulungs-Entscheidung.

    Integration zu aie-hash-chain — wenn aie_hash_chain importierbar, wird
    eine echte Ed25519-signierte Chain-Append durchgeführt. Sonst Fallback
    auf reine sha256-Hash-Chain (ohne Sig) und ehrliche Markierung.

    Args:
        decision: Entscheidungs-Text (Pflicht).
        evidence: Quell-/Beleg-Link/-Text (optional).
        kategorie: "geprüft" / "vermittelt" / "offen" (default geprüft).
        client_id: Mandant-/Bot-ID für Chain-File-Pfad.

    Returns:
        {entry_id, entry_hash, signed: bool, chain_path: str,
         backend_reachable: bool (immer True — local), is_demo: bool}
    """
    cfg = get_config()
    if not decision:
        raise ValueError("audit_log_decision: decision required")
    kategorie = kategorie.strip().lower()
    if kategorie not in ("geprüft", "geprueft", "vermittelt", "offen"):
        raise ValueError(
            "audit_log_decision: kategorie must be geprüft/vermittelt/offen"
        )
    kategorie_norm = "geprüft" if kategorie in ("geprüft", "geprueft") else kategorie

    chain_dir = cfg.hash_chain_dir / client_id
    chain_dir.mkdir(parents=True, exist_ok=True)
    chain_path = chain_dir / "chain.json"

    # Versuch: echte aie-hash-chain
    signed = False
    try:
        from aie_hash_chain.chain import (  # type: ignore
            Payload,
            append_entry,
            init_chain,
            load_chain,
            save_chain,
        )

        if not chain_path.exists():
            chain_path_real, privkey_path = init_chain(client_id, chain_dir)
            chain_path = chain_path_real
        else:
            privkey_path = chain_dir / "key.pem"
            if not privkey_path.exists():
                # Inkonsistenz — chain.json ohne key.pem; init überschreibt nicht.
                # In dem Fall: fallback auf no-sig mode.
                raise RuntimeError("chain.json present but key.pem missing")
        chain = load_chain(chain_path)
        payload = Payload(
            kategorie=kategorie_norm,  # type: ignore
            thema=decision[:200],
            quelle=(evidence or "")[:500],
            datum=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        entry = append_entry(chain, privkey_path, payload)
        save_chain(chain, chain_path)
        signed = True
        return {
            "entry_id": entry.id,
            "entry_hash": entry.entry_hash,
            "prev_hash": entry.prev_hash,
            "signed": signed,
            "chain_path": str(chain_path),
            "client_id": client_id,
            "backend_reachable": True,
            "is_demo": False,
            "note": "Ed25519-signed via aie-hash-chain",
        }
    except Exception as e:
        # Fallback: minimal sha256-Chain ohne Signature
        chain_data: dict[str, Any] = {}
        if chain_path.exists():
            try:
                chain_data = json.loads(chain_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                chain_data = {}
        entries = chain_data.setdefault("entries", [])
        prev_hash = entries[-1]["entry_hash"] if entries else ""
        entry_id = uuid.uuid4().hex
        payload_dict = {
            "kategorie": kategorie_norm,
            "thema": decision[:200],
            "quelle": (evidence or "")[:500],
            "datum": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        canonical = json.dumps(
            {"id": entry_id, "prev_hash": prev_hash, "payload": payload_dict},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        entry_hash = hashlib.sha256(canonical).hexdigest()
        entry = {
            "id": entry_id,
            "prev_hash": prev_hash,
            "payload": payload_dict,
            "entry_hash": entry_hash,
            "ed25519_sig": "",
        }
        entries.append(entry)
        chain_data.setdefault("client", client_id)
        chain_data.setdefault("pubkey_pem", "")
        chain_path.write_text(
            json.dumps(chain_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return {
            "entry_id": entry_id,
            "entry_hash": entry_hash,
            "prev_hash": prev_hash,
            "signed": False,
            "chain_path": str(chain_path),
            "client_id": client_id,
            "backend_reachable": True,
            "is_demo": False,
            "note": f"mock-only signature — aie-hash-chain nicht importierbar oder key fehlt ({type(e).__name__})",
        }


# --------------------------------------------------------------------------- #
# Tool 10: verify_url_build                                                   #
# --------------------------------------------------------------------------- #
def verify_url_build(payload: dict) -> dict:
    """Baut eine verify.ai-engineering.at Verify-URL aus einem Chain-Payload.

    Format-Spec:
      <verify_base>/v?c=<client_id>&e=<entry_id>&h=<entry_hash>
        [&p=<short_proof_b64>]

    Args:
        payload: dict mit mindestens {client_id, entry_id, entry_hash}.
                 Optional {proof_b64}.

    Returns:
        {url: str, canonical_hash: str, verify_base: str}
    """
    cfg = get_config()
    if not isinstance(payload, dict):
        raise TypeError("verify_url_build: payload must be dict")
    required = ("client_id", "entry_id", "entry_hash")
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(f"verify_url_build: missing keys {missing}")

    canonical_hash = hashlib.sha256(
        json.dumps(
            {k: payload[k] for k in required},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    params = {
        "c": payload["client_id"],
        "e": payload["entry_id"],
        "h": payload["entry_hash"],
    }
    if payload.get("proof_b64"):
        params["p"] = payload["proof_b64"]
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{cfg.verify_base_url}/v?{qs}"
    return {
        "url": url,
        "canonical_hash": canonical_hash,
        "verify_base": cfg.verify_base_url,
    }


# --------------------------------------------------------------------------- #
# Public registry — used by server.py for FastMCP tool registration           #
# --------------------------------------------------------------------------- #
TOOL_REGISTRY = {
    "voice_check": voice_check,
    "pattern_learn": pattern_learn,
    "substrate_query": substrate_query,
    "notebook_recall": notebook_recall,
    "peer_memory_read": peer_memory_read,
    "peer_memory_write": peer_memory_write,
    "system_status_summary": system_status_summary,
    "human_in_loop_escalate": human_in_loop_escalate,
    "audit_log_decision": audit_log_decision,
    "verify_url_build": verify_url_build,
}
