# CONVENTIONS.md — Code Style & Patterns

## Code Style

- **Python version**: Uses `from __future__ import annotations` for PEP 563 deferred evaluation
- **Type hints**: Present throughout — function signatures, dataclass fields, return types
- **Docstrings**: Single-line module docstrings on all core files; minimal inline comments
- **f-strings**: Used consistently for logging and status messages
- **Line length**: No enforced limit — some lines exceed 100 chars
- **No linter config**: No `pyproject.toml`, `setup.cfg`, `.flake8`, `.pylintrc`, or `ruff.toml`

## Async Patterns

### Fire-and-forget from Qt slots
```python
# Correct pattern used throughout gui/
def _on_button_clicked(self):
    asyncio.ensure_future(self._async_action())

async def _async_action(self):
    result = await some_telethon_call()
    self._label.setText(result)  # Qt update from async is safe with qasync
```

### Cancellable sleep
```python
# Used in CampaignController to allow immediate stop
async def _sleep(self, seconds: float) -> None:
    try:
        await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass
```

### Stop signaling
```python
self._stop_event = asyncio.Event()  # Set to stop
self._pause_event = asyncio.Event()  # Clear to pause, set to resume
self._pause_event.set()  # Initially unpaused
```

## Error Handling

- **Telethon errors**: Always caught explicitly by type, never swallowed silently
- **Generic fallback**: `except Exception as e: logger.error(...); return False, str(e)`
- **Result tuple pattern**: `(success: bool, error: str)` returned by send/join methods
- **UI callbacks**: `log_cb`, `metrics_cb`, `state_cb` — never raises, always optional

Example:
```python
async def send_message(self, group_username: str, text: str) -> tuple[bool, str]:
    try:
        await self.client.send_message(group_username, text)
        return True, ""
    except FloodWaitError as e:
        return False, f"FloodWait:{e.seconds}"
    except Exception as e:
        return False, str(e)
```

## Data Model Pattern (Dataclasses)

All domain models use `@dataclass`:
```python
@dataclass
class Group:
    username: str
    title: str = ""
    member_count: int = 0
    joined: bool = False
    priority_score: float = 50.0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Group":
        return Group(**{k: v for k, v in d.items() if k in Group.__dataclass_fields__})
```

## Manager Pattern

Managers follow a consistent pattern:
1. `__init__()` → calls `self.load()`
2. `load()` → reads JSON from `DATA_FILE`, populates `self._<items>` dict/list
3. `save()` → serializes to JSON, writes to disk
4. CRUD methods: `add()`, `remove()`, `get_all()`, `get_by_*()` 
5. Save on mutation: each mutation method calls `self.save()`

## Qt Signal/Slot Conventions

```python
# Signal definition on class
class AccountsTab(QWidget):
    accounts_changed = pyqtSignal()  # no-arg signals are common

# Connecting in MainWindow
self._accounts_tab.accounts_changed.connect(self._on_accounts_changed)

# Cross-tab callbacks via MainWindow methods (not direct widget references)
def _on_accounts_changed(self) -> None:
    self._discovery_tab.on_accounts_changed()
```

## Callback Pattern for Core → GUI Communication

`CampaignController` receives callbacks at construction:
```python
CampaignController(
    log_cb=lambda level, msg: ...,      # Called on every log event
    metrics_cb=lambda d: ...,           # Called after each task execution
    state_cb=lambda state_str: ...,     # Called on state transitions
)
```

## Naming

| What | Convention | Example |
|------|-----------|---------|
| Private Qt fields | `self._btn_*`, `self._lbl_*` | `self._btn_search`, `self._table` |
| Async methods | `_async_*` prefix | `_async_login()`, `_async_search()` |
| Phase methods | `_phase_*` prefix | `_phase_join()`, `_phase_forward_loop()` |
| Module constants | `UPPER_CASE` | `DATA_FILE`, `DARK_THEME` |
| Enums | `PascalCase` values that are strings | `CampaignState.RUNNING = "Running"` |
