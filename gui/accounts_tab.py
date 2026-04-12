"""Accounts Tab — add, login, remove multiple Telegram accounts."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from core.account_manager import AccountManager

logger = logging.getLogger(__name__)
DATA_DIR = Path.home() / "FurayaPromoEngine" / "data"


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
            phone = acc.get('phone', '???')
            self._table.setItem(row, 0, QTableWidgetItem(phone))

            s_text = "—"
            s_color = "#5060a0"
            status = acc.get('status', 'unknown')
            engine = acc.get('engine')
            
            if status == 'connected':
                s_text, s_color = "✅ Logged In", "#40d060"
            elif status == 'pending':
                s_text, s_color = "● Idle", "#6070a0"
            elif status == 'failed':
                s_text, s_color = "❌ Failed", "#e05050"
            elif status == 'disconnected':
                s_text, s_color = "✖ Disconnected", "#e05050"

            status_item = QTableWidgetItem(s_text)
            status_item.setForeground(QColor(s_color))
            self._table.setItem(row, 1, status_item)

            health = "✅ Good" if engine else "⚠️ Offline"
            self._table.setItem(row, 2, QTableWidgetItem(health))

            btn_login = QPushButton("🔑 Login" if not engine else "🔄 Reconnect")
            # We pass row index instead of acc dictionary, as manager expects index
            btn_login.clicked.connect(lambda checked, idx=row: asyncio.ensure_future(self._async_login(idx)))
            self._table.setCellWidget(row, 3, btn_login)

            btn_remove = QPushButton("🗑")
            btn_remove.setObjectName("btn_danger")
            btn_remove.setFixedWidth(40)
            btn_remove.clicked.connect(lambda checked, p=phone: self._on_remove(p))
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
            self.manager.add_account(phone, api_id, api_hash)
            self.refresh_table()
            self.accounts_changed.emit()
            self._status.setText(f"✅ Added {phone}")
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_remove(self, phone: str):
        if QMessageBox.question(self, "Remove", f"Remove {phone}?") == QMessageBox.Yes:
            self.manager.accounts = [a for a in self.manager.accounts if a.get('phone') != phone]
            self.manager.save_accounts()
            self.refresh_table()
            self.accounts_changed.emit()

    async def _async_login(self, index: int):
        acc = self.manager.accounts[index]
        phone = acc.get('phone')
        self._status.setText(f"⏳ Logging in {phone} via TDLib...")
        try:
            success = await self.manager.login_account(
                index,
                on_otp=self.manager.otp_provider,
                on_2fa=self.manager.tfa_provider
            )

            if success:
                self.refresh_table()
                self.accounts_changed.emit()
                self._status.setText(f"✅ {phone} connected (TDLib)")
            else:
                self._status.setText(f"❌ {phone} login failed")

        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._status.setText(f"❌ Login crashed: {exc}")
            logger.error("Login crashed for %s: %s", phone, exc)

    def on_accounts_changed(self):
        self.refresh_table()
