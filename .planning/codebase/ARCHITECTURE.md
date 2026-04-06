# ARCHITECTURE.md — System Architecture

## Pattern

**Layered Desktop MVC** with async Telegram I/O:
- **Model** layer: `core/` — pure data + logic, no Qt imports
- **View+Controller** layer: `gui/` — Qt widgets wiring signals to `core/` managers
- **Bridge**: `qasync.QEventLoop` unifies asyncio + Qt event loops

## Two Parallel Engine Systems (⚠️ Key Architectural Divergence)

The codebase has **two independent campaign engine systems** that evolved separately:

### System A: CampaignController (v2 — Current primary)
```
MainWindow
  └── CampaignController (orchestrator)
        ├── AccountManager  (multi-account pool)
        ├── GroupManager    (group DB with scoring)
        ├── MessageEngine   (template rotation + variation)
        ├── PerformanceTracker (metrics + session history)
        ├── TaskQueue       (structured task distribution)
        ├── AdaptiveEngine  (dynamic delay/wave adjustment)
        └── PromotionEngine (Telethon wrapper per account)
```
- Mounted under `gui/campaign_tab.py` (Start/Pause/Stop)
- Multi-account support: one `PromotionEngine` per logged-in account
- Wave-based batching with adaptive delays
- Priority-scored group ranking

### System B: ForwardEngine (v1 — Legacy, GUI still mounted)
```
MainWindow
  └── EngineTab
        └── ForwardEngine (single account, 3-phase pipeline)
              Phase 1: discovery → Phase 2: join → Phase 3: forward loop
```
- Mounted under `gui/engine_tab.py` — still accessible in the UI
- Single-account only, hardcoded `DATA_DIR = "C:/FurayaPromoEngine/data"`
- Uses only `contacts.SearchRequest` (not the dual-strategy search)
- **Not integrated** with AccountManager/GroupManager — writes its own joined_groups.json

## Data Flow

```
User Action (Qt Button click)
  → QSlot (sync)
    → asyncio.ensure_future(coroutine)
      → Telethon API call (MTProto over network)
        → Result handling (update Qt widget / persist JSON)
          → pyqtSignal.emit() if cross-widget notification needed
```

## Entry Points

| File | Role |
|------|------|
| `main.py` | Creates QApplication, installs qasync event loop, shows MainWindow |
| `gui/main_window.py` | Instantiates all core managers + CampaignController, wires up 8 tabs |
| `core/campaign_controller.py` | Top-level campaign state machine, `_run_loop()` is the main async task |
| `core/forward_engine.py` | Legacy 3-phase engine, standalone asyncio task |

## Key Abstractions

| Class | File | Responsibility |
|-------|------|----------------|
| `Account` | `core/account.py` | Single account dataclass + flood/ban state |
| `AccountManager` | `core/account_manager.py` | CRUD + persistence for account pool |
| `Group` | `core/group_manager.py` | Group dataclass + priority scoring |
| `GroupManager` | `core/group_manager.py` | CRUD + ranking for group pool |
| `MessageTemplate` | `core/message_engine.py` | Template + performance tracking |
| `MessageEngine` | `core/message_engine.py` | Rotation + micro-variation |
| `Task` | `core/task_queue.py` | (account, group, message) unit of work |
| `TaskQueue` | `core/task_queue.py` | Balanced distribution + retry logic |
| `AdaptiveEngine` | `core/adaptive_engine.py` | Dynamic delay scaling based on error rate |
| `CampaignState` | `core/campaign_controller.py` | State machine enum (IDLE→RUNNING→STOPPED) |
| `PromotionEngine` | `core/promotion_engine.py` | Per-account Telethon wrapper |
| `ForwardEngine` | `core/forward_engine.py` | Legacy standalone engine |

## GUI Tab Layout

| Tab | Widget | Key Dependency |
|-----|--------|---------------|
| Dashboard | `DashboardTab` | Receives metrics callbacks from CampaignController |
| Campaign | `CampaignTab` | Owns Start/Pause/Stop → CampaignController |
| Accounts | `AccountsTab` | Owns AccountManager, handles login flow |
| Groups | `GroupsTab` | Displays GroupManager contents |
| Discovery | `DiscoveryTab` | AccountManager + GroupManager + PromotionEngine |
| Messages | `MessagesTab` | MessageEngine CRUD |
| Analytics | `AnalyticsTab` | PerformanceTracker display |
| Logs | `LogsTab` | Receives log_cb events |

## State Management

- No global state — managers are instantiated once in `MainWindow.__init__()` and passed by reference to tabs
- `CampaignController` holds `_state: CampaignState` + `asyncio.Event` objects for stop/pause
- Data persistence: each manager owns its `DATA_FILE` path and calls `save()` after mutations
- Working directory changed to `~/FurayaPromoEngine/` at startup (`os.chdir()` in `main.py`)
