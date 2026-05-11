"""
gui/accounts_tab.py — Furaya v6.0 Enterprise
Accounts management with vibrant login UX, real-time status,
and concurrent multi-account login support.
"""

from __future__ import annotations
import asyncio
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QFormLayout, QMessageBox, QFrame,
    QSizePolicy,
)
from PyQt5.QtGui import QColor, QFont
import qasync


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("border: none; border-top: 1px solid rgba(0,212,255,0.10);")
    return f


def _styled_lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #6a9ab8; font-size: 12px; font-weight: 600;")
    return lbl


STATUS_COLORS = {
    "connected":    ("#00ff88", "✅ Connected"),
    "connecting":   ("#ffd700", "⏳ Connecting..."),
    "failed":       ("#ff3366", "❌ Failed"),
    "pending":      ("#6a8aa8", "○ Pending"),
    "disconnected": ("#304050", "○ Disconnected"),
}


# ─── Add Account Dialog ──────────────────────────────────────────────────────

class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Telegram Account")
        self.setMinimumWidth(460)
        self.setMinimumHeight(340)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(18)
        lay.setContentsMargins(32, 28, 32, 28)

        # Title
        title = QLabel("ADD ACCOUNT")
        title.setStyleSheet(
            "color: #00d4ff; font-size: 18px; font-weight: 900; letter-spacing: 4px;"
        )
        sub = QLabel("Get your API credentials from  my.telegram.org/apps")
        sub.setStyleSheet("color: #507090; font-size: 12px;")
        sub.setOpenExternalLinks(True)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addWidget(_sep())

        # Form
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+1 234 567 8900")
        self.phone_edit.setMinimumHeight(40)

        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText("12345678")
        self.api_id_edit.setMinimumHeight(40)

        self.api_hash_edit = QLineEdit()
        self.api_hash_edit.setPlaceholderText("abcdef1234567890abcdef1234567890")
        self.api_hash_edit.setEchoMode(QLineEdit.Password)
        self.api_hash_edit.setMinimumHeight(40)

        form.addRow(_styled_lbl("Phone Number"), self.phone_edit)
        form.addRow(_styled_lbl("API ID"), self.api_id_edit)
        form.addRow(_styled_lbl("API Hash"), self.api_hash_edit)
        lay.addLayout(form)

        # Buttons
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.clicked.connect(self.reject)

        self._btn_add = QPushButton("＋  Add Account")
        self._btn_add.setObjectName("btn_primary")
        self._btn_add.setMinimumHeight(40)
        self._btn_add.clicked.connect(self._validate_and_accept)
        self._btn_add.setDefault(True)

        btn_lay.addWidget(btn_cancel)
        btn_lay.addWidget(self._btn_add, 1)
        lay.addLayout(btn_lay)

    def _validate_and_accept(self):
        phone   = self.phone_edit.text().strip()
        api_id  = self.api_id_edit.text().strip()
        api_hash = self.api_hash_edit.text().strip()

        if not phone:
            QMessageBox.warning(self, "Validation", "Phone number is required.")
            return
        if not api_id.isdigit():
            QMessageBox.warning(self, "Validation", "API ID must be a number.")
            return
        if len(api_hash) < 10:
            QMessageBox.warning(self, "Validation", "API Hash looks invalid (too short).")
            return
        self.accept()

    def values(self):
        return (
            self.phone_edit.text().strip(),
            int(self.api_id_edit.text().strip()),
            self.api_hash_edit.text().strip(),
        )


# ─── OTP Dialog ──────────────────────────────────────────────────────────────

class OTPDialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, phone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram Verification Code")
        self.setMinimumWidth(420)
        self.setMinimumHeight(280)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(20)
        lay.setContentsMargins(36, 32, 36, 32)

        title = QLabel("VERIFICATION CODE")
        title.setStyleSheet(
            "color: #00d4ff; font-size: 20px; font-weight: 900; letter-spacing: 3px;"
        )
        title.setAlignment(Qt.AlignCenter)

        msg = QLabel(f"Telegram sent a code to\n{phone}")
        msg.setStyleSheet("color: #7a9ab8; font-size: 13px;")
        msg.setAlignment(Qt.AlignCenter)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Enter code  e.g.  1 2 3 4 5")
        self.code_edit.setAlignment(Qt.AlignCenter)
        self.code_edit.setStyleSheet(
            "font-size: 28px; letter-spacing: 10px; font-weight: 800;"
            "padding: 10px; border: 2px solid rgba(0,212,255,0.5);"
            "border-radius: 8px;"
        )
        self.code_edit.setMaxLength(10)
        self.code_edit.setMinimumHeight(58)

        btn = QPushButton("✔  Submit Code")
        btn.setObjectName("btn_primary")
        btn.setMinimumHeight(44)
        btn.clicked.connect(self._submit)
        self.code_edit.returnPressed.connect(self._submit)

        lay.addWidget(title)
        lay.addWidget(msg)
        lay.addWidget(self.code_edit)
        lay.addWidget(btn)

        self.code_edit.setFocus()

    def _submit(self):
        code = self.code_edit.text().strip()
        if code:
            self.submitted.emit(code)
            self.accept()


