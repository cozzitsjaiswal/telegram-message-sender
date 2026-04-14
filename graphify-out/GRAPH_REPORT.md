# Graph Report - .  (2026-04-15)

## Corpus Check
- Corpus is ~22,285 words - fits in a single context window. You may not need a graph.

## Summary
- 592 nodes · 1005 edges · 33 communities detected
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 181 edges (avg confidence: 0.51)
- Token cost: 850 input · 420 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Group Discovery & Promotion|Group Discovery & Promotion]]
- [[_COMMUNITY_Campaign Controller & Autopilot|Campaign Controller & Autopilot]]
- [[_COMMUNITY_Content Forwarder|Content Forwarder]]
- [[_COMMUNITY_Message Engine|Message Engine]]
- [[_COMMUNITY_Account Manager|Account Manager]]
- [[_COMMUNITY_Smart Messenger|Smart Messenger]]
- [[_COMMUNITY_Accounts Tab UI|Accounts Tab UI]]
- [[_COMMUNITY_App Entry & Main Window|App Entry & Main Window]]
- [[_COMMUNITY_Analytics Tab|Analytics Tab]]
- [[_COMMUNITY_Autopilot Engine|Autopilot Engine]]
- [[_COMMUNITY_Engine Control Tab|Engine Control Tab]]
- [[_COMMUNITY_Advanced Scraper|Advanced Scraper]]
- [[_COMMUNITY_Member Adder|Member Adder]]
- [[_COMMUNITY_Dashboard Tab|Dashboard Tab]]
- [[_COMMUNITY_TDLib Engine|TDLib Engine]]
- [[_COMMUNITY_Account Auth Flow|Account Auth Flow]]
- [[_COMMUNITY_Adaptive Engine|Adaptive Engine]]
- [[_COMMUNITY_README & Docs|README & Docs]]
- [[_COMMUNITY_Adder Tab UI|Adder Tab UI]]
- [[_COMMUNITY_Groups Tab UI|Groups Tab UI]]
- [[_COMMUNITY_TDLib Tests|TDLib Tests]]
- [[_COMMUNITY_Icon Builder|Icon Builder]]
- [[_COMMUNITY_UI Styles|UI Styles]]
- [[_COMMUNITY_Installer Script|Installer Script]]
- [[_COMMUNITY_TDLib Test Stub 1|TDLib Test Stub 1]]
- [[_COMMUNITY_TDLib Test Stub 2|TDLib Test Stub 2]]
- [[_COMMUNITY_Env Check Script|Env Check Script]]
- [[_COMMUNITY_Final Build Script|Final Build Script]]
- [[_COMMUNITY_Zip Packager|Zip Packager]]
- [[_COMMUNITY_Package Script|Package Script]]
- [[_COMMUNITY_Smart Messenger Rationale|Smart Messenger Rationale]]
- [[_COMMUNITY_Core Package Init|Core Package Init]]
- [[_COMMUNITY_GUI Package Init|GUI Package Init]]

