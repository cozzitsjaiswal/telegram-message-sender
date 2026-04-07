"""
Discovery Tab — production GUI for global Telegram group discovery & join.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  DiscoveryTab (QWidget)                                 │
  │    └── _SearchWorker (asyncio task via qasync)          │
  │          → yields results via asyncio.Queue             │
  │          → _ResultConsumer polls queue, updates GUI     │
  │    └── _JoinWorker (asyncio task)                       │
  │          → force-joins every selected row               │
  │          → emits live row color + counter               │
  └─────────────────────────────────────────────────────────┘

Key design decisions:
  • asyncio.Queue bridges the search generator and GUI updates
    so each result appears in the table the moment it's found.
  • processEvents() is called after every table update so GUI
    never freezes even across 200+ results.
  • Zero skip logic — join always attempts JoinChannelRequest.
  • Keyword input supports comma-separated lists AND multi-line.
  • Search can be CANCELLED mid-run via a cancel flag.
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSpinBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.group_manager import GroupManager, Group
from core.promotion_engine import PromotionEngine

logger = logging.getLogger(__name__)

# ── Row colour palette ─────────────────────────────────────────────────────
_COL = {
    "pending": "#1a1a30",
    "joining": "#1e2840",
    "ok":      "#0b2216",
    "fail":    "#220b0b",
    "header":  "#0d0d1e",
}


# ==========================================================================
# DiscoveryTab
# ==========================================================================

class DiscoveryTab(QWidget):
    groups_updated = pyqtSignal()

    # Internal signals (cross-coroutine safe)
    _sig_result   = pyqtSignal(dict)           # one discovered group
    _sig_status   = pyqtSignal(str, str)       # (text, color)
    _sig_progress = pyqtSignal(int, int)       # (found, limit)
    _sig_search_done = pyqtSignal(int)         # total found
    _sig_row_color = pyqtSignal(int, str)      # (row, color_key)
    _sig_row_label = pyqtSignal(int, str)      # (row, extra_text)
    _sig_join_counter = pyqtSignal(int, int, int)  # (done, joined, failed)

    def __init__(
        self,
        account_manager: AccountManager,
        group_manager: GroupManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.accounts = account_manager
        self.groups   = group_manager
        self._results: List[dict] = []
        self._search_task:  Optional[asyncio.Task] = None
        self._join_task:    Optional[asyncio.Task] = None
        self._cancel_search = False
        self._cancel_join   = False

        self._setup_ui()
        self._connect_signals()

    # -----------------------------------------------------------------------
    # UI build
    # -----------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Title
        title = QLabel("Group Discovery")
        title.setObjectName("label_title")
        root.addWidget(title)

        sub = QLabel(
            "Multi-strategy global search: keyword variations + contacts API + "
            "global message extraction + username probing.  "
            "All results stream live into the table."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#4a5080; font-size:11px;")
        root.addWidget(sub)

        # ── Account + Keyword ──────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Account:"))
        self._acc_combo = QComboBox()
        self._acc_combo.setMinimumWidth(200)
        row1.addWidget(self._acc_combo)

        row1.addWidget(QLabel("Limit/kw:"))
        self._limit = QSpinBox()
        self._limit.setRange(10, 500)
        self._limit.setValue(100)
        self._limit.setFixedWidth(70)
        row1.addWidget(self._limit)

        self._chk_variations = QCheckBox("Keyword variations")
        self._chk_variations.setChecked(True)
        self._chk_variations.setStyleSheet("color:#6070a8;")
        row1.addWidget(self._chk_variations)

        self._chk_probe = QCheckBox("Username probing")
        self._chk_probe.setChecked(True)
        self._chk_probe.setStyleSheet("color:#6070a8;")
        row1.addWidget(self._chk_probe)

        self._chk_auto_join = QCheckBox("Auto-Join immediately")
        self._chk_auto_join.setChecked(False)
        self._chk_auto_join.setStyleSheet("color:#d0a020; font-weight:bold;")
        row1.addWidget(self._chk_auto_join)

        row1.addStretch()
        root.addLayout(row1)

        # Keyword text box (multi-line / comma-separated)
        kw_box = QGroupBox("Keywords  (comma-separated or one per line)")
        kw_lay = QVBoxLayout(kw_box)
        self._keyword_edit = QTextEdit()
        self._keyword_edit.setPlaceholderText(
            "bank account india, usdt, forex signals, crypto trading..."
        )
        self._keyword_edit.setMaximumHeight(72)
        self._keyword_edit.setStyleSheet(
            "background:#0c0c1e; color:#c8c8f0; "
            "border:1px solid #222240; border-radius:5px; padding:6px;"
        )
        kw_lay.addWidget(self._keyword_edit)
        root.addWidget(kw_box)

        # ── Action buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._btn_search = QPushButton("🔍  Search")
        self._btn_search.setObjectName("btn_gold")
        self._btn_search.setMinimumHeight(36)
        self._btn_search.clicked.connect(self._on_search)
        btn_row.addWidget(self._btn_search)

        self._btn_cancel_search = QPushButton("✖  Stop Search")
        self._btn_cancel_search.setObjectName("btn_danger")
        self._btn_cancel_search.setEnabled(False)
        self._btn_cancel_search.clicked.connect(self._on_cancel_search)
        btn_row.addWidget(self._btn_cancel_search)

        btn_row.addStretch()

        self._btn_sel_all = QPushButton("☑ All")
        self._btn_sel_all.setFixedWidth(70)
        self._btn_sel_all.clicked.connect(self._table.selectAll if hasattr(self, "_table") else lambda: None)
        btn_row.addWidget(self._btn_sel_all)

        self._btn_sel_none = QPushButton("☐ None")
        self._btn_sel_none.setFixedWidth(70)
        self._btn_sel_none.clicked.connect(lambda: self._table.clearSelection() if hasattr(self, "_table") else None)
        btn_row.addWidget(self._btn_sel_none)

        root.addLayout(btn_row)

        # ── Status + progress ──────────────────────────────────────────
        status_row = QHBoxLayout()
        self._status = QLabel("Ready — enter keywords and press Search")
        self._status.setStyleSheet("color:#5060a0; font-size:11px;")
        self._status.setWordWrap(True)
        status_row.addWidget(self._status, 3)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(14)
        self._progress.setFormat("%v / %m")
        status_row.addWidget(self._progress, 1)
        root.addLayout(status_row)

        # ── Results table ──────────────────────────────────────────────
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Group Name", "Username", "Members", "Type", "Strategy"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

        # ── Join controls ──────────────────────────────────────────────
        join_box = QGroupBox("Join Controls")
        join_lay = QHBoxLayout(join_box)

        self._btn_sel_all2 = QPushButton("☑ Select All")
        self._btn_sel_all2.clicked.connect(self._table.selectAll)
        join_lay.addWidget(self._btn_sel_all2)

        join_lay.addWidget(QLabel("Delay (s):"))
        self._join_delay = QSpinBox()
        self._join_delay.setRange(1, 120)
        self._join_delay.setValue(6)
        self._join_delay.setFixedWidth(60)
        join_lay.addWidget(self._join_delay)

        self._btn_join = QPushButton("➕  Force Join All Selected")
        self._btn_join.setObjectName("btn_start")
        self._btn_join.setMinimumHeight(38)
        self._btn_join.clicked.connect(self._on_join)
        join_lay.addWidget(self._btn_join)

        self._btn_cancel_join = QPushButton("✖  Stop Joining")
        self._btn_cancel_join.setObjectName("btn_danger")
        self._btn_cancel_join.setEnabled(False)
        self._btn_cancel_join.clicked.connect(self._on_cancel_join)
        join_lay.addWidget(self._btn_cancel_join)

        join_lay.addStretch()

        self._join_counter = QLabel("✅ 0  ❌ 0")
        self._join_counter.setStyleSheet("font-size:13px; font-weight:700; color:#d0a020;")
        join_lay.addWidget(self._join_counter)

        root.addWidget(join_box)

        # Fix btn_sel_all reference now that _table exists
        self._btn_sel_all.clicked.disconnect()
        self._btn_sel_all.clicked.connect(self._table.selectAll)
        self._btn_sel_none.clicked.disconnect()
        self._btn_sel_none.clicked.connect(self._table.clearSelection)

        self._refresh_combo()

    def _connect_signals(self) -> None:
        self._sig_result.connect(self._on_result)
        self._sig_status.connect(self._on_status)
        self._sig_progress.connect(self._on_progress)
        self._sig_search_done.connect(self._on_search_done)
        self._sig_row_color.connect(self._color_row)
        self._sig_row_label.connect(self._label_row)
        self._sig_join_counter.connect(self._on_join_counter)

    # -----------------------------------------------------------------------
    # Combo refresh
    # -----------------------------------------------------------------------

    def _refresh_combo(self) -> None:
        self._acc_combo.clear()
        for acc in self.accounts.get_all():
            icon = "✅" if acc.client else "❌"
            self._acc_combo.addItem(f"{icon} {acc.phone}", acc)

    def on_accounts_changed(self) -> None:
        self._refresh_combo()

    def on_groups_changed(self) -> None:
        pass

    # -----------------------------------------------------------------------
    # Search flow
    # -----------------------------------------------------------------------

    def _on_search(self) -> None:
        acc = self._acc_combo.currentData()
        if not acc or not acc.client:
            self._on_status("❌ Account not logged in — go to Accounts tab", "#e05050")
            return

        raw = self._keyword_edit.toPlainText().strip()
        if not raw:
            self._on_status("❌ Enter at least one keyword", "#e05050")
            return

        # Parse keywords (comma OR newline separated)
        keywords = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
        if not keywords:
            self._on_status("❌ No valid keywords found", "#e05050")
            return

        # Clear table
        self._table.setRowCount(0)
        self._results.clear()
        self._progress.setValue(0)
        self._progress.setMaximum(len(keywords) * self._limit.value())
        self._cancel_search = False

        self._btn_search.setEnabled(False)
        self._btn_cancel_search.setEnabled(True)

        self._search_task = asyncio.ensure_future(
            self._run_search(
                acc, keywords,
                self._limit.value(),
                self._chk_variations.isChecked(),
                self._chk_probe.isChecked(),
                self._chk_auto_join.isChecked(),
                self._join_delay.value(),
            )
        )

    def _on_cancel_search(self) -> None:
        self._cancel_search = True
        if self._search_task and not self._search_task.done():
            self._search_task.cancel()
        self._on_status("🛑 Search cancelled", "#d0a020")
        self._btn_search.setEnabled(True)
        self._btn_cancel_search.setEnabled(False)

    async def _run_search(
        self, account, keywords: List[str], limit_per_kw: int,
        use_variations: bool, use_probe: bool, auto_join: bool, auto_join_delay: int
    ) -> None:
        engine = PromotionEngine(account.client, account.phone)
        total_found = 0
        seen_ids: set = set()

        for i, kw in enumerate(keywords):
            if self._cancel_search:
                break
            self._sig_status.emit(
                f"🔍 [{i+1}/{len(keywords)}] Searching: '{kw}'...",
                "#5ab4f0",
            )
            kw_found = 0
            
            def _status_cb(msg: str):
                self._sig_status.emit(
                    f"🔍 [{i+1}/{len(keywords)}] '{kw}' → {msg} | Total: {total_found}",
                    "#4070c0"
                )
                
            try:
                async for result in engine.discover_groups(
                    kw, limit_per_kw, use_variations, use_probe, status_callback=_status_cb
                ):
                    if self._cancel_search:
                        break
                    eid = getattr(result.get("entity"), "id", None) or result.get("username")
                    if eid in seen_ids:
                        continue
                    seen_ids.add(eid)
                    self._sig_result.emit(result)
                    total_found += 1
                    kw_found += 1
                    self._sig_progress.emit(total_found, len(keywords) * limit_per_kw)
                    # Let status_cb handle the textual updates, but we can do a brief check
                    await asyncio.sleep(0)   # yield to Qt event loop

                    if auto_join and eid:
                        row_idx = total_found - 1
                        self._sig_row_color.emit(row_idx, "joining")
                        self._sig_status.emit(f"➕ Auto-joining: {result['title']}...", "#d0a020")
                        ok, err = await engine.join_group(result["entity"])
                        
                        uname = result.get("username") or f"id_{getattr(result['entity'], 'id', total_found)}"
                        if ok:
                            self._sig_row_color.emit(row_idx, "ok")
                            self._sig_row_label.emit(row_idx, "✅ Joined")
                            existing = self.groups.get_by_username(uname)
                            if existing:
                                existing.joined = True
                                self.groups.save()
                            else:
                                self.groups.add(Group(
                                    username=uname, title=result["title"],
                                    member_count=result.get("member_count", 0), joined=True
                                ))
                            self.groups_updated.emit()
                            self._sig_status.emit(f"✅ Joined: {result['title']}", "#40d060")
                            if auto_join_delay > 0:
                                await asyncio.sleep(auto_join_delay)
                        else:
                            self._sig_row_color.emit(row_idx, "fail")
                            self._sig_row_label.emit(row_idx, f"❌ {err}")
                            self._sig_status.emit(f"❌ Failed to join: {result['title']} ({err})", "#e05050")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._sig_status.emit(f"⚠️ '{kw}': {exc}", "#c07020")
            if i < len(keywords) - 1 and not self._cancel_search:
                await asyncio.sleep(1.0)   # brief pause between keyword batches

        self._sig_search_done.emit(total_found)

    # -----------------------------------------------------------------------
    # Signal handlers — these run in the Qt main thread
    # -----------------------------------------------------------------------

    def _on_result(self, r: dict) -> None:
        """Append one result to the table immediately."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._results.append(r)

        name_item = QTableWidgetItem(r["title"])
        name_item.setData(Qt.UserRole, len(self._results) - 1)
        self._table.setItem(row, 0, name_item)

        uname = r.get("username") or f"id:{getattr(r.get('entity'), 'id', '?')}"
        self._table.setItem(row, 1, QTableWidgetItem(uname))
        self._table.setItem(row, 2, QTableWidgetItem(f"{r.get('member_count', 0):,}"))

        kind = "📡 Channel" if r.get("is_channel") else "👥 Group"
        ki = QTableWidgetItem(kind)
        ki.setForeground(QColor("#5ab4f0") if r.get("is_channel") else QColor("#40c080"))
        self._table.setItem(row, 3, ki)

        strat = r.get("strategy", "")
        si = QTableWidgetItem(strat)
        si.setForeground(QColor("#4a3a70"))
        si.setFont(QFont("Consolas", 9))
        self._table.setItem(row, 4, si)

        self._table.setRowHeight(row, 34)
        QApplication.processEvents()

    def _on_status(self, text: str, color: str = "#5060a0") -> None:
        self._status.setText(text)
        self._status.setStyleSheet(f"color:{color}; font-size:11px;")
        QApplication.processEvents()

    def _on_progress(self, found: int, total: int) -> None:
        self._progress.setMaximum(max(total, 1))
        self._progress.setValue(found)
        self._progress.setFormat(f"{found} found")

    def _on_search_done(self, total: int) -> None:
        self._btn_search.setEnabled(True)
        self._btn_cancel_search.setEnabled(False)
        if total:
            self._on_status(
                f"✅ Done — {total} unique groups/channels found",
                "#40d060",
            )
        else:
            self._on_status(
                "⚠️ No results. Check: account is authed, keywords are in English, "
                "or try turning off 'variations' for exact match.",
                "#d07020",
            )
        self._progress.setValue(self._progress.maximum())

    # -----------------------------------------------------------------------
    # Join flow
    # -----------------------------------------------------------------------

    def _on_join(self) -> None:
        rows = sorted(set(i.row() for i in self._table.selectedItems()))
        if not rows:
            self._on_status("⚠️ Select at least one group to join", "#d07020")
            return
        acc = self._acc_combo.currentData()
        if not acc or not acc.client:
            self._on_status("❌ Account not logged in", "#e05050")
            return

        self._cancel_join = False
        self._btn_join.setEnabled(False)
        self._btn_cancel_join.setEnabled(True)
        self._join_counter.setText("✅ 0  ❌ 0")

        self._join_task = asyncio.ensure_future(
            self._run_join(acc, rows, self._join_delay.value())
        )

    def _on_cancel_join(self) -> None:
        self._cancel_join = True
        if self._join_task and not self._join_task.done():
            self._join_task.cancel()
        self._on_status("🛑 Join cancelled", "#d0a020")
        self._btn_join.setEnabled(True)
        self._btn_cancel_join.setEnabled(False)

    async def _run_join(self, account, rows: List[int], delay: int) -> None:
        engine = PromotionEngine(account.client, account.phone)
        joined = 0
        failed = 0
        total = len(rows)

        for i, row in enumerate(rows):
            if self._cancel_join:
                break
            if row >= len(self._results):
                continue

            r = self._results[row]
            entity = r.get("entity")
            uname = r.get("username") or f"id_{getattr(entity, 'id', row)}"

            # Live "joining" highlight + status
            self._sig_row_color.emit(row, "joining")
            self._sig_status.emit(
                f"➕ [{i+1}/{total}] Joining: {r['title']}  |  ✅ {joined}  ❌ {failed}",
                "#5ab4f0",
            )
            await asyncio.sleep(0)

            if not entity:
                failed += 1
                self._sig_row_color.emit(row, "fail")
                self._sig_row_label.emit(row, "❌ no entity")
                self._sig_join_counter.emit(i + 1, joined, failed)
                continue

            # ── FORCE JOIN ─────────────────────────────────────────────
            ok, err = await engine.join_group(entity)

            if ok:
                joined += 1
                self._sig_row_color.emit(row, "ok")
                self._sig_row_label.emit(row, "✅ Joined")
                # Upsert into group manager
                existing = self.groups.get_by_username(uname)
                if existing:
                    existing.joined = True
                    self.groups.save()
                else:
                    self.groups.add(Group(
                        username=uname,
                        title=r["title"],
                        member_count=r.get("member_count", 0),
                        joined=True,
                    ))
                self._sig_status.emit(
                    f"✅ [{i+1}/{total}] Joined: {r['title']}  |  ✅ {joined}  ❌ {failed}",
                    "#40d060",
                )
            else:
                failed += 1
                self._sig_row_color.emit(row, "fail")
                self._sig_row_label.emit(row, f"❌ {err}")
                self._sig_status.emit(
                    f"❌ [{i+1}/{total}] {r['title']} — {err}  |  ✅ {joined}  ❌ {failed}",
                    "#e05050",
                )

            self._sig_join_counter.emit(i + 1, joined, failed)

            # Countdown between joins
            if i < total - 1 and delay > 0 and not self._cancel_join:
                for remaining in range(delay, 0, -1):
                    if self._cancel_join:
                        break
                    self._sig_status.emit(
                        f"⏱ Next join in {remaining}s  |  [{i+1}/{total}]  ✅ {joined}  ❌ {failed}",
                        "#6060a0",
                    )
                    await asyncio.sleep(1)

        # Done
        color = "#40d060" if joined > 0 else "#e05050"
        self._sig_status.emit(
            f"🏁 Done — Joined: {joined} / {total}  |  Failed: {failed}",
            color,
        )
        self._btn_join.setEnabled(True)
        self._btn_cancel_join.setEnabled(False)
        self.groups_updated.emit()

    # -----------------------------------------------------------------------
    # Row helpers  (connected to signals — always run on Qt thread)
    # -----------------------------------------------------------------------

    def _color_row(self, row: int, state: str) -> None:
        bg = QColor(_COL.get(state, "#151528"))
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item:
                item.setBackground(bg)
        QApplication.processEvents()

    def _label_row(self, row: int, text: str) -> None:
        """Append status badge to the group name cell."""
        item = self._table.item(row, 0)
        if item:
            base = item.text().split(" │")[0]
            item.setText(f"{base} │ {text}")
        QApplication.processEvents()

    def _on_join_counter(self, done: int, joined: int, failed: int) -> None:
        self._join_counter.setText(f"✅ {joined}  ❌ {failed}")
        rate = round(joined / done * 100) if done else 0
        color = "#40d060" if rate >= 60 else "#d0a020" if rate >= 30 else "#e05050"
        self._join_counter.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{color};"
        )
