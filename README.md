<!-- W41-DOC-SWEEP-FRONTMATTER
---
title: aie-echolog-toolkit — Echolog-Persona-Toolset
stand: 2026-05-26
gelockt-am: mutable
mutability: mutable
hash-chain: nein
review-due: 2026-08-26
quelle: W16-F-Folge Build-Beleg + BAUTEILE-INVENTAR.md neu (Task #218)
operationalisiert: M40 (Bauteil-Disziplin) · A30/A31 (Fallback-Chain-Doku) · Regel 17 (Doku-Versionierung)
welle: W41-DOC-SWEEP (2026-05-26)
cross-ref: ~/kb/ops/BAUTEILE-INVENTAR.md neu (Task #218) · ~/kb/ops/FALLBACK-CHAINS.md · ~/kb/ops/DOCU-VERSIONING-LOCK.md
---
-->

# aie-echolog-toolkit

Mac-lokales FastMCP-Toolset für die echo_log-Persona (Brand-Soul L4).
Registriert 10 MCP-Tools, die echo_log via Mattermost-Bridge / direktem
HTTP-Call konsumieren kann, ohne dass ein VG-Plugin im Voice-Gateway-
Container deployed werden muss (Welle-17-C Recon: VG-Bridge-Anbindung
blockiert; deshalb Option D — Mac-lokal MCP-Set + direkte HTTP-Bridge).

**Task #218** (W16-F-Folge-1). Bauteil-Status M40: lauffähig + getestet +
reproduzierbar durch `python scripts/smoke_test.py`.

## Die 10 Tools

| # | Tool                      | Zweck                                                                              | Integration                |
|---|---------------------------|------------------------------------------------------------------------------------|----------------------------|
| 1 | `voice_check`             | 7-Dimensionen-Pre-Publish-Voice-Gate (Heuristik-Spiegel von brand-voice-watcher)   | brand-voice-watcher Skill  |
| 2 | `pattern_learn`           | Persistiert erfolgreiche Voice-Patterns lokal + Notebook-Ready                     | voice-pattern-keeper Skill |
| 3 | `substrate_query`         | kb-Substrat-Suche (~/kb/ literal-search, case-insensitive)                         | aie-kb-reader-mcp          |
| 4 | `notebook_recall`         | Brand-Soul-Sources aus Open-Notebook `jkbjq4ndpqmo5nxkfhit`                        | open-notebook              |
| 5 | `peer_memory_read`        | Honcho-Workspace Conclusions des Peers lesen                                       | aie-honcho-sync-mcp        |
| 6 | `peer_memory_write`       | Honcho-Workspace Conclusion schreiben + lokaler Audit-Mirror                       | aie-honcho-sync-mcp        |
| 7 | `system_status_summary`   | Composite-Status: VG-Bridge + Honcho + Notebook + MM + Verify                      | aie-docker-mcp + aie-http-api-mcp |
| 8 | `human_in_loop_escalate`  | Eskaliert Entscheidung an Joe via Mattermost-DM (Pflicht-Local-Mirror)              | aie-echo-bridge            |
| 9 | `audit_log_decision`      | Hash-Chain-Append (Ed25519 via aie-hash-chain, sha256-Fallback)                    | aie-hash-chain             |
|10 | `verify_url_build`        | Baut Verify-URL für verify.ai-engineering.at                                       | aie-verify                 |

## Anti-Slop-Garantien (M40 + A33)

- **Backend nicht erreichbar → ehrliche Markierung**: Tools setzen
  `is_demo: True` + `backend_reachable: False` + Kommentar mit Grund.
  Keine stille Fake-Antwort.
- **Local-Mirror Pflicht** für `peer_memory_write`, `human_in_loop_escalate`,
  `audit_log_decision` und `pattern_learn`: auch wenn Remote down, ist die
  Datei lokal im `AIE_HASH_CHAIN_DIR` (default `~/.aie/echolog-chains/`).
- **Hash-Chain Real-vs-Fallback**: wenn `aie_hash_chain` importierbar →
  Ed25519-signiert. Sonst sha256-only mit `signed: False` und Note.
- **Path-Escape-Schutz** bei `substrate_query` (scope-Pfad-Validierung).
- **A33 KEIN-MOCK in reachable-Pfaden** (W41-ECHO-LOG-FIX): wenn ein Backend
  erreichbar ist aber die API-Layer instabil (Beispiel: Open-Notebook hat
  noch keine stabile REST-Suche), werden **KEINE synthetischen Snippets**
  zurueckgegeben. Stattdessen echte Surrogat-Suche im kb-Substrat (siehe
  unten). Bei kein Match: ehrlich `sources: []`, kein Demo-Fallback.

## `notebook_recall` Fallback-Chain (Surrogat-Pfad)

Open-Notebook v0.x liefert noch keine stabile REST-Suche. `notebook_recall`
folgt deshalb dieser Chain:

1. **`force_demo=True`** (Test-/Offline-Mode) → synthetische Demo-Sources
   mit `is_demo: True` + `backend_reachable: False`.
2. **Backend unreachable** (`/api/health` failed) → synthetische Demo-Sources
   mit `is_demo: True` + `backend_reachable: False` + `note: "mock-only ..."`.
3. **Backend reachable, REST-Suche instabil** (aktueller Live-Pfad) →
   `_surrogate_search_kb()` liest **echte** kb-Dateien:
   - `~/kb/projects/echo-log-evolution.md`
   - `~/kb/company/IDENTITY.md`
   - `~/kb/company/NORDSTERN.md`
   Returns `sources` mit echtem `source_path`, `surrogate_path: True`,
   `is_demo: False`. Bei keinem Match: `sources: []` (ehrlich).
4. **Open-Notebook bekommt stabile REST-Suche** (Future) → direkter API-Call,
   Surrogat-Pfad obsolet.

Test-Coverage (`tests/test_notebook_recall.py`):
- 4 Demo-Pfad-Tests (alt)
- 6 Surrogat-Pfad-Tests (W41): find-match, honest-empty-on-no-match,
  honest-empty-on-missing-kb, surrogate-marker-explicit, unreachable-is-demo,
  limit-respected.

## Konfiguration (ENV)

```sh
# Substrat
AIE_KB_ROOT=~/kb

# Honcho
HONCHO_BASE_URL=http://10.40.10.82:8055
HONCHO_TOKEN=                       # optional
HONCHO_WORKSPACE=ai-engineering

# Open-Notebook (Brand-Soul)
OPEN_NOTEBOOK_URL=http://10.40.10.82:5055
BRAND_SOUL_NOTEBOOK_ID=jkbjq4ndpqmo5nxkfhit

# VG-MCP-Bridge (Mac-lokal)
VG_BRIDGE_URL=http://127.0.0.1:8765

# Mattermost (für human_in_loop_escalate)
MATTERMOST_URL=https://mm.ai-engineering.at
MATTERMOST_TOKEN=                   # erforderlich für Live-Eskalation
JOE_DM_CHANNEL=                     # MM-Channel-ID für Joe-DM

# Verify-Surface
AIE_VERIFY_URL=https://verify.ai-engineering.at

# Hash-Chain Output
AIE_HASH_CHAIN_DIR=~/.aie/echolog-chains

# Force-Demo (für Tests / Offline)
AIE_ECHOLOG_DEMO=0
```

## Installation

```sh
cd ~/code-aie/aie-echolog-toolkit
pip install -e ".[dev]"
```

## Tests

```sh
pytest -v
```

Erwartung: 20+ grüne Tests.

## Smoke-Test

```sh
python scripts/smoke_test.py
# oder explizit Demo-Mode:
AIE_ECHOLOG_DEMO=1 python scripts/smoke_test.py
```

Exit-Code 0 = alle 10 Tools ausgeführt ohne Exception.

## Einbindung als MCP-Server (Claude Code)

```sh
# stdio-MCP starten:
aie-echolog-toolkit
```

oder via `~/.claude/.mcp.json` / Projektpfad `claude-mcp-config.json`
(siehe Datei im Repo-Root).

## Cross-Integration zu 6 Brain-Bauteilen

1. **aie-kb-reader-mcp** — Tool 3 (`substrate_query`) nutzt denselben
   Search-Algo + Path-Escape-Schutz wie der read-only kb-Server.
2. **aie-honcho-sync-mcp** — Tools 5+6 sprechen die Honcho-v3-REST-API
   mit denselben Endpoints (`/v3/workspaces/<ws>/conclusions/list` +
   `/v3/workspaces/<ws>/conclusions`).
3. **aie-hash-chain** — Tool 9 importiert `aie_hash_chain.chain` direkt
   für Ed25519-signierte Appends. Fallback bei Import-Fail.
4. **aie-verify** — Tool 10 baut URLs für die verify.ai-engineering.at
   Verifier-Surface (`/v?c=&e=&h=&p=`).
5. **aie-echo-bridge** — Tool 8 spiegelt das mm_dm.MattermostDMClient-
   Format (Bearer-Auth + `/api/v4/posts` + channel_id + message-Body).
6. **aie-vg-mcp-bridge** — Tool 7 probet `VG_BRIDGE_URL/health` als
   Teil des Composite-Status.

## Welle-17 Kontext

W17-C-Folge-2 (Task #225) hatte echo_log MCP-Client-Recon gefordert
mit der Decision-Option D = "VG umgehen". Dieses Toolkit ist die
Implementierung von Option D: Mac-lokal startet der stdio-MCP-Server,
echo_log spricht ihn via Mattermost-Bridge-Workflow oder direkter
HTTP-Wrapper-Schicht an. Solange aie-vg-mcp-bridge (Task #226) blockiert
ist, kann echo_log dennoch ein vollständiges Tool-Set bekommen.
