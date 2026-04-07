"""
gui/messenger_tab.py — PyQt5 tab for SmartMessenger campaigns.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QProgressBar, QPushButton, QSpinBox, QTextEdit,
    QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.smart_messenger import SmartMessenger

logger = logging.getLogger(__name__)


class MessengerTab(QWidget):
    _sig_status = pyqtSignal(str, str)
    _sig_progress = pyqtSignal(int, int, str)

    def __init__(self, account_manager: AccountManager, parent=None):
        super().__init__(parent)
        self.accounts = account_manager
        self._messenger = SmartMessenger(account_manager)
        self._task: Optional[asyncio.Task] = None
        self._setup_ui()
        self._sig_status.connect(self._on_status)
        self._sig_progress.connect(self._on_progress)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Smart Messenger")
        title.setObjectName("label_title")
        root.addWidget(title)

        sub = QLabel(
            "Multi-account message distributor with round-robin, deduplication, "
            "and automatic PeerFlood cooldown."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#4a5080; font-size:11px;")
        root.addWidget(sub)

        # Campaign name + limits
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Campaign:"))
        self._campaign_edit = QLineEdit("default")
        self._campaign_edit.setMaximumWidth(180)
        row1.addWidget(self._campaign_edit)

        row1.addWidget(QLabel("Msgs/Account:"))
        self._per_acc = QSpinBox()
        self._per_acc.setRange(1, 500)
        self._per_acc.setValue(50)
        self._per_acc.setFixedWidth(70)
        row1.addWidget(self._per_acc)

        row1.addWidget(QLabel("Delay (s):"))
        self._delay_min = QSpinBox()
        self._delay_min.setRange(5, 300)
        self._delay_min.setValue(30)
        self._delay_min.setFixedWidth(60)
        row1.addWidget(self._delay_min)
        row1.addWidget(QLabel("–"))
        self._delay_max = QSpinBox()
        self._delay_max.setRange(10, 600)
        self._delay_max.setValue(90)
        self._delay_max.setFixedWidth(60)
        row1.addWidget(self._delay_max)

        row1.addStretch()
        root.addLayout(row1)

        # Target users input
        target_box = QGroupBox("Target Users (one per line, or load CSV)")
        tlay = QVBoxLayout(target_box)

        btn_csv = QPushButton("📂  Load CSV")
        btn_csv.setFixedWidth(120)
        btn_csv.clicked.connect(self._load_csv)
        tlay.addWidget(btn_csv)

        self._targets_edit = QTextEdit()
        self._targets_edit.setPlaceholderText("@username1\n@username2\nuser_id_123\n...")
        self._targets_edit.setMaximumHeight(100)
        self._targets_edit.setStyleSheet(
            "background:#0c0c1e; color:#c8c8f0; "
            "border:1px solid #222240; border-radius:5px; padding:6px;"
        )
        tlay.addWidget(self._targets_edit)
        root.addWidget(target_box)

        # Message template
        msg_box = QGroupBox("Message")
        mlay = QVBoxLayout(msg_box)
        self._msg_edit = QTextEdit()
        self._msg_edit.setPlaceholderText("Your promo message here...")
        self._msg_edit.setMaximumHeight(80)
        self._msg_edit.setStyleSheet(
            "background:#0c0c1e; color:#c8c8f0; "
            "border:1px solid #222240; border-radius:5px; padding:6px;"
        )
        mlay.addWidget(self._msg_edit)
        root.addWidget(msg_box)

        # Action buttons
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("🚀  Start Campaign")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setMinimumHeight(38)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("✖  Stop")
        self._btn_stop.setObjectName("btn_danger")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_stop)

        self._btn_reset = QPushButton("🔄  Reset Dedup")
        self._btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(self._btn_reset)

        btn_row.addStretch()

        self._counter = QLabel("✅ 0  ❌ 0  ⏭ 0")
        self._counter.setStyleSheet("font-size:13px; font-weight:700; color:#d0a020;")
        btn_row.addWidget(self._counter)
        root.addLayout(btn_row)

        # Status + Progress
        status_row = QHBoxLayout()
        self._status = QLabel("Ready — configure campaign and press Start")
        self._status.setStyleSheet("color:#5060a0; font-size:11px;")
        self._status.setWordWrap(True)
        status_row.addWidget(self._status, 3)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setFixedHeight(14)
        status_row.addWidget(self._progress, 1)
        root.addLayout(status_row)

        # Log feed
        self._log_feed = QPlainTextEdit()
        self._log_feed.setReadOnly(True)
        self._log_feed.setMaximumHeight(200)
        self._log_feed.setStyleSheet(
            "background:#07070d; color:#5060a0; font-family:Consolas; font-size:11px;"
        )
        root.addWidget(self._log_feed)

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load CSV", "", "CSV Files (*.csv);;All (*)")
        if path:
            users = SmartMessenger.load_users_from_csv(path)
            self._targets_edit.setPlainText("\n".join(users))
            self._on_status(f"✅ Loaded {len(users)} users from CSV", "#40d060")

    def _on_start(self):
        msg = self._msg_edit.toPlainText().strip()
        if not msg:
            self._on_status("❌ Enter a message", "#e05050")
            return

        raw = self._targets_edit.toPlainText().strip()
        users = [u.strip() for u in raw.split("\n") if u.strip()]
        if not users:
            self._on_status("❌ Add target users", "#e05050")
            return

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._log_feed.clear()

        self._task = asyncio.ensure_future(self._run(users, msg))

    def _on_stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._on_status("🛑 Stopped", "#d0a020")

    def _on_reset(self):
        name = self._campaign_edit.text().strip() or "default"
        count = self._messenger.reset_campaign(name)
        self._on_status(f"🔄 Reset '{name}' — cleared {count} entries", "#5ab4f0")

    async def _run(self, users, message):
        campaign = self._campaign_edit.text().strip() or "default"

        def _progress(curr, total, msg):
            self._sig_progress.emit(curr, total, msg)
            # Also append to log
            self._log_feed.appendPlainText(msg)

        try:
            result = await self._messenger.run_campaign(
                target_users=users,
                message=message,
                campaign_name=campaign,
                msgs_per_account=self._per_acc.value(),
                delay=(self._delay_min.value(), self._delay_max.value()),
                on_progress=_progress,
            )

            self._counter.setText(
                f"✅ {result.sent_ok}  ❌ {result.sent_failed}  "
                f"⏭ {result.skipped_dup}  🔒 {result.skipped_privacy}"
            )
            self._sig_status.emit(
                f"🏁 Done — {result.sent_ok} sent, {result.sent_failed} failed, "
                f"Rate: {result.success_rate:.0f}%",
                "#40d060" if result.sent_ok > 0 else "#e05050",
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
        QApplication.processEvents()

    def _on_progress(self, curr, total, msg):
        self._progress.setMaximum(max(total, 1))
        self._progress.setValue(curr)
        self._status.setText(msg)
        QApplication.processEvents()
