"""FastMCP-Server: aie-echolog-toolkit.

10 Tools für echo_log-Persona (Brand-Soul L4). Mac-lokal als stdio-MCP.

Tools werden in einer for-Loop aus TOOL_REGISTRY angemeldet, damit die
Tests dieselbe Funktionsmenge direkt aufrufen können wie der live-Server.
"""
from __future__ import annotations

from fastmcp import FastMCP

from . import tools as _tools

mcp = FastMCP("aie-echolog-toolkit")


# --------------------------------------------------------------------------- #
# Tool-Registrierung (one-shot, deklarativ)                                   #
# --------------------------------------------------------------------------- #

@mcp.tool()
def voice_check(text: str) -> dict:
    """7-Dimensionen-Voice-Profil-Check (Pre-Publish-Gate für echo_log)."""
    return _tools.voice_check(text)


@mcp.tool()
def pattern_learn(
    success_pattern: str,
    source_label: str = "echo_log",
    append_to_notebook: bool = True,
) -> dict:
    """Lernt einen erfolgreichen Voice-Pattern + persistiert lokal + Notebook-Ready."""
    return _tools.pattern_learn(success_pattern, source_label, append_to_notebook)


@mcp.tool()
def substrate_query(query: str, scope: str = "") -> dict:
    """kb-Substrat-Search via in-process aie-kb-reader-Algorithmus."""
    return _tools.substrate_query(query, scope)


@mcp.tool()
def notebook_recall(
    notebook_id: str | None = None,
    query: str = "",
    limit: int = 10,
) -> dict:
    """Brand-Soul-Sources/Evolution-Notes aus Open-Notebook (fallback: kb/raw)."""
    return _tools.notebook_recall(notebook_id, query, limit)


@mcp.tool()
def peer_memory_read(
    peer_id: str,
    since: str | None = None,
    limit: int = 50,
) -> dict:
    """Honcho-Peer-Memory lesen."""
    return _tools.peer_memory_read(peer_id, since, limit)


@mcp.tool()
def peer_memory_write(
    peer_id: str,
    content: str,
    metadata: dict | None = None,
) -> dict:
    """Honcho-Peer-Memory schreiben + lokaler Audit-Mirror."""
    return _tools.peer_memory_write(peer_id, content, metadata)


@mcp.tool()
def system_status_summary() -> dict:
    """Composite-Status der echo_log-Surfaces (VG/Honcho/Notebook/MM/Verify)."""
    return _tools.system_status_summary()


@mcp.tool()
def human_in_loop_escalate(reason: str, channel: str | None = None) -> dict:
    """Eskaliert an Joe via Mattermost-DM (Pflicht-Local-Mirror)."""
    return _tools.human_in_loop_escalate(reason, channel)


@mcp.tool()
def audit_log_decision(
    decision: str,
    evidence: str | None = None,
    kategorie: str = "geprüft",
    client_id: str = "echo_log",
) -> dict:
    """Hash-Chain-Append (Ed25519 via aie-hash-chain, sonst sha256-fallback)."""
    return _tools.audit_log_decision(decision, evidence, kategorie, client_id)


@mcp.tool()
def verify_url_build(payload: dict) -> dict:
    """Baut Verify-URL für verify.ai-engineering.at aus Chain-Payload."""
    return _tools.verify_url_build(payload)


# --------------------------------------------------------------------------- #
# Entry-point                                                                 #
# --------------------------------------------------------------------------- #
def main() -> None:
    """FastMCP-Server starten (stdio-Transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