# ─── 2FA Dialog ──────────────────────────────────────────────────────────────

class TwoFADialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, phone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Two-Factor Authentication")
        self.setMinimumWidth(420)
        self.setMinimumHeight(260)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(20)
        lay.setContentsMargins(36, 32, 36, 32)

        title = QLabel("2FA PASSWORD")
        title.setStyleSheet(
            "color: #ffd700; font-size: 20px; font-weight: 900; letter-spacing: 3px;"
        )
        title.setAlignment(Qt.AlignCenter)

        msg = QLabel(f"This account has 2FA enabled.\nEnter your Telegram cloud password for\n{phone}")
        msg.setStyleSheet("color: #7a9ab8; font-size: 13px;")
        msg.setAlignment(Qt.AlignCenter)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("Your cloud password")
        self.pwd_edit.setMinimumHeight(44)
        self.pwd_edit.setStyleSheet(
            "font-size: 16px; border: 2px solid rgba(255,215,0,0.4); border-radius: 8px;"
        )

        btn = QPushButton("✔  Submit Password")
        btn.setObjectName("btn_gold")
        btn.setMinimumHeight(44)
        btn.clicked.connect(self._submit)
        self.pwd_edit.returnPressed.connect(self._submit)

        lay.addWidget(title)
        lay.addWidget(msg)
        lay.addWidget(self.pwd_edit)
        lay.addWidget(btn)

        self.pwd_edit.setFocus()

    def _submit(self):
        pwd = self.pwd_edit.text()
        if pwd:
            self.submitted.emit(pwd)
            self.accept()


# ─── AccountsTab ──────────────────────────────────────────────────────────────

