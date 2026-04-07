"""
gui/adder_tab.py — PyQt5 tab for SmartMemberAdder.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSpinBox, QTextEdit,
    QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.member_adder import SmartMemberAdder

logger = logging.getLogger(__name__)


class AdderTab(QWidget):
    _sig_status = pyqtSignal(str, str)
    _sig_progress = pyqtSignal(int, int, str)

    def __init__(self, account_manager: AccountManager, parent=None):
        super().__init__(parent)
        self.accounts = account_manager
        self._task: Optional[asyncio.Task] = None
        self._setup_ui()
        self._sig_status.connect(self._on_status)
        self._sig_progress.connect(self._on_progress)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Member Adder")
        title.setObjectName("label_title")
        root.addWidget(title)

        sub = QLabel(
            "Add members to your groups with smart rate limiting (20/hour hard cap). "
            "Supports CSV bulk import."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#4a5080; font-size:11px;")
        root.addWidget(sub)

        # Controls
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Account:"))
        self._acc_combo = QComboBox()
        self._acc_combo.setMinimumWidth(180)
        row1.addWidget(self._acc_combo)

        row1.addWidget(QLabel("Target Group:"))
        self._group_edit = QLineEdit()
        self._group_edit.setPlaceholderText("@my_group or group ID")
        self._group_edit.setMinimumWidth(200)
        row1.addWidget(self._group_edit)

        row1.addWidget(QLabel("Delay (s):"))
        self._delay_min = QSpinBox()
        self._delay_min.setRange(5, 120)
        self._delay_min.setValue(10)
        self._delay_min.setFixedWidth(55)
        row1.addWidget(self._delay_min)
        row1.addWidget(QLabel("–"))
        self._delay_max = QSpinBox()
        self._delay_max.setRange(10, 300)
        self._delay_max.setValue(20)
        self._delay_max.setFixedWidth(55)
        row1.addWidget(self._delay_max)

        row1.addStretch()
        root.addLayout(row1)

        # Users input
        users_box = QGroupBox("Users to Add (one per line, or load CSV)")
        ulay = QVBoxLayout(users_box)

        btn_csv = QPushButton("📂  Load CSV")
        btn_csv.setFixedWidth(120)
        btn_csv.clicked.connect(self._load_csv)
        ulay.addWidget(btn_csv)

        self._users_edit = QTextEdit()
        self._users_edit.setPlaceholderText("@user1\n@user2\nuser_id_123\n...")
        self._users_edit.setMaximumHeight(120)
        self._users_edit.setStyleSheet(
            "background:#0c0c1e; color:#c8c8f0; "
            "border:1px solid #222240; border-radius:5px; padding:6px;"
        )
        ulay.addWidget(self._users_edit)
        root.addWidget(users_box)

        # Action buttons
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("➕  Start Adding")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setMinimumHeight(38)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("✖  Stop")
        self._btn_stop.setObjectName("btn_danger")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_stop)

        btn_row.addStretch()

        self._counter = QLabel("✅ 0  ❌ 0  🔒 0")
        self._counter.setStyleSheet("font-size:13px; font-weight:700; color:#d0a020;")
        btn_row.addWidget(self._counter)
        root.addLayout(btn_row)

        # Rate limit indicator
        rate_box = QGroupBox("Rate Limit Status")
        rlay = QHBoxLayout(rate_box)
        self._rate_label = QLabel("0 / 20 adds this hour")
        self._rate_label.setStyleSheet("color:#5ab4f0; font-size:12px; font-weight:600;")
        rlay.addWidget(self._rate_label)
        root.addWidget(rate_box)

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

        root.addStretch()
        self._refresh_combo()

    def _refresh_combo(self):
        self._acc_combo.clear()
        for acc in self.accounts.get_all():
            icon = "✅" if acc.client else "❌"
            self._acc_combo.addItem(f"{icon} {acc.phone}", acc)

    def on_accounts_changed(self):
        self._refresh_combo()

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load CSV", "", "CSV Files (*.csv);;All (*)")
        if path:
            import csv
            users = []
            with open(path, "r", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if row and row[0].strip():
                        users.append(row[0].strip())
            self._users_edit.setPlainText("\n".join(users))
            self._on_status(f"✅ Loaded {len(users)} users", "#40d060")

    def _on_start(self):
        acc = self._acc_combo.currentData()
        if not acc or not acc.client:
            self._on_status("❌ Account not logged in", "#e05050")
            return
        group = self._group_edit.text().strip()
        if not group:
            self._on_status("❌ Enter a target group", "#e05050")
            return
        raw = self._users_edit.toPlainText().strip()
        users = [u.strip() for u in raw.split("\n") if u.strip()]
        if not users:
            self._on_status("❌ Add users to add", "#e05050")
            return

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._task = asyncio.ensure_future(self._run(acc, group, users))

    def _on_stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._on_status("🛑 Stopped", "#d0a020")

    async def _run(self, account, group, users):
        adder = SmartMemberAdder(account.client, account.phone)

        def _progress(curr, total, msg):
            self._sig_progress.emit(curr, total, msg)

        try:
            stats = await adder.bulk_add(
                users, group,
                delay=(self._delay_min.value(), self._delay_max.value()),
                on_progress=_progress,
            )

            self._counter.setText(
                f"✅ {stats.added_ok}  ❌ {stats.failed}  🔒 {stats.privacy_blocked}"
            )
            self._sig_status.emit(
                f"🏁 Done — ✅ {stats.added_ok} added | ❌ {stats.failed} failed | "
                f"Rate: {stats.success_rate:.0f}%",
                "#40d060" if stats.added_ok > 0 else "#e05050",
            )

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
