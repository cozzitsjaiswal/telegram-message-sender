"""
core/account_manager.py — Furaya v5.5
Multi-account store. Each account has its own TDLibEngine instance.
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

from core.tdlib_engine import TDLibEngine

logger = logging.getLogger(__name__)


class AccountManager:
    """
    Manages multiple Telegram accounts, each backed by its own TDLibEngine.
    Thread-safe login via asyncio lock to prevent concurrent auth races.
    """

    def __init__(self, data_path: Path, tdlib_dll_path: Path, log_cb: Optional[Callable] = None):
        self.data_path = Path(data_path)
        self.tdlib_dll_path = Path(tdlib_dll_path)
        self.log_cb = log_cb or (lambda level, msg: logger.info(msg))
        self.accounts_file = self.data_path / "accounts.json"
        self.accounts: List[Dict] = []
        self._login_lock = asyncio.Lock()

        # These are set by MainWindow for OTP/2FA dialogs
        self.otp_provider: Optional[Callable] = None
        self.tfa_provider: Optional[Callable] = None

        self.load_accounts()

    def _log(self, level: str, msg: str):
        self.log_cb(level, msg)

    # ── Persistence ────────────────────────────────────────────────────

    def load_accounts(self):
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw = data.get("accounts", data) if isinstance(data, dict) else data
                self.accounts = raw if isinstance(raw, list) else []
            except Exception as e:
                logger.error(f"load_accounts failed: {e}")
                self.accounts = []
        else:
            self.accounts = []

        for acc in self.accounts:
            acc["engine"] = None
            acc["status"] = "disconnected"

    def save_accounts(self):
        self.data_path.mkdir(parents=True, exist_ok=True)
        to_save = []
        for acc in self.accounts:
            to_save.append({
                "phone": acc["phone"],
                "api_id": acc["api_id"],
                "api_hash": acc["api_hash"],
                "status": acc.get("status", "disconnected"),
                "added_at": acc.get("added_at", datetime.now().isoformat()),
            })
        try:
            with open(self.accounts_file, "w", encoding="utf-8") as f:
                json.dump({"accounts": to_save, "version": "5.5"}, f, indent=2)
        except Exception as e:
            logger.error(f"save_accounts failed: {e}")

    # ── Account CRUD ───────────────────────────────────────────────────

    def add_account(self, phone: str, api_id: int, api_hash: str) -> bool:
        # Normalize phone number: always start with +
        phone = phone.strip()
        if not phone.startswith("+"):
            phone = "+" + phone

        if any(a["phone"] == phone for a in self.accounts):
            self._log("WARN", f"Account {phone} already exists")
            return False

        self.accounts.append({
            "phone": phone,
            "api_id": int(api_id),
            "api_hash": str(api_hash).strip(),
            "engine": None,
            "status": "pending",
            "added_at": datetime.now().isoformat(),
            "messages_sent": 0,
            "groups_joined": 0,
        })
        self.save_accounts()
        self._log("INFO", f"✅ Account {phone} added")
        return True

    def remove_account(self, index: int):
        if 0 <= index < len(self.accounts):
            acc = self.accounts.pop(index)
            self.save_accounts()
            self._log("INFO", f"Removed account {acc['phone']}")

    # ── Login ──────────────────────────────────────────────────────────

    async def login_account(self, index: int) -> bool:
        """Login a single account via TDLib. Thread-safe via lock."""
        if index < 0 or index >= len(self.accounts):
            return False

        acc = self.accounts[index]

        if acc.get("engine") and acc.get("status") == "connected":
            return True  # Already connected

        async with self._login_lock:
            acc["status"] = "connecting"
            self._log("INFO", f"🔌 Logging in {acc['phone']}...")

            engine = TDLibEngine(
                phone_number=acc["phone"],
                api_id=acc["api_id"],
                api_hash=acc["api_hash"],
                database_dir=self.data_path,
                tdlib_dll_path=self.tdlib_dll_path,
                on_otp=self.otp_provider,
                on_2fa=self.tfa_provider,
                log_cb=self.log_cb,
            )

            try:
                success = await engine.start()
            except Exception as e:
                self._log("ERROR", f"Login exception for {acc['phone']}: {e}")
                success = False

            if success:
                acc["engine"] = engine
                acc["status"] = "connected"
                self._log("INFO", f"✅ {acc['phone']} connected")
            else:
                acc["engine"] = None
                acc["status"] = "failed"
                reason = getattr(engine, "_fail_reason", "")
                self._log("ERROR", f"❌ {acc['phone']} login failed" + (f": {reason}" if reason else ""))

            self.save_accounts()
            return success

    async def login_all(self) -> int:
        """Login all pending/failed accounts. Returns count of newly connected."""
        connected = 0
        for i, acc in enumerate(self.accounts):
            if acc.get("status") not in ("connected",):
                if await self.login_account(i):
                    connected += 1
                await asyncio.sleep(1.0)  # Stagger logins
        return connected

    # ── Engine access ──────────────────────────────────────────────────

    def get_engine(self, index: int) -> Optional[TDLibEngine]:
        if 0 <= index < len(self.accounts):
            return self.accounts[index].get("engine")
        return None

    def get_active_engines(self) -> List[TDLibEngine]:
        return [
            acc["engine"] for acc in self.accounts
            if acc.get("status") == "connected" and acc.get("engine")
        ]

    def get_status(self, index: int) -> str:
        if 0 <= index < len(self.accounts):
            return self.accounts[index].get("status", "unknown")
        return "unknown"

    # ── Stats ──────────────────────────────────────────────────────────

    @property
    def total_count(self) -> int:
        return len(self.accounts)

    @property
    def logged_in_count(self) -> int:
        return sum(1 for a in self.accounts if a.get("status") == "connected")

    def get_all(self) -> List[Dict]:
        return self.accounts

    def get_active(self) -> List[Dict]:
        return [a for a in self.accounts if a.get("status") == "connected"]

    def increment_sent(self, index: int):
        if 0 <= index < len(self.accounts):
            self.accounts[index]["messages_sent"] = self.accounts[index].get("messages_sent", 0) + 1

    def increment_joined(self, index: int):
        if 0 <= index < len(self.accounts):
            self.accounts[index]["groups_joined"] = self.accounts[index].get("groups_joined", 0) + 1

    async def stop_all(self):
        for acc in self.accounts:
            if acc.get("engine"):
                try:
                    await acc["engine"].stop()
                except Exception:
                    pass
                acc["engine"] = None
                acc["status"] = "disconnected"
