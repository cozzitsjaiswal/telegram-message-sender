"""
gui/main_window.py — Furaya v5.5
Simplified pipeline-focused layout. 6 tabs, clean sidebar.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QStackedWidget, QStatusBar, QVBoxLayout,
    QWidget, QFrame,
)

from core.account_manager import AccountManager
from core.promo_pipeline import PromoPipeline

from gui.accounts_tab import AccountsTab
from gui.pipeline_tab import PipelineTab
from gui.logs_tab import LogsTab

logger = logging.getLogger(__name__)


def _make_sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("border: none; border-top: 1px solid rgba(0,212,255,0.06); margin: 4px 16px;")
    return f


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Furaya — Autonomous Campaign System v5.5")
        self.setMinimumSize(1050, 680)
        self.resize(1280, 820)

        self.app_dir = Path.home() / "FurayaPromoEngine"
        self.app_dir.mkdir(parents=True, exist_ok=True)

        # ── Resolve tdjson.dll ──────────────────────────────────────────
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent
        self.tdlib_dll = base_path / "tdjson.dll"

        # ── Core managers ───────────────────────────────────────────────
        self._accounts = AccountManager(
            data_path=self.app_dir / "data",
            tdlib_dll_path=self.tdlib_dll,
            log_cb=self._on_log,
        )

        self._pipeline = PromoPipeline(
            account_manager=self._accounts,
            log_cb=self._on_log,
            metrics_cb=self._on_metrics,
            status_cb=self._on_pipeline_status,
        )

        self._setup_ui()

    # ── UI setup ─────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QWidget()
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.setCentralWidget(root)

        # ── SIDEBAR ───────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # Logo block
        logo_w = QWidget()
        logo_lay = QVBoxLayout(logo_w)
        logo_lay.setContentsMargins(20, 24, 20, 16)
        logo_lay.setSpacing(2)
        logo = QLabel("FURAYA")
        logo.setObjectName("logo_label")
        ver = QLabel("v5.5  ENTERPRISE")
        ver.setObjectName("version_label")
        logo_lay.addWidget(logo)
        logo_lay.addWidget(ver)
        sb_lay.addWidget(logo_w)
        sb_lay.addWidget(_make_sep())

        # Navigation
        self._stack = QStackedWidget()
        nav_items = [
            ("🤖", "AutoPilot", self._make_pipeline()),
            ("👤", "Accounts", self._make_accounts()),
            ("📋", "Logs", self._make_logs()),
        ]

        self._nav_buttons: list[QPushButton] = []
        for i, (icon, label, widget) in enumerate(nav_items):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("sidebar_btn")
            btn.setFixedHeight(44)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sb_lay.addWidget(btn)
            self._nav_buttons.append(btn)
            self._stack.addWidget(widget)

        sb_lay.addStretch()
        sb_lay.addWidget(_make_sep())

        # System status in sidebar
        self._pipeline_status = QLabel("○  Idle")
        self._pipeline_status.setObjectName("status_dot")
        self._pipeline_status.setStyleSheet("color: #304050; padding: 10px 20px; font-size: 11px;")
        sb_lay.addWidget(self._pipeline_status)

        # Account count
        self._acct_count = QLabel("0 accounts")
        self._acct_count.setStyleSheet("color: #202a35; padding: 0 20px 16px 20px; font-size: 10px;")
        sb_lay.addWidget(self._acct_count)

        root_lay.addWidget(sidebar)
        root_lay.addWidget(self._stack, 1)

        # ── Status bar ────────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_lbl = QLabel("Furaya v5.5  |  Ready")
        self._status_lbl.setStyleSheet("color: #304050; padding: 0 8px;")
        self._status_bar.addPermanentWidget(self._status_lbl)

        # Start on Pipeline tab
        self._switch(0)

        # Refresh sidebar status every 2s
        self._sidebar_timer = QTimer()
        self._sidebar_timer.timeout.connect(self._refresh_sidebar)
        self._sidebar_timer.start(2000)

    def _switch(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Tab factories ─────────────────────────────────────────────────

    def _make_pipeline(self) -> QWidget:
        self._pipeline_tab = PipelineTab(self._accounts, self._pipeline)
        self._pipeline_tab.log_requested.connect(self._on_log)
        return self._pipeline_tab

    def _make_accounts(self) -> QWidget:
        self._accounts_tab = AccountsTab(self._accounts)
        self._accounts_tab.accounts_changed.connect(self._on_accounts_changed)
        return self._accounts_tab

    def _make_logs(self) -> QWidget:
        self._logs_tab = LogsTab()
        return self._logs_tab

    # ── Callbacks ─────────────────────────────────────────────────────

    def _on_log(self, level: str, msg: str) -> None:
        try:
            self._logs_tab.append(level, msg)
        except Exception:
            pass

    def _on_metrics(self, m: dict) -> None:
        sent = m.get("sent", 0)
        joined = m.get("joined", 0)
        found = m.get("discovered", 0)
        phase = m.get("phase", "Idle")
        self._status_lbl.setText(
            f"Phase: {phase}  |  Found: {found}  |  Joined: {joined}  |  Sent: {sent}"
        )

    def _on_pipeline_status(self, phase: str) -> None:
        colors = {
            "Discovering Groups": "#00d4ff",
            "Joining Groups": "#ffd700",
            "Sending Promotions": "#00ff88",
            "Done": "#00ff88",
            "Error": "#ff3366",
            "Idle": "#304050",
            "Paused": "#ffd700",
        }
        color = colors.get(phase, "#304050")
        self._pipeline_status.setText(f"●  {phase}")
        self._pipeline_status.setStyleSheet(
            f"color: {color}; padding: 10px 20px; font-size: 11px; font-weight: 700;"
        )

    def _on_accounts_changed(self) -> None:
        self._refresh_sidebar()

    def _refresh_sidebar(self) -> None:
        n = self._accounts.logged_in_count
        t = self._accounts.total_count
        self._acct_count.setText(f"{n}/{t} accounts connected")
        col = "#00ff88" if n > 0 else "#304050"
        self._acct_count.setStyleSheet(f"color: {col}; padding: 0 20px 16px 20px; font-size: 10px;")

    # ── Close ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._pipeline.stop()
        asyncio.ensure_future(self._accounts.stop_all())
        super().closeEvent(event)
