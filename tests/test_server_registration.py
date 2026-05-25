"""Tests dass alle 10 Tools im FastMCP-Server registriert sind."""
from __future__ import annotations

from aie_echolog_toolkit import server
from aie_echolog_toolkit.tools import TOOL_REGISTRY


EXPECTED_TOOLS = {
    "voice_check",
    "pattern_learn",
    "substrate_query",
    "notebook_recall",
    "peer_memory_read",
    "peer_memory_write",
    "system_status_summary",
    "human_in_loop_escalate",
    "audit_log_decision",
    "verify_url_build",
}


def test_registry_has_ten_tools():
    assert set(TOOL_REGISTRY.keys()) == EXPECTED_TOOLS
    assert len(TOOL_REGISTRY) == 10


def test_server_module_exposes_all_tools():
    for name in EXPECTED_TOOLS:
        assert hasattr(server, name), f"server.{name} not bound"


def test_mcp_instance_name():
    assert server.mcp.name == "aie-echolog-toolkit"
