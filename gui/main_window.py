"""MainWindow — Left sidebar navigation + stacked content panels."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.campaign_controller import CampaignController
from core.group_manager import GroupManager
from core.message_engine import MessageEngine
from core.performance_tracker import PerformanceTracker

from gui.accounts_tab   import AccountsTab
from gui.analytics_tab  import AnalyticsTab
from gui.campaign_tab   import CampaignTab
from gui.dashboard_tab  import DashboardTab
from gui.discovery_tab  import DiscoveryTab
from gui.groups_tab     import GroupsTab
from gui.logs_tab       import LogsTab
from gui.messages_tab   import MessagesTab

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Furaya — Campaign Control System")
        self.setMinimumSize(1100, 700)
        self.resize(1260, 800)

        # ── Shared core modules ──────────────────────────────────────
        self._accounts = AccountManager()
        self._groups   = GroupManager()
        self._messages = MessageEngine()
        self._perf     = PerformanceTracker()

        # ── Controller (brain) ───────────────────────────────────────
        self._ctrl = CampaignController(
            account_manager   = self._accounts,
            group_manager     = self._groups,
            message_engine    = self._messages,
            performance_tracker = self._perf,
            log_cb    = self._on_log,
            metrics_cb= self._on_metrics,
            state_cb  = self._on_state,
        )

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QWidget()
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.setCentralWidget(root)

        # ── LEFT SIDEBAR ─────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(0, 0, 0, 0)
        sidebar_lay.setSpacing(0)

        logo = QLabel("FURAYA")
        logo.setObjectName("logo_label")
        sidebar_lay.addWidget(logo)

        ver = QLabel("v2.0  Campaign System")
        ver.setObjectName("version_label")
        sidebar_lay.addWidget(ver)

        # ── Tabs ─────────────────────────────────────────────────────
        self._stack = QStackedWidget()

        nav_items = [
            ("📊  Dashboard",   self._make_dashboard()),
            ("🚀  Campaign",    self._make_campaign()),
            ("👤  Accounts",    self._make_accounts()),
            ("👥  Groups",      self._make_groups()),
            ("🔍  Discovery",   self._make_discovery()),
            ("✉️   Messages",   self._make_messages()),
            ("📈  Analytics",   self._make_analytics()),
            ("📋  Logs",        self._make_logs()),
        ]

        self._nav_buttons: list[QPushButton] = []
        for i, (label, widget) in enumerate(nav_items):
            btn = QPushButton(label)
            btn.setObjectName("sidebar_btn")
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked, idx=i: self._switch(idx))
            sidebar_lay.addWidget(btn)
            self._nav_buttons.append(btn)
            self._stack.addWidget(widget)

        sidebar_lay.addStretch()

        # System health indicator in sidebar
        self._sidebar_status = QLabel("● Idle")
        self._sidebar_status.setStyleSheet("color:#303060; padding:8px 16px; font-size:11px;")
        sidebar_lay.addWidget(self._sidebar_status)

        root_lay.addWidget(sidebar)
        root_lay.addWidget(self._stack, 1)

        # ── Status bar ───────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_lbl = QLabel("Furaya System — Ready")
        self._status_bar.addPermanentWidget(self._status_lbl)

        self._switch(0)

    def _switch(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ------------------------------------------------------------------
    # Tab factories
    # ------------------------------------------------------------------

    def _make_dashboard(self) -> QWidget:
        self._dashboard = DashboardTab()
        return self._dashboard

    def _make_campaign(self) -> QWidget:
        self._campaign_tab = CampaignTab(self._ctrl)
        self._campaign_tab.log_requested.connect(self._on_log)
        return self._campaign_tab

    def _make_accounts(self) -> QWidget:
        self._accounts_tab = AccountsTab(self._accounts)
        self._accounts_tab.accounts_changed.connect(self._on_accounts_changed)
        return self._accounts_tab

    def _make_groups(self) -> QWidget:
        self._groups_tab = GroupsTab(self._groups)
        return self._groups_tab

    def _make_discovery(self) -> QWidget:
        self._discovery_tab = DiscoveryTab(self._accounts, self._groups)
        self._discovery_tab.groups_updated.connect(self._on_groups_changed)
        return self._discovery_tab

    def _make_messages(self) -> QWidget:
        self._messages_tab = MessagesTab(self._messages)
        self._messages_tab.messages_changed.connect(
            lambda: self._on_log("INFO", f"Messages updated — {len(self._messages)} template(s)")
        )
        return self._messages_tab

    def _make_analytics(self) -> QWidget:
        self._analytics_tab = AnalyticsTab(self._perf)
        return self._analytics_tab

    def _make_logs(self) -> QWidget:
        self._logs_tab = LogsTab()
        return self._logs_tab

    # ------------------------------------------------------------------
    # Callbacks from controller
    # ------------------------------------------------------------------

    def _on_log(self, level: str, msg: str) -> None:
        self._logs_tab.append(level, msg)
        self._dashboard.add_event(level, msg)

    def _on_metrics(self, m: dict) -> None:
        self._dashboard.on_metrics(m)
        self._campaign_tab.on_metrics(m)
        self._analytics_tab.on_metrics(m)
        state = m.get("state", "Idle")
        sent = m.get("total_sent", 0)
        rate = m.get("success_rate", 0)
        self._status_lbl.setText(
            f"State: {state}  |  Sent: {sent:,}  |  Rate: {rate}%  |  Wave: {m.get('wave', 0)}"
        )

    def _on_state(self, state: str) -> None:
        self._dashboard.on_state_changed(state)
        self._campaign_tab.on_state_changed(state)
        colors = {"Running": "#40d060", "Paused": "#d0a020", "Stopped": "#404060", "Error": "#e05050"}
        color = colors.get(state, "#404060")
        self._sidebar_status.setText(f"● {state}")
        self._sidebar_status.setStyleSheet(f"color:{color}; padding:8px 16px; font-size:11px; font-weight:700;")

    def _on_accounts_changed(self) -> None:
        self._discovery_tab.on_accounts_changed()
        n = self._accounts.logged_in_count
        self._on_log("INFO", f"Accounts updated — {n} logged in, {self._accounts.total_count} total")

    def _on_groups_changed(self) -> None:
        self._groups_tab.on_groups_changed()
        n = self._groups.joined_count
        self._on_log("INFO", f"Groups updated — {n} joined")

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self._ctrl.stop()
        self._perf.save()
        super().closeEvent(event)
