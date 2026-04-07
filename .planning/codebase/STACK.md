# STACK.md — Technology Stack

## Languages & Runtime

| Item | Value |
| ---- | ----- |
| Language | Python 3.10+ (uses `X \| Y` union syntax, `from __future__ import annotations`) |
| Runtime | CPython (no Cython, no C extensions beyond Qt) |
| Entry Point | `main.py` → calls `main()` |

## Core Dependencies (`requirements.txt`)

| Package | Version | Purpose |
| ------- | ------- | ------- |
| `telethon` | 1.36.0 | Telegram MTProto client — all API calls |
| `PyQt5` | ≥5.15 | Desktop GUI framework |
| `qasync` | ≥0.27 | Bridge between asyncio event loop and Qt event loop |
| `python-dotenv` | 1.0.1 | Loads `.env` files for legacy env-based config |

## Build & Distribution

| Item | Detail |
| ---- | ------ |
| Packager | PyInstaller (`FurayaPromoEngine.spec`) |
| Output | Single-file `FurayaPromoEngine.exe` |
| Hidden imports | `qasync`, `telethon.*` modules explicitly listed |
| UPX | Enabled (compresses binary) |
| Console | Disabled (windowed app) |
| Icon | `furaya.ico` bundled |

## Async Architecture

- `qasync.QEventLoop` wraps Qt's native event loop, enabling `await` inside Qt slot callbacks
- All network operations use `asyncio.ensure_future()` to fire coroutines from sync Qt slots
- Pattern: `asyncio.ensure_future(self._async_*(...))` — fire-and-forget from button handlers

## Data Storage

- **Format**: JSON files in `~/FurayaPromoEngine/data/` (user home directory)
- `data/accounts.json` — serialized `Account` objects (phone, api\_id, api\_hash only)
- `data/groups.json` — serialized `Group` objects (username, title, stats, priority\_score)
- `data/messages.json` — serialized `MessageTemplate` objects
- `data/performance.json` — per-account metrics + session history (last 50 sessions)
- `data/state.json` — TaskQueue state (currently placeholder, not persisted)
- Session files: `data/session_<phone>.session` (Telethon SQLite session, gitignored)

## Configuration

- Old config via `.env` file (phone, API credentials, channel usernames, timing)
- New config: all entered via GUI with JSON persistence in `data/`
- `python-dotenv` still present but effectively unused in current v2 GUI flow
- No global config singleton — managers load from their own `DATA_FILE` paths

## Logging

- Python stdlib `logging` module
- `basicConfig` in `main.py`: INFO level, dual handlers (file + stdout)
- Log file: `~/FurayaPromoEngine/logs/bot.log`
- GUI also captures logs via `log_cb` callback chain → `LogsTab`
