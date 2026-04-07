# CONCERNS.md — Technical Debt, Known Issues & Fragile Areas

## Critical Concerns

### 1. Two Competing Engine Systems (High Risk)

- **Issue**: `ForwardEngine` (v1, `core/forward_engine.py`) and `CampaignController` (v2) are both mounted in the GUI
- **Risk**: Users can run both simultaneously — they'd be sending from the same account to the same groups with no coordination
- **Impact**: Duplicate sends, account rate-limit amplification, confusing UX
- **Location**: `gui/engine_tab.py` + `gui/main_window.py` lines 91, 94
- **Recommended Fix**: Remove `EngineTab` from sidebar and deprecate `ForwardEngine`

### 2. Hardcoded Windows Path in ForwardEngine (High Risk)

- **Issue**: `DATA_DIR = Path("C:/FurayaPromoEngine/data")` hardcoded in `core/forward_engine.py` line 36
- **Risk**: Fails on any system where the user is not "NazaraX" or where `C:/` isn't available
- **Also**: `gui/engine_tab.py` line 29: `DATA_DIR = Path("C:/FurayaPromoEngine/data")`
- **Fix**: Use `Path.home() / "FurayaPromoEngine" / "data"` (already done correctly in `main.py`)

### 3. asyncio.ensure\_future() in Qt Slot Callbacks (Medium Risk)

- **Issue**: All async operations launched from Qt slots using `asyncio.ensure_future()` with no handle to cancel
- **Risk**: If user clicks multiple times rapidly, multiple concurrent async tasks spawn with no deduplication
- **Seen in**: `DiscoveryTab._on_search()`, `DiscoveryTab._on_join()`, `AccountsTab._async_login()`
- **Workaround needed**: Disable buttons during async operation (partially done — search button disabled, join partially)

### 4. QApplication.processEvents() in Async Context (Medium Risk)

- **Issue**: `QApplication.processEvents()` called manually inside `_async_join()` in `discovery_tab.py`
- **Risk**: Can cause re-entrant event processing, potential crashes if user interacts during join loop
- **Location**: `gui/discovery_tab.py` lines 217, 223, 250, 258
- **Note**: This is a common qasync pitfall — `await asyncio.sleep(0)` is safer

### 5. No Session Reconnection on Startup (Medium Risk)

- **Issue**: `Account.client` is `None` until user manually clicks Login in the GUI — even if a session file exists
- **Risk**: After restart, CampaignController refuses to start because `accounts.get_active()` returns `[]`
- **Missing feature**: Auto-reconnect all accounts with existing session files on app startup
- **Files to change**: `AccountsTab.__init__()` or `MainWindow.__init__()`

### 6. Data File Path Inconsistency (Medium Risk)

- **Issue**: Managers use relative paths (`DATA_FILE = Path("data/accounts.json")`) resolved from CWD
- **Relies on**: `os.chdir(str(BASE_DIR))` in `main.py` — if this breaks, all JSON reads fail silently
- **AccountsTab** also hardcodes `DATA_DIR = Path("data")` at line 22
- **Risk**: If any code runs before `os.chdir()`, or if working directory changes, files won't be found

### 7. Duplicate AddAccountDialog (Low Risk)

- **Issue**: `AddAccountDialog` is defined in both `gui/accounts_tab.py` (line 25) AND `gui/add_account_dialog.py`
- **Risk**: Potential divergence if one is updated but not the other
- **Fix**: Delete `gui/add_account_dialog.py` or import from it instead of redefining

### 8. No Account Auto-Reconnect on `client.disconnect()` (Medium Risk)

- **Issue**: Telethon sessions can disconnect after idle periods; no reconnection logic in the campaign loop
- **Workaround**: `PromotionEngine.is_alive()` calls `client.connect()` if disconnected, but this isn't called proactively
- **Risk**: Long-running campaigns may fail silently mid-wave if a client disconnects

### 9. Deprecated Legacy GUI Files (Low Risk)

- `gui/log_tab.py` — replaced by `gui/logs_tab.py`, both exist
- `gui/account_tab.py` — replaced by `gui/accounts_tab.py`, both exist
- Risk: Confusion about which is current, dead code in repo

## Performance Concerns

### Per-Mutation JSON Saves

- Every `groups.record_success()` and `record_failure()` writes the entire groups.json to disk
- At high batch rates this creates excessive I/O — consider batching saves every N operations or on a timer

### No Message/Group Deduplication Check During Campaign

- `TaskQueue.build()` assigns all groups to all accounts — if `groups.json` has duplicates (same group under different usernames), both get targeted

## Security Concerns

### API Credentials in JSON (accounts.json)

- `api_id` and `api_hash` stored in plaintext JSON
- `accounts.json` is gitignored — but if the user's home directory is synced (Dropbox, OneDrive), credentials are exposed
- No encryption of stored credentials

### No Rate Limit Budget Tracking

- The adaptive engine responds to FloodWait errors reactively — no proactive tracking of Telegram's rolling rate limits
- Risk: Getting a FloodWait does not inform the user of account ban risk

## Missing Features (Noted but Not Implemented)

| Feature | Status |
| ------- | ------ |
| Auto-reconnect sessions on startup | Missing |
| Campaign schedule (run at specific times) | Missing |
| Per-account message templates | Not supported |
| Group blacklist | Not implemented |
| Export groups/stats to CSV | Not implemented |
| Proxy support for Telethon | Not implemented |
| Invite link joining (`ImportChatInviteRequest` imported but unused in v2) | Not implemented |
