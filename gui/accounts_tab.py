"""Accounts Tab — add, login, remove multiple Telegram accounts."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from core.account import Account, AccountStatus
from core.account_manager import AccountManager
from gui.otp_dialog import OtpDialog

logger = logging.getLogger(__name__)
DATA_DIR = Path("data")


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Account")
        self.setMinimumWidth(380)
        lay = QFormLayout(self)
        self.phone = QLineEdit(); self.phone.setPlaceholderText("+1234567890")
        self.api_id = QLineEdit(); self.api_id.setPlaceholderText("12345678")
        self.api_hash = QLineEdit(); self.api_hash.setPlaceholderText("abcdef...")
        lay.addRow("Phone:", self.phone)
        lay.addRow("API ID:", self.api_id)
        lay.addRow("API Hash:", self.api_hash)
        hint = QLabel('<a href="https://my.telegram.org/apps" style="color:#a05050;">Get API credentials →</a>')
        hint.setOpenExternalLinks(True)
        lay.addRow("", hint)
        btn_row = QHBoxLayout()
        ok = QPushButton("Add")
        ok.setObjectName("btn_gold")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        lay.addRow(btn_row)


class AccountsTab(QWidget):
    accounts_changed = pyqtSignal()

    def __init__(self, manager: AccountManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Account Management")
        title.setObjectName("label_title")
        layout.addWidget(title)

        sub = QLabel("Manage multiple Telegram accounts. Login each account separately.")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Phone", "Status", "Health", "Actions", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("➕  Add Account")
        self._btn_add.setObjectName("btn_gold")
        self._btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self._btn_add)
        btn_row.addStretch()
        self._status = QLabel("")
        btn_row.addWidget(self._status)
        layout.addLayout(btn_row)

    def refresh_table(self):
        accounts = self.manager.get_all()
        self._table.setRowCount(len(accounts))
        for row, acc in enumerate(accounts):
            self._table.setItem(row, 0, QTableWidgetItem(acc.phone))

            status_map = {
                AccountStatus.IDLE: ("● Idle", "#6070a0"),
                AccountStatus.ACTIVE: ("▶ Active", "#40d060"),
                AccountStatus.FLOOD: ("⏳ Flood", "#d0a020"),
                AccountStatus.BANNED: ("✖ Banned", "#e05050"),
                AccountStatus.DISCONNECTED: ("✖ Disconnected", "#e05050"),
            }
            s_text, s_color = status_map.get(acc.status, ("—", "#5060a0"))
            if acc.client is None:
                s_text, s_color = "❌ Not logged in", "#5a3030"
            status_item = QTableWidgetItem(s_text)
            status_item.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(s_color))
            self._table.setItem(row, 1, status_item)

            health = "✅ Good" if acc.client else "⚠️ Offline"
            self._table.setItem(row, 2, QTableWidgetItem(health))

            btn_login = QPushButton("🔑 Login" if not acc.client else "🔄 Reconnect")
            btn_login.clicked.connect(lambda checked, a=acc: asyncio.ensure_future(self._async_login(a)))
            self._table.setCellWidget(row, 3, btn_login)

            btn_remove = QPushButton("🗑")
            btn_remove.setObjectName("btn_danger")
            btn_remove.setFixedWidth(40)
            btn_remove.clicked.connect(lambda checked, p=acc.phone: self._on_remove(p))
            self._table.setCellWidget(row, 4, btn_remove)

        self._table.setRowHeight.__doc__  # dummy ref
        for r in range(self._table.rowCount()):
            self._table.setRowHeight(r, 40)

    def _on_add(self):
        dlg = AddAccountDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        phone = dlg.phone.text().strip()
        api_id_str = dlg.api_id.text().strip()
        api_hash = dlg.api_hash.text().strip()
        if not phone or not api_id_str or not api_hash:
            QMessageBox.warning(self, "Missing fields", "All fields are required.")
            return
        try:
            api_id = int(api_id_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "API ID must be a number.")
            return
        try:
            self.manager.add(phone, api_id, api_hash)
            self.refresh_table()
            self.accounts_changed.emit()
            self._status.setText(f"✅ Added {phone}")
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_remove(self, phone: str):
        if QMessageBox.question(self, "Remove", f"Remove {phone}?") == QMessageBox.Yes:
            self.manager.remove(phone)
            self.refresh_table()
            self.accounts_changed.emit()

    async def _async_login(self, account: Account):
        self._status.setText(f"⏳ Logging in {account.phone}...")
        try:
            session_path = str(DATA_DIR / account.session_name)
            client = TelegramClient(session_path, account.api_id, account.api_hash)
            await client.connect()

            if await client.is_user_authorized():
                account.client = client
                account.mark_idle()
                self.refresh_table()
                self.accounts_changed.emit()
                self._status.setText(f"✅ {account.phone} connected")
                return

            await client.send_code_request(account.phone)
            dlg = OtpDialog(account.phone, self)
            loop = asyncio.get_event_loop()
            fut = loop.create_future()
            dlg.finished.connect(lambda r: fut.set_result(r) if not fut.done() else None)
            dlg.open()
            result = await fut

            if result != QDialog.Accepted or not dlg.code:
                await client.disconnect()
                self._status.setText("❌ Login cancelled")
                return

            try:
                await client.sign_in(account.phone, dlg.code)
            except SessionPasswordNeededError:
                if not dlg.password:
                    self._status.setText("❌ 2FA required but no password entered")
                    await client.disconnect()
                    return
                await client.sign_in(password=dlg.password)

            account.client = client
            account.mark_idle()
            self.refresh_table()
            self.accounts_changed.emit()
            self._status.setText(f"✅ {account.phone} logged in")

        except Exception as exc:
            self._status.setText(f"❌ Login failed: {exc}")
            logger.error("Login failed for %s: %s", account.phone, exc)

    def on_accounts_changed(self):
        self.refresh_table()
