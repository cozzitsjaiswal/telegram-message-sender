# STRUCTURE.md — Directory Layout & Key Locations

## Root Layout

```text
telegram-message-sender/
├── main.py                          # Entry point — app bootstrap
├── requirements.txt                  # 4 deps: telethon, PyQt5, qasync, python-dotenv
├── FurayaPromoEngine.spec            # PyInstaller build config
├── furaya.ico                        # Application icon
├── .env.example                      # Legacy env config template (unused in v2)
├── .gitignore                        # Excludes .env, *.session, accounts.json, build/
│
├── core/                            # Business logic — NO Qt imports
│   ├── account.py                   # Account dataclass + status (IDLE/ACTIVE/FLOOD/BANNED)
│   ├── account_manager.py           # Multi-account CRUD + persistence
│   ├── adaptive_engine.py           # Dynamic delay/wave-size tuning
│   ├── campaign_controller.py       # Main orchestrator (state machine + run loop)
│   ├── forward_engine.py            # Legacy v1 engine (3-phase: search→join→forward)
│   ├── group_manager.py             # Group CRUD + priority scoring
│   ├── message_engine.py            # Template rotation + micro-variation
│   ├── performance_tracker.py       # Per-account metrics + session history
│   ├── promotion_engine.py          # Telethon wrapper (search, join, send)
│   └── task_queue.py               # Task (account+group+msg) queue + retry
│
├── gui/                             # Qt5 widgets — all inherit QWidget
│   ├── main_window.py              # QMainWindow — sidebar + stacked tabs
│   ├── styles.py                    # DARK_THEME QSS string
│   ├── accounts_tab.py             # Multi-account management + login flow
│   ├── account_tab.py              # (Legacy single-account tab — may be unused)
│   ├── add_account_dialog.py       # Inline add dialog (also duplicated in accounts_tab.py)
│   ├── analytics_tab.py            # Performance charts/stats
│   ├── campaign_tab.py             # Campaign control (START/PAUSE/STOP)
│   ├── dashboard_tab.py            # Live KPI cards + event feed
│   ├── discovery_tab.py            # Keyword search + group join
│   ├── engine_tab.py               # Legacy v1 engine control panel
│   ├── groups_tab.py               # Group list viewer
│   ├── log_tab.py                  # (Legacy — possibly replaced by logs_tab.py)
│   ├── logs_tab.py                 # Log stream viewer
│   ├── messages_tab.py             # Message template CRUD
│   └── otp_dialog.py              # OTP + 2FA password prompt dialog
│
├── data/                            # Runtime data (IN REPO but mostly gitignored)
│   ├── accounts.json               # Account pool (gitignored)
│   ├── groups.json                 # Group DB
│   ├── messages.json               # Message templates (gitignored)
│   ├── performance.json            # Metrics history (gitignored)
│   └── state.json                  # Task state (placeholder)
│
├── logs/                            # Log output directory (gitignored)
├── build/                           # PyInstaller build artifacts (gitignored)
├── dist/                            # PyInstaller output (gitignored)
├── .venv/                           # Virtual environment (gitignored)
│
├── _package.ps1                     # PowerShell build + packaging script
├── _final.ps1                       # Final distribution script
├── _make_zip.ps1                    # Zip distribution maker
├── _make_ico.py                     # Icon generation helper
├── _check.py                        # Pre-build sanity check
└── installer.ps1                    # End-user installer script
```

## Key File Locations

| What | Path |
| ---- | ---- |
| App entry | `main.py` |
| QSS theme | `gui/styles.py` → `DARK_THEME` string |
| Campaign brain | `core/campaign_controller.py` → `CampaignController._run_loop()` |
| Telegram API layer | `core/promotion_engine.py` → `PromotionEngine` |
| Legacy engine | `core/forward_engine.py` → `ForwardEngine` |
| Group DB | `~/FurayaPromoEngine/data/groups.json` (runtime) |
| Telethon sessions | `~/FurayaPromoEngine/data/session_<phone>.session` |
| Application logs | `~/FurayaPromoEngine/logs/bot.log` |

## Naming Conventions

- Python modules: `snake_case.py`
- Classes: `PascalCase`
- Qt widget instances: `self._<name>` prefixed with underscore
- Private methods: `_method_name` single underscore
- Async methods: `_async_<name>` or `_phase_<name>` prefix
- Button PyQt objects: `self._btn_<action>`
- Label PyQt objects: `self._lbl_<name>` or `self._status`
- Constants: `UPPER_CASE` at module level

## Duplication Notes

| Issue | Files |
| ----- | ----- |
| `AddAccountDialog` defined twice | `gui/accounts_tab.py` line 25 AND `gui/add_account_dialog.py` |
| `log_tab.py` vs `logs_tab.py` | Both exist — `logs_tab.py` is imported in `main_window.py` |
| `account_tab.py` vs `accounts_tab.py` | `account_tab.py` appears to be earlier single-account version |
| `ForwardEngine` vs `CampaignController` | Two full campaign systems, both mounted in GUI |
