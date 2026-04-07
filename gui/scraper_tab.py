"""
gui/scraper_tab.py — PyQt5 tab for AdvancedScraper operations.
Scrape messages, members, or search globally — all async with live progress.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSpinBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.advanced_scraper import AdvancedScraper

logger = logging.getLogger(__name__)


class ScraperTab(QWidget):
    _sig_status = pyqtSignal(str, str)
    _sig_progress = pyqtSignal(int, int, str)
    _sig_row = pyqtSignal(dict)

    def __init__(self, account_manager: AccountManager, parent=None):
        super().__init__(parent)
        self.accounts = account_manager
        self._task: Optional[asyncio.Task] = None
        self._setup_ui()
        self._sig_status.connect(self._on_status)
        self._sig_progress.connect(self._on_progress)
        self._sig_row.connect(self._on_row)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Advanced Scraper")
        title.setObjectName("label_title")
        root.addWidget(title)

        sub = QLabel("Scrape messages from channels, members from groups, or search globally.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#4a5080; font-size:11px;")
        root.addWidget(sub)

        # Controls
        ctrl = QHBoxLayout()

        ctrl.addWidget(QLabel("Account:"))
        self._acc_combo = QComboBox()
        self._acc_combo.setMinimumWidth(180)
        ctrl.addWidget(self._acc_combo)

        ctrl.addWidget(QLabel("Mode:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Channel Messages", "Group Members", "Global Search"])
        ctrl.addWidget(self._mode_combo)

        ctrl.addWidget(QLabel("Target:"))
        self._target_edit = QLineEdit()
        self._target_edit.setPlaceholderText("@channel or keyword...")
        self._target_edit.setMinimumWidth(200)
        ctrl.addWidget(self._target_edit)

        ctrl.addWidget(QLabel("Limit:"))
        self._limit = QSpinBox()
        self._limit.setRange(10, 10000)
        self._limit.setValue(500)
        self._limit.setFixedWidth(80)
        ctrl.addWidget(self._limit)

        ctrl.addStretch()
        root.addLayout(ctrl)

        # Action buttons
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("▶  Start Scraping")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setMinimumHeight(36)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("✖  Stop")
        self._btn_stop.setObjectName("btn_danger")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_stop)

        btn_row.addStretch()
        root.addLayout(btn_row)

        # Status + Progress
        status_row = QHBoxLayout()
        self._status = QLabel("Ready")
        self._status.setStyleSheet("color:#5060a0; font-size:11px;")
        self._status.setWordWrap(True)
        status_row.addWidget(self._status, 3)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setFixedHeight(14)
        status_row.addWidget(self._progress, 1)
        root.addLayout(status_row)

        # Results table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Date", "Content/Info", "Extra"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

        self._refresh_combo()

    def _refresh_combo(self):
        self._acc_combo.clear()
        for acc in self.accounts.get_all():
            icon = "✅" if acc.client else "❌"
            self._acc_combo.addItem(f"{icon} {acc.phone}", acc)

    def on_accounts_changed(self):
        self._refresh_combo()

    def _on_start(self):
        acc = self._acc_combo.currentData()
        if not acc or not acc.client:
            self._on_status("❌ Account not logged in", "#e05050")
            return
        target = self._target_edit.text().strip()
        if not target:
            self._on_status("❌ Enter a target", "#e05050")
            return

        self._table.setRowCount(0)
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

        mode = self._mode_combo.currentIndex()
        self._task = asyncio.ensure_future(
            self._run_scrape(acc, mode, target, self._limit.value())
        )

    def _on_stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._on_status("🛑 Stopped", "#d0a020")

    async def _run_scrape(self, account, mode: int, target: str, limit: int):
        scraper = AdvancedScraper(account.client, account.phone)

        def _progress(curr, total, msg):
            self._sig_progress.emit(curr, total, msg)

        try:
            if mode == 0:  # Channel Messages
                results = await scraper.scrape_channel_messages(target, limit, on_progress=_progress)
                for r in results:
                    self._sig_row.emit(r)
            elif mode == 1:  # Group Members
                results = await scraper.scrape_group_members(target, limit, on_progress=_progress)
                for r in results:
                    self._sig_row.emit({
                        "id": r["id"],
                        "date": "",
                        "text": f"@{r.get('username', '?')} — {r.get('first_name', '')} {r.get('last_name', '')}",
                        "views": "Premium" if r.get("is_premium") else "",
                    })
            else:  # Global Search
                results = await scraper.search_global(target, limit, on_progress=_progress)
                for r in results:
                    self._sig_row.emit(r)

            self._sig_status.emit(f"✅ Scraped {len(results)} results", "#40d060")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._sig_status.emit(f"❌ Error: {e}", "#e05050")
        finally:
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)

    def _on_status(self, text, color="#5060a0"):
        self._status.setText(text)
        self._status.setStyleSheet(f"color:{color}; font-size:11px;")

    def _on_progress(self, curr, total, msg):
        self._progress.setMaximum(max(total, 1))
        self._progress.setValue(curr)
        self._status.setText(msg)
        QApplication.processEvents()

    def _on_row(self, r: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(str(r.get("id", ""))))
        self._table.setItem(row, 1, QTableWidgetItem(str(r.get("date", ""))))
        text = r.get("text", "") or ""
        self._table.setItem(row, 2, QTableWidgetItem(text[:200]))
        extra = str(r.get("views", r.get("source_username", "")))
        self._table.setItem(row, 3, QTableWidgetItem(extra))
        self._table.setRowHeight(row, 30)