class AccountsTab(QWidget):
    accounts_changed = pyqtSignal()

    def __init__(self, account_manager, parent=None):
        super().__init__(parent)
        self._accounts = account_manager
        self._setup_ui()
        self._refresh_table()

        # Wire OTP/2FA providers
        self._accounts.otp_provider = self._provide_otp
        self._accounts.tfa_provider = self._provide_2fa

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_table)
        self._timer.start(2000)

    def _log(self, level: str, msg: str):
        self._accounts._log(level, msg)

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        # Header row
        hdr_lay = QHBoxLayout()
        hdr_col = QVBoxLayout()
        hdr_col.setSpacing(3)

        title = QLabel("ACCOUNTS")
        title.setStyleSheet(
            "color: #00d4ff; font-size: 22px; font-weight: 900; letter-spacing: 4px;"
        )
        sub = QLabel("Manage multiple Telegram accounts — concurrent login supported")
        sub.setStyleSheet("color: #405060; font-size: 12px;")
        hdr_col.addWidget(title)
        hdr_col.addWidget(sub)
        hdr_lay.addLayout(hdr_col, 1)

        btn_add = QPushButton("＋  Add Account")
        btn_add.setObjectName("btn_success")
        btn_add.setFixedHeight(40)
        btn_add.setMinimumWidth(140)
        btn_add.clicked.connect(self._add_account)

        btn_login_all = QPushButton("⚡  Login All")
        btn_login_all.setObjectName("btn_gold")
        btn_login_all.setFixedHeight(40)
        btn_login_all.setMinimumWidth(120)
        btn_login_all.clicked.connect(self._login_all)

        btn_stop_all = QPushButton("■  Stop All")
        btn_stop_all.setObjectName("btn_danger")
        btn_stop_all.setFixedHeight(40)
        btn_stop_all.setMinimumWidth(110)
        btn_stop_all.clicked.connect(self._stop_all)

        hdr_lay.addWidget(btn_add)
        hdr_lay.addWidget(btn_login_all)
        hdr_lay.addWidget(btn_stop_all)
        lay.addLayout(hdr_lay)
        lay.addWidget(_sep())

        # Account table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Phone", "API ID", "Status", "Msgs Sent", "Groups", "Actions"]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 180)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(340)
        lay.addWidget(self._table)

        # Summary bar
        self._summary = QLabel("No accounts added yet")
        self._summary.setStyleSheet("color: #405060; font-size: 12px; padding: 4px 0;")
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
                str(acc.get("groups_joined", 0)),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor(color))
                self._table.setItem(row, col, item)

            # Action buttons cell
            btn_w = QWidget()
            btn_lay = QHBoxLayout(btn_w)
            btn_lay.setContentsMargins(6, 4, 6, 4)
            btn_lay.setSpacing(6)

            if status not in ("connected", "connecting"):
                btn_login = QPushButton("Login")
                btn_login.setFixedHeight(28)
                btn_login.setStyleSheet("""
                    QPushButton {
                        background: rgba(0,212,255,0.12);
                        color: #00d4ff;
                        border: 1px solid rgba(0,212,255,0.30);
                        border-radius: 5px;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 0 10px;
                    }
                    QPushButton:hover { background: rgba(0,212,255,0.25); }
                """)
                btn_login.clicked.connect(lambda _, r=row: self._login(r))
                btn_lay.addWidget(btn_login)
            else:
                btn_disc = QPushButton("Disconnect")
                btn_disc.setFixedHeight(28)
                btn_disc.setStyleSheet("""
                    QPushButton {
                        background: rgba(255,215,0,0.10);
                        color: #ffd700;
                        border: 1px solid rgba(255,215,0,0.25);
                        border-radius: 5px;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 0 6px;
                    }
                    QPushButton:hover { background: rgba(255,215,0,0.22); }
                """)
                btn_disc.clicked.connect(lambda _, r=row: self._disconnect(r))
                btn_lay.addWidget(btn_disc)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(28, 28)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: rgba(255,50,80,0.12);
                    color: #ff3366;
                    border: 1px solid rgba(255,50,80,0.25);
                    border-radius: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { background: rgba(255,50,80,0.28); }
            """)
            btn_del.clicked.connect(lambda _, r=row: self._remove(r))
            btn_lay.addWidget(btn_del)
            btn_lay.addStretch()

            self._table.setCellWidget(row, 5, btn_w)
            self._table.setRowHeight(row, 48)

        n = self._accounts.logged_in_count
        t = self._accounts.total_count
        if t == 0:
            self._summary.setText("No accounts added — click '＋ Add Account' to get started")
        else:
            self._summary.setText(f"{n}/{t} accounts connected")

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
        try:
            await self._accounts.login_account(row)
        except Exception as e:
            self._log("ERROR", f"Login task crashed for row {row}: {e}")
        finally:
            self._refresh_table()
            self.accounts_changed.emit()

    def _login_all(self):
        asyncio.ensure_future(self._async_login_all())

    @qasync.asyncSlot()
    async def _async_login_all(self):
        try:
            connected = await self._accounts.login_all()
            self._log("INFO", f"Login All complete — {connected} accounts connected")
        except Exception as e:
            self._log("ERROR", f"Login All crashed: {e}")
        finally:
            self._refresh_table()
            self.accounts_changed.emit()

    def _disconnect(self, row: int):
        asyncio.ensure_future(self._async_disconnect(row))

    @qasync.asyncSlot()
    async def _async_disconnect(self, row: int):
        accs = self._accounts.get_all()
        if row < len(accs):
            acc = accs[row]
            engine = acc.get("engine")
            if engine:
                try:
                    await engine.stop()
                except Exception:
                    pass
            acc["engine"] = None
            acc["status"] = "disconnected"
            self._accounts.save_accounts()
        self._refresh_table()
        self.accounts_changed.emit()

    def _stop_all(self):
        asyncio.ensure_future(self._async_stop_all())

    @qasync.asyncSlot()
    async def _async_stop_all(self):
        await self._accounts.stop_all()
        self._refresh_table()
        self.accounts_changed.emit()

    def _remove(self, row: int):
        accs = self._accounts.get_all()
        if row < len(accs):
            phone = accs[row].get("phone", "?")
            reply = QMessageBox.question(
                self, "Remove Account",
                f"Remove {phone}?\nThis will disconnect it immediately.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._accounts.remove_account(row)
                self._refresh_table()
                self.accounts_changed.emit()

    # ── OTP / 2FA providers ───────────────────────────────────────────

    async def _provide_otp(self, phone: str):
        """Show OTP dialog and submit code to the waiting engine."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def _show():
            try:
                dlg = OTPDialog(phone, self)

                def _on_submit(code):
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, code.strip())

                def _on_cancel():
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, "")

                dlg.submitted.connect(_on_submit)
                dlg.rejected.connect(_on_cancel)
                dlg.exec_()
            except Exception as e:
                self._log("ERROR", f"OTP dialog crashed: {e}")
                if not future.done():
                    loop.call_soon_threadsafe(future.set_result, "")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, _show)

        try:
            code = await asyncio.wait_for(future, timeout=300.0)
        except asyncio.TimeoutError:
            self._log("ERROR", f"OTP dialog timed out for {phone}")
            code = ""

        if code:
            engine = self._accounts.get_pending_engine(phone)
            if engine:
                engine.submit_otp(code)
            else:
                self._log("ERROR", f"OTP received but no pending engine found for {phone}")

    async def _provide_2fa(self, phone: str):
        """Show 2FA dialog and submit password to the waiting engine."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def _show():
            try:
                dlg = TwoFADialog(phone, self)

                def _on_submit(pwd):
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, pwd.strip())

                def _on_cancel():
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, "")

                dlg.submitted.connect(_on_submit)
                dlg.rejected.connect(_on_cancel)
                dlg.exec_()
            except Exception as e:
                self._log("ERROR", f"2FA dialog crashed: {e}")
                if not future.done():
                    loop.call_soon_threadsafe(future.set_result, "")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, _show)

        try:
            password = await asyncio.wait_for(future, timeout=300.0)
        except asyncio.TimeoutError:
            self._log("ERROR", f"2FA dialog timed out for {phone}")
            password = ""

        if password:
            engine = self._accounts.get_pending_engine(phone)
            if engine:
                engine.submit_2fa(password)
            else:
                self._log("ERROR", f"2FA received but no pending engine found for {phone}")
