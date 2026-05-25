#!/usr/bin/env python3
"""Smoke-Test für aie-echolog-toolkit.

Ruft alle 10 Tools in einem realistischen Demo-Mode-Lauf auf und
schreibt ein JSON-Summary nach stdout. Exit-Code 0 = alle Tools
führten ohne Exception aus.

Verwendung:
    AIE_ECHOLOG_DEMO=1 python scripts/smoke_test.py
oder live:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

# Erlaube Aufruf via `python scripts/smoke_test.py` ohne pip-install
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aie_echolog_toolkit import tools  # noqa: E402


def _run(name: str, fn, *args, **kw) -> dict:
    t0 = time.perf_counter()
    try:
        result = fn(*args, **kw)
        return {
            "name": name,
            "ok": True,
            "dt_ms": int((time.perf_counter() - t0) * 1000),
            "result_keys": sorted(result.keys()) if isinstance(result, dict) else None,
        }
    except Exception as e:
        return {
            "name": name,
            "ok": False,
            "dt_ms": int((time.perf_counter() - t0) * 1000),
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc().splitlines()[-3:],
        }


def main() -> int:
    # In Live-Run nicht force_demo, sondern realer Probe-Pfad — Backends
    # die nicht antworten landen automatisch im Demo-Fallback der Tools.
    cfg = tools.ToolkitConfig()
    tools.set_config(cfg)

    print(f"# smoke-test aie-echolog-toolkit @ {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"# force_demo={cfg.force_demo}  kb_root={cfg.kb_root}")

    runs = []
    runs.append(_run("voice_check", tools.voice_check,
                     "Joe in Burgenland: Art. 4 EU AI Act — Beleg ~/kb/raw/123.md"))
    runs.append(_run("pattern_learn", tools.pattern_learn,
                     "Ich sehe Marktversagen DACH-KMU und vermittle Art. 4.",
                     "echo_log", False))
    runs.append(_run("substrate_query", tools.substrate_query, "Art. 4"))
    runs.append(_run("notebook_recall", tools.notebook_recall, None, "IDENTITY", 5))
    runs.append(_run("peer_memory_read", tools.peer_memory_read, "joe", None, 5))
    runs.append(_run("peer_memory_write", tools.peer_memory_write,
                     "echo_log", "Smoke-Test-Eintrag", {"smoke": True}))
    runs.append(_run("system_status_summary", tools.system_status_summary))
    runs.append(_run("human_in_loop_escalate", tools.human_in_loop_escalate,
                     "Smoke-Test: keine echte Eskalation"))
    runs.append(_run("audit_log_decision", tools.audit_log_decision,
                     "Smoke-Test-Entscheidung", "~/kb/raw/smoke.md", "geprüft",
                     "smoke-test-client"))
    runs.append(_run("verify_url_build", tools.verify_url_build, {
        "client_id": "smoke", "entry_id": "e1", "entry_hash": "abc",
    }))

    summary = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_tools": len(runs),
        "ok_count": sum(1 for r in runs if r["ok"]),
        "fail_count": sum(1 for r in runs if not r["ok"]),
        "runs": runs,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
