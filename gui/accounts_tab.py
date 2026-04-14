"""
gui/accounts_tab.py — Furaya v5.5
Accounts management with clean login UX and real-time status.
"""

from __future__ import annotations
import asyncio
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QFrame,
)
from PyQt5.QtGui import QColor
import qasync


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("border: none; border-top: 1px solid rgba(0,212,255,0.08);")
    return f


STATUS_COLORS = {
    "connected":    ("#00ff88", "✅ Connected"),
    "connecting":   ("#ffd700", "⏳ Connecting"),
    "failed":       ("#ff3366", "❌ Failed"),
    "pending":      ("#6a8aa8", "○ Pending"),
    "disconnected": ("#304050", "○ Disconnected"),
}


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Telegram Account")
        self.setMinimumWidth(380)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        title = QLabel("ADD ACCOUNT")
        title.setStyleSheet("color: #00d4ff; font-size: 14px; font-weight: 800; letter-spacing: 3px;")
        sub = QLabel("Get API keys from https://my.telegram.org/apps")
        sub.setStyleSheet("color: #405060; font-size: 11px;")
        sub.setOpenExternalLinks(True)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addWidget(_sep())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+1234567890")
        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText("12345678")
        self.api_hash_edit = QLineEdit()
        self.api_hash_edit.setPlaceholderText("abcdef1234...")
        self.api_hash_edit.setEchoMode(QLineEdit.Password)

        lbl_style = "color: #507090; font-size: 11px;"
        for lbl in ("Phone:", "API ID:", "API Hash:"):
            form.setFormAlignment(Qt.AlignLeft)

        form.addRow(_styled_lbl("Phone Number"), self.phone_edit)
        form.addRow(_styled_lbl("API ID"), self.api_id_edit)
        form.addRow(_styled_lbl("API Hash"), self.api_hash_edit)
        lay.addLayout(form)

        btn_lay = QHBoxLayout()
        self._btn_add = QPushButton("Add Account")
        self._btn_add.setObjectName("btn_primary")
        self._btn_add.clicked.connect(self._validate_and_accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_cancel)
        btn_lay.addWidget(self._btn_add)
        lay.addLayout(btn_lay)

    def _validate_and_accept(self):
        phone = self.phone_edit.text().strip()
        api_id = self.api_id_edit.text().strip()
        api_hash = self.api_hash_edit.text().strip()

        if not phone:
            self._err("Phone number is required")
            return
        if not api_id.isdigit():
            self._err("API ID must be a number")
            return
        if len(api_hash) < 10:
            self._err("API Hash looks invalid")
            return
        self.accept()

    def _err(self, msg: str):
        QMessageBox.warning(self, "Validation Error", msg)

    def values(self):
        return (
            self.phone_edit.text().strip(),
            int(self.api_id_edit.text().strip()),
            self.api_hash_edit.text().strip()
        )


class OTPDialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, phone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Verification Code")
        self.setMinimumWidth(340)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        title = QLabel("VERIFICATION CODE")
        title.setStyleSheet("color: #00d4ff; font-size: 14px; font-weight: 800; letter-spacing: 2px;")
        msg = QLabel(f"Telegram sent a code to\n{phone}")
        msg.setStyleSheet("color: #6a8aa8; font-size: 12px; text-align: center;")
        msg.setAlignment(Qt.AlignCenter)
        lay.addWidget(title, alignment=Qt.AlignCenter)
        lay.addWidget(msg)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Enter code (e.g. 12345)")
        self.code_edit.setAlignment(Qt.AlignCenter)
        self.code_edit.setStyleSheet("font-size: 22px; letter-spacing: 8px; font-weight: 700;")
        self.code_edit.setMaxLength(10)
        lay.addWidget(self.code_edit)

        btn = QPushButton("Submit Code")
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self._submit)
        self.code_edit.returnPressed.connect(self._submit)
        lay.addWidget(btn)

    def _submit(self):
        code = self.code_edit.text().strip()
        if code:
            self.submitted.emit(code)
            self.accept()


class TwoFADialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, phone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Two-Factor Authentication")
        self.setMinimumWidth(340)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        title = QLabel("2FA PASSWORD")
        title.setStyleSheet("color: #ffd700; font-size: 14px; font-weight: 800; letter-spacing: 2px;")
        msg = QLabel(f"This account has 2FA enabled.\nEnter your cloud password for {phone}")
        msg.setStyleSheet("color: #6a8aa8; font-size: 12px; text-align: center;")
        msg.setAlignment(Qt.AlignCenter)
        lay.addWidget(title, alignment=Qt.AlignCenter)
        lay.addWidget(msg)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("Your cloud password")
        lay.addWidget(self.pwd_edit)

        btn = QPushButton("Submit Password")
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self._submit)
        self.pwd_edit.returnPressed.connect(self._submit)
        lay.addWidget(btn)

    def _submit(self):
        pwd = self.pwd_edit.text()
        if pwd:
            self.submitted.emit(pwd)
            self.accept()


def _styled_lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #507090; font-size: 11px;")
    return lbl


