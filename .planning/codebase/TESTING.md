# TESTING.md — Test Structure & Practices

## Current State

**No automated tests exist in this project.**

- No `tests/` or `test/` directory
- No `pytest`, `unittest`, `nose`, or any test framework in `requirements.txt`
- No CI/CD configuration (no GitHub Actions, no `.github/` directory)
- No `_check.py` test content — it's a pre-build sanity check script, not a test suite

## Manual Test Patterns (Inferred from Code)

All "testing" is done manually by running the GUI application:

| Feature | Manual Test Approach |
| ------- | -------------------- |
| Account login | Add account → click Login → enter OTP → verify ✅ Connected status |
| Group search | Discovery tab → enter keyword → click Search → verify table populated |
| Group join | Select rows → click Join → observe row color change (green/red) |
| Campaign start | Campaign tab → verify accounts logged in → click START → watch log stream |
| Flood wait handling | Observed in log tab when `⏳ FloodWait Xs` appears |

## Where Tests Should Go (If Added)

```text
tests/
├── unit/
│   ├── test_group_manager.py      # CRUD, ranking, persistence
│   ├── test_message_engine.py     # Rotation, micro-variation
│   ├── test_task_queue.py         # Build, retry, mark_done/failed
│   ├── test_adaptive_engine.py    # Mode configs, _adapt() logic
│   └── test_account.py            # is_available, flood cooldown
├── integration/
│   └── test_promotion_engine.py   # With mocked TelegramClient
└── conftest.py
```

## Recommended Testing Framework

- `pytest` (simple, widely supported)
- `pytest-asyncio` for coroutine testing
- `unittest.mock` / `pytest-mock` for mocking `TelegramClient`

## Testability Notes

- **Core layer is testable**: No Qt imports in `core/` → pure Python → easily unit-tested
- **Managers are file-dependent**: Use `tmp_path` fixture to override `DATA_FILE` paths
- **GUI layer is NOT unit-testable**: Would require `pytest-qt` or headless Qt setup
- **AdaptiveEngine** is fully testable (no I/O, pure logic)
- **TaskQueue** is fully testable (no I/O, pure logic)
- **PerformanceTracker** requires patching `Path` or `DATA_FILE`

## Example Unit Test Structure (Not Yet Implemented)

```python
# tests/unit/test_group_manager.py
import pytest
from pathlib import Path
from core.group_manager import GroupManager, Group

def test_add_and_retrieve(tmp_path, monkeypatch):
    monkeypatch.setattr("core.group_manager.DATA_FILE", tmp_path / "groups.json")
    gm = GroupManager()
    g = Group(username="testgroup", title="Test", joined=True)
    gm.add(g)
    assert gm.get_by_username("testgroup") is not None
    assert gm.joined_count == 1
```
