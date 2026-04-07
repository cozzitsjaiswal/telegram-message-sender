"""Account tab — Add a Telegram account and log in once."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from core.account import Account
from gui.otp_dialog import OtpDialog

logger = logging.getLogger(__name__)

DATA_DIR = Path("C:/FurayaPromoEngine/data")
ACCOUNT_FILE = DATA_DIR / "account.json"


class AccountTab(QWidget):
    """Single-account login panel."""

    account_ready = pyqtSignal(object)   # emits the Account when logged in
    account_lost = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._account: Optional[Account] = None
        self._setup_ui()
        self._try_load_saved()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("Telegram Account")
        title.setObjectName("label_title")
        layout.addWidget(title)

        sub = QLabel(
            "Enter your Telegram credentials below. You only need to log in once — "
            "your session is saved for future runs."
        )
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # ── Credentials form ──
        box = QGroupBox("Credentials")
        form = QFormLayout(box)

        self._phone_input = QLineEdit()
        self._phone_input.setPlaceholderText("+1234567890")
        form.addRow("Phone Number:", self._phone_input)

        self._api_id_input = QLineEdit()
        self._api_id_input.setPlaceholderText("12345678")
        form.addRow("API ID:", self._api_id_input)

        self._api_hash_input = QLineEdit()
        self._api_hash_input.setPlaceholderText("abcdef1234567890abcdef1234567890")
        form.addRow("API Hash:", self._api_hash_input)

        hint = QLabel('<a href="https://my.telegram.org/apps" style="color:#5ab4f0;">📎 Get API ID & Hash from my.telegram.org</a>')
        hint.setOpenExternalLinks(True)
        form.addRow("", hint)

        layout.addWidget(box)

        # ── Login button ──
        btn_row = QHBoxLayout()
        self._btn_login = QPushButton("🔑  Login / Connect")
        self._btn_login.setObjectName("btn_start")
        self._btn_login.clicked.connect(self._on_login)
        btn_row.addWidget(self._btn_login)

        self._btn_logout = QPushButton("🚪  Logout")
        self._btn_logout.clicked.connect(self._on_logout)
        self._btn_logout.setEnabled(False)
        btn_row.addWidget(self._btn_logout)
        layout.addLayout(btn_row)

        # ── Status ──
        self._status_label = QLabel("❌  Not logged in")
        self._status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e05050;")
        layout.addWidget(self._status_label)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _try_load_saved(self) -> None:
        if not ACCOUNT_FILE.exists():
            return
        try:
            data = json.loads(ACCOUNT_FILE.read_text())
            self._phone_input.setText(data.get("phone", ""))
            self._api_id_input.setText(str(data.get("api_id", "")))
            self._api_hash_input.setText(data.get("api_hash", ""))
            self._status_label.setText("ℹ️  Credentials loaded — click Login to connect")
            self._status_label.setStyleSheet("font-size: 13px; color: #f0a020;")
        except Exception:
            pass

    def _save_account(self, account: Account) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ACCOUNT_FILE.write_text(json.dumps(account.to_dict(), indent=2))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_login(self) -> None:
        phone = self._phone_input.text().strip()
        api_id_str = self._api_id_input.text().strip()
        api_hash = self._api_hash_input.text().strip()

        if not phone or not api_id_str or not api_hash:
            QMessageBox.warning(self, "Missing fields", "Please fill in all three fields.")
            return
        try:
            api_id = int(api_id_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid API ID", "API ID must be a number.")
            return

        account = Account(phone=phone, api_id=api_id, api_hash=api_hash)
        self._btn_login.setEnabled(False)
        self._status_label.setText("⏳  Connecting...")
        self._status_label.setStyleSheet("font-size: 13px; color: #f0a020;")
        asyncio.ensure_future(self._async_login(account))

    async def _async_login(self, account: Account) -> None:
        try:
            session_path = str(DATA_DIR / account.session_name)
            client = TelegramClient(session_path, account.api_id, account.api_hash)
            await client.connect()

            if await client.is_user_authorized():
                account.client = client
                self._finalize_login(account)
                return

            # Send OTP
            await client.send_code_request(account.phone)

            dlg = OtpDialog(account.phone, self)
            loop = asyncio.get_event_loop()
            future: asyncio.Future = loop.create_future()

            def _on_finished(result: int) -> None:
                if not future.done():
                    future.set_result(result)

            dlg.finished.connect(_on_finished)
            dlg.open()
            result = await future

            if result != dlg.Accepted or not dlg.code:
                await client.disconnect()
                self._btn_login.setEnabled(True)
                self._status_label.setText("❌  Login cancelled")
                return

            try:
                await client.sign_in(account.phone, dlg.code)
            except SessionPasswordNeededError:
                if not dlg.password:
                    await client.disconnect()
                    self._status_label.setText("❌  2FA required but no password provided")
                    self._btn_login.setEnabled(True)
                    return
                await client.sign_in(password=dlg.password)

            account.client = client
            self._finalize_login(account)

        except Exception as exc:
            self._status_label.setText(f"❌  Login failed: {exc}")
            self._status_label.setStyleSheet("font-size: 13px; color: #e05050;")
            self._btn_login.setEnabled(True)
            logger.error("Login failed: %s", exc)

    def _finalize_login(self, account: Account) -> None:
        self._account = account
        account.mark_idle()
        self._save_account(account)
        self._status_label.setText(f"✅  Logged in as {account.phone}")
        self._status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #40c080;")
        self._btn_login.setEnabled(True)
        self._btn_logout.setEnabled(True)
        self.account_ready.emit(account)
        logger.info("Account logged in: %s", account.phone)

    def _on_logout(self) -> None:
        self._account = None
        self._status_label.setText("❌  Not logged in")
        self._status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e05050;")
        self._btn_logout.setEnabled(False)
        self.account_lost.emit()

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    @property
    def account(self) -> Optional[Account]:
        return self._account