## God Nodes (most connected - your core abstractions)
1. `MainWindow` - 48 edges
2. `AccountManager` - 43 edges
3. `GroupManager` - 35 edges
4. `MessageEngine` - 31 edges
5. `DiscoveryTab` - 27 edges
6. `CampaignController` - 26 edges
7. `AutoPilot` - 24 edges
8. `MainWindow — Left sidebar navigation + stacked content panels.  Full integrati` - 22 edges
9. `ContentForwarder` - 21 edges
10. `AutoPilotTab` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Accounts Tab — add, login, remove multiple Telegram accounts.` --uses--> `AccountManager`  [INFERRED]
  gui\accounts_tab.py → core\account_manager.py
- `core/account_manager.py – Multi‑account management with TDLib backend` --uses--> `TDLibEngine`  [INFERRED]
  core\account_manager.py → core\tdlib_engine.py
- `Groups Tab — view joined groups, their stats, and manage them.` --uses--> `GroupManager`  [INFERRED]
  gui\groups_tab.py → core\group_manager.py
- `Furaya Campaign System — Entry point.` --uses--> `MainWindow`  [INFERRED]
  main.py → gui\main_window.py
- `AccountManager` --uses--> `TDLibEngine`  [INFERRED]
  core\account_manager.py → core\tdlib_engine.py

## Hyperedges (group relationships)
- **Core UI + Async Stack** — req_pyqt5, req_qasync, req_telethon [EXTRACTED 0.95]

## Communities

### Community 0 - "Group Discovery & Promotion"
Cohesion: 0.05
Nodes (19): DiscoveryTab, Discovery Tab — production GUI for global Telegram group discovery & join.  Ar, Append one result to the table immediately., Append status badge to the group name cell., from_dict(), Group, GroupManager, Group model and GroupManager — persists all discovered/joined groups. (+11 more)

### Community 1 - "Campaign Controller & Autopilot"
Cohesion: 0.06
Nodes (18): CampaignMode, Phase, CampaignController, CampaignState, CampaignController — the brain. Orchestrates all modules., The executive brain of the system.     Wires together: AccountManager, GroupMan, CampaignTab, Campaign Tab — start/stop/pause controller with mode + batch config. (+10 more)

### Community 2 - "Content Forwarder"
Cohesion: 0.07
Nodes (14): ContentForwarder, ForwardRule, ForwardStats, from_dict(), core/content_forwarder.py  Rule-based auto-forwarder that monitors source chats, Manages forwarding rules and registers Telethon event handlers.      Sample rule, Register the event handler to start monitoring source chats., Unregister the event handler. (+6 more)

### Community 3 - "Message Engine"
Cohesion: 0.1
Nodes (9): from_dict(), MessageEngine, MessageTemplate, MessageEngine — stores templates, rotates, adds micro-variations., Apply subtle micro-variation to avoid identical sends., Return next message in rotation — never repeats consecutively., EditDialog, MessagesTab (+1 more)

### Community 4 - "Account Manager"
Cohesion: 0.08
Nodes (6): AccountManager, core/account_manager.py – Multi‑account management with TDLib backend, AutoPilotTab, gui/autopilot_tab.py — Command center for the fully autonomous 24/7 engine.  D, Called when the app is closing., Periodic health table + gauge refresh.

### Community 5 - "Smart Messenger"
Cohesion: 0.09
Nodes (8): MessengerTab, gui/messenger_tab.py — PyQt5 tab for SmartMessenger campaigns., CampaignResult, core/smart_messenger.py  Multi-account message distributor with round-robin ac, Clear dedup history for a campaign. Returns number of entries removed., Distribute messages across accounts with round-robin rotation.         Handles, Multi-account message distributor with deduplication., SmartMessenger

### Community 6 - "Accounts Tab UI"
Cohesion: 0.1
Nodes (10): AccountsTab, AddAccountDialog, Accounts Tab — add, login, remove multiple Telegram accounts., account(), AddAccountDialog, Add Account dialog – collects phone, API ID, API Hash., MainWindow — Left sidebar navigation + stacked content panels.  Full integrati, QDialog (+2 more)

### Community 7 - "App Entry & Main Window"
Cohesion: 0.11
Nodes (3): Furaya Campaign System — Entry point., MainWindow, QMainWindow

### Community 8 - "Analytics Tab"
Cohesion: 0.11
Nodes (6): AnalyticsTab, Analytics Tab — account performance table and session history., AccountMetrics, PerformanceTracker, PerformanceTracker — records and persists all campaign metrics., SessionRecord

### Community 9 - "Autopilot Engine"
Cohesion: 0.17
Nodes (4): AutoPilot, AutoPilotStats, CycleConfig, core/autopilot.py  — Enterprise TDLib Engine v5.0  Full autonomous 24/7 engine u

### Community 10 - "Engine Control Tab"
Cohesion: 0.15
Nodes (6): EngineTab, Engine tab — Keywords, promo post, mode, and the big START/STOP controls., Main control panel — keywords, promo, start/stop., EngineStats, ForwardEngine, The core forwarding engine.

### Community 11 - "Advanced Scraper"
Cohesion: 0.11
Nodes (8): AdvancedScraper, core/advanced_scraper.py  Production-grade Telegram scraping engine for Furaya C, Scrapes a list of users from a Telegram group. Requires Admin/visibility rights, Searches ALL of public Telegram indexed messages for a particular keyword., Handles robust scraping operations across Telegram channels/groups., Scrape messages from a specific channel/chat, respecting 100 msg/min limits., gui/scraper_tab.py — PyQt5 tab for AdvancedScraper operations. Scrape messages,, ScraperTab

### Community 12 - "Member Adder"
Cohesion: 0.13
Nodes (9): AddStats, core/member_adder.py  Smart member adder with hard 20-adds/hour rate cap, admin/, Try direct InviteToChannel (admin). On ChatAdminRequired, skip.         Always r, Load users from CSV (first column) and add them to group.         Enforces 20/ho, Bulk add a list of user identifiers., Adds users to a group with:     - Hard limit: 20 adds / hour / account     - Adm, Enforce 20 adds/hour hard limit., Returns seconds to wait until next slot opens. (+1 more)

### Community 13 - "Dashboard Tab"
Cohesion: 0.1
Nodes (9): DashboardTab, _kpi_card(), Dashboard Tab — live KPI cards, system health, event feed., LogTab, Log tab – colour-coded, timestamped log display., Append a coloured log line. Thread-safe via Qt signal queuing., LogsTab, Logs Tab — color-coded live log viewer. (+1 more)

### Community 14 - "TDLib Engine"
Cohesion: 0.1
Nodes (10): core/tdlib_engine.py Production TDLib client with full async support for PyQt5, Called from GUI to provide OTP, Send a message – returns message info, Join by username or invite link, Get members of a supergroup (requires supergroup ID), Search for public groups/channels, Get current user info, Single TDLib client with automatic state machine and Qt callbacks (+2 more)

### Community 15 - "Account Auth Flow"
Cohesion: 0.14
Nodes (6): account(), AccountTab, Account tab — Add a Telegram account and log in once., Single-account login panel., OtpDialog, OTP dialog – shown during account login when Telegram sends a code.

### Community 16 - "Adaptive Engine"
Cohesion: 0.13
Nodes (4): AdaptiveEngine, ModeConfig, AdaptiveEngine — dynamically adjusts delays and batch sizes., Reads real-time error metrics and adjusts execution parameters.

### Community 17 - "README & Docs"
Cohesion: 0.19
Nodes (14): Account Rotation, FloodWait Error Handling, Furaya Promo Engine, Message Templates, Multi-Account Management, OTP Login Flow, PyInstaller EXE Build, Session Persistence (+6 more)

### Community 18 - "Adder Tab UI"
Cohesion: 0.24
Nodes (2): AdderTab, gui/adder_tab.py — PyQt5 tab for SmartMemberAdder.

### Community 19 - "Groups Tab UI"
Cohesion: 0.39
Nodes (2): GroupsTab, Groups Tab — view joined groups, their stats, and manage them.

### Community 20 - "TDLib Tests"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Icon Builder"
Cohesion: 1.0
Nodes (1): Convert Furaya PNG logo to a proper multi-size .ico file.

### Community 22 - "UI Styles"
Cohesion: 1.0
Nodes (1): Dark futuristic theme — Black/Red/Gold with glow accents.

### Community 23 - "Installer Script"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "TDLib Test Stub 1"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "TDLib Test Stub 2"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Env Check Script"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Final Build Script"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Zip Packager"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Package Script"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Smart Messenger Rationale"
Cohesion: 1.0
Nodes (1): Load user identifiers from a CSV. First column = username/id.

### Community 31 - "Core Package Init"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "GUI Package Init"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **68 isolated node(s):** `Convert Furaya PNG logo to a proper multi-size .ico file.`, `AdaptiveEngine — dynamically adjusts delays and batch sizes.`, `Reads real-time error metrics and adjusts execution parameters.`, `core/advanced_scraper.py  Production-grade Telegram scraping engine for Furaya C`, `Handles robust scraping operations across Telegram channels/groups.` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `TDLib Tests`** (2 nodes): `test_tdlib_standalone.py`, `test()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Icon Builder`** (2 nodes): `_make_ico.py`, `Convert Furaya PNG logo to a proper multi-size .ico file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `UI Styles`** (2 nodes): `styles.py`, `Dark futuristic theme — Black/Red/Gold with glow accents.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Installer Script`** (1 nodes): `installer.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TDLib Test Stub 1`** (1 nodes): `tdlib_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TDLib Test Stub 2`** (1 nodes): `tdlib_test2.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Env Check Script`** (1 nodes): `_check.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Final Build Script`** (1 nodes): `_final.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Zip Packager`** (1 nodes): `_make_zip.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Script`** (1 nodes): `_package.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Smart Messenger Rationale`** (1 nodes): `Load user identifiers from a CSV. First column = username/id.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GUI Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AccountManager` connect `Account Manager` to `Group Discovery & Promotion`, `Campaign Controller & Autopilot`, `Content Forwarder`, `Smart Messenger`, `Accounts Tab UI`, `App Entry & Main Window`, `Autopilot Engine`, `Advanced Scraper`, `TDLib Engine`, `Adder Tab UI`?**
  _High betweenness centrality (0.238) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `App Entry & Main Window` to `Group Discovery & Promotion`, `Campaign Controller & Autopilot`, `Content Forwarder`, `Message Engine`, `Account Manager`, `Smart Messenger`, `Accounts Tab UI`, `Analytics Tab`, `Advanced Scraper`, `Dashboard Tab`, `Adder Tab UI`, `Groups Tab UI`?**
  _High betweenness centrality (0.221) - this node is a cross-community bridge._
- **Why does `MainWindow — Left sidebar navigation + stacked content panels.  Full integrati` connect `Accounts Tab UI` to `Group Discovery & Promotion`, `Campaign Controller & Autopilot`, `Content Forwarder`, `Message Engine`, `Account Manager`, `Smart Messenger`, `Analytics Tab`, `Advanced Scraper`, `Dashboard Tab`, `Adder Tab UI`, `Groups Tab UI`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `MainWindow` (e.g. with `Furaya Campaign System — Entry point.` and `AccountManager`) actually correct?**
  _`MainWindow` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `AccountManager` (e.g. with `TDLibEngine` and `Phase`) actually correct?**
  _`AccountManager` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `GroupManager` (e.g. with `Phase` and `AutoPilotStats`) actually correct?**
  _`GroupManager` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `MessageEngine` (e.g. with `Phase` and `AutoPilotStats`) actually correct?**
  _`MessageEngine` has 18 INFERRED edges - model-reasoned connections that need verification._