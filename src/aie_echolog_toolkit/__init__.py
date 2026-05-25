"""aie-echolog-toolkit — MCP-Toolset für echo_log-Persona (Brand-Soul L4).

10 MCP-Tools die echo_log via Mac-lokalen FastMCP-Server bekommt:
  voice_check, pattern_learn, substrate_query, notebook_recall,
  peer_memory_read, peer_memory_write, system_status_summary,
  human_in_loop_escalate, audit_log_decision, verify_url_build.

Cross-Integration zu 6 Brain-Bauteilen (kb-reader, honcho-sync,
hash-chain, verify, echo-bridge, vg-mcp-bridge).

Anti-Slop: Bei nicht erreichbaren Backends → ehrliche Demo-Mode-
Markierung im Tool-Output (`is_demo`, `backend_reachable`).
"""

__version__ = "0.1.0"