class AccountsTab(QWidget):
    accounts_changed = pyqtSignal()

    def __init__(self, account_manager, parent=None):
        super().__init__(parent)
        self._accounts = account_manager
        self._pending_otp: dict = {}      # phone -> asyncio.Future
        self._pending_2fa: dict = {}
        self._setup_ui()
        self._refresh_table()

        # Wire OTP/2FA providers into account manager
        self._accounts.otp_provider = self._provide_otp
        self._accounts.tfa_provider = self._provide_2fa

        # Refresh table every 2 seconds
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_table)
        self._timer.start(2000)

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr_lay = QHBoxLayout()
        title = QLabel("ACCOUNTS")
        title.setStyleSheet("color: #00d4ff; font-size: 18px; font-weight: 800; letter-spacing: 3px;")
        sub = QLabel("Manage multiple Telegram accounts for rotation")
        sub.setStyleSheet("color: #405060; font-size: 11px;")
        hdr_col = QVBoxLayout()
        hdr_col.setSpacing(2)
        hdr_col.addWidget(title)
        hdr_col.addWidget(sub)
        hdr_lay.addLayout(hdr_col, 1)

        btn_add = QPushButton("＋  Add Account")
        btn_add.setObjectName("btn_success")
        btn_add.setFixedHeight(36)
        btn_add.clicked.connect(self._add_account)

        btn_login_all = QPushButton("⚡  Login All")
        btn_login_all.setObjectName("btn_gold")
        btn_login_all.setFixedHeight(36)
        btn_login_all.clicked.connect(self._login_all)

        hdr_lay.addWidget(btn_add)
        hdr_lay.addWidget(btn_login_all)
        lay.addLayout(hdr_lay)
        lay.addWidget(_sep())

        # Account table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Phone", "API ID", "Status", "Sent", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._table.setColumnWidth(4, 160)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(300)
        lay.addWidget(self._table)

        # Summary bar
        self._summary = QLabel("No accounts added yet")
        self._summary.setStyleSheet("color: #304050; font-size: 11px; padding: 4px 0;")
        lay.addWidget(self._summary)
        lay.addStretch()

    def _refresh_table(self):
        accounts = self._accounts.get_all()
        self._table.setRowCount(len(accounts))

        for row, acc in enumerate(accounts):
            status = acc.get("status", "disconnected")
            color, status_text = STATUS_COLORS.get(status, ("#304050", status.capitalize()))

            items = [
                acc.get("phone", ""),
                str(acc.get("api_id", "")),
                status_text,
                str(acc.get("messages_sent", 0)),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor(color))
                self._table.setItem(row, col, item)

            # Action buttons
            btn_w = QWidget()
            btn_lay = QHBoxLayout(btn_w)
            btn_lay.setContentsMargins(4, 3, 4, 3)
            btn_lay.setSpacing(4)

            if status not in ("connected", "connecting"):
                btn_login = QPushButton("Login")
                btn_login.setFixedHeight(26)
                btn_login.setStyleSheet("""
                    QPushButton {
                        background: rgba(0,212,255,0.10);
                        color: #00d4ff;
                        border: 1px solid rgba(0,212,255,0.25);
                        border-radius: 4px;
                        font-size: 11px;
                        padding: 0 8px;
                    }
                    QPushButton:hover { background: rgba(0,212,255,0.20); }
                """)
                btn_login.clicked.connect(lambda _, r=row: self._login(r))
                btn_lay.addWidget(btn_login)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(26, 26)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: rgba(255,50,80,0.10);
                    color: #ff3366;
                    border: 1px solid rgba(255,50,80,0.20);
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover { background: rgba(255,50,80,0.25); }
            """)
            btn_del.clicked.connect(lambda _, r=row: self._remove(r))
            btn_lay.addWidget(btn_del)
            btn_lay.addStretch()

            self._table.setCellWidget(row, 4, btn_w)
            self._table.setRowHeight(row, 44)

        connected = self._accounts.logged_in_count
        total = self._accounts.total_count
        if total == 0:
            self._summary.setText("No accounts added — click '＋ Add Account' to get started")
        else:
            self._summary.setText(f"{connected}/{total} accounts connected")

    # ── Actions ────────────────────────────────────────────────────────

    def _add_account(self):
        dlg = AddAccountDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            phone, api_id, api_hash = dlg.values()
            if self._accounts.add_account(phone, api_id, api_hash):
                self._refresh_table()
                self.accounts_changed.emit()
            else:
                QMessageBox.warning(self, "Duplicate", f"Account {phone} is already added.")

    def _login(self, row: int):
        asyncio.ensure_future(self._async_login(row))

    @qasync.asyncSlot()
    async def _async_login(self, row: int):
        await self._accounts.login_account(row)
        self._refresh_table()
        self.accounts_changed.emit()

    def _login_all(self):
        asyncio.ensure_future(self._async_login_all())

    @qasync.asyncSlot()
    async def _async_login_all(self):
        await self._accounts.login_all()
        self._refresh_table()
        self.accounts_changed.emit()

    def _remove(self, row: int):
        accs = self._accounts.get_all()
        if row < len(accs):
            phone = accs[row].get("phone", "?")
            reply = QMessageBox.question(
                self, "Remove Account",
                f"Remove {phone}?\nThis will disconnect it immediately.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._accounts.remove_account(row)
                self._refresh_table()
                self.accounts_changed.emit()

    # ── OTP / 2FA providers ────────────────────────────────────────────

    async def _provide_otp(self, phone: str):
        """Show OTP dialog without blocking the event loop."""
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def _show():
            dlg = OTPDialog(phone, self)
            dlg.submitted.connect(lambda code: loop.call_soon_threadsafe(future.set_result, code))
            dlg.rejected.connect(lambda: loop.call_soon_threadsafe(
                future.set_result, "") if not future.done() else None)
            dlg.exec_()

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, _show)
        await future

    async def _provide_2fa(self, phone: str):
        """Show 2FA dialog without blocking the event loop."""
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def _show():
            dlg = TwoFADialog(phone, self)
            dlg.submitted.connect(lambda pwd: loop.call_soon_threadsafe(future.set_result, pwd))
            dlg.rejected.connect(lambda: loop.call_soon_threadsafe(
                future.set_result, "") if not future.done() else None)
            dlg.exec_()

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, _show)
        await future
