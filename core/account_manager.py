"""AccountManager — multi-account management with persistence."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from core.account import Account, AccountStatus

logger = logging.getLogger(__name__)
DATA_FILE = Path("data/accounts.json")


class AccountManager:
    def __init__(self) -> None:
        self._accounts: Dict[str, Account] = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        if DATA_FILE.exists():
            try:
                raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    for d in raw:
                        acc = Account.from_dict(d)
                        self._accounts[acc.phone] = acc
                elif isinstance(raw, dict):
                    for phone, d in raw.items():
                        acc = Account.from_dict(d)
                        self._accounts[acc.phone] = acc
                logger.info("Loaded %d account(s)", len(self._accounts))
            except Exception as e:
                logger.error("Failed to load accounts: %s", e)

    def save(self) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(
            json.dumps([a.to_dict() for a in self._accounts.values()], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, phone: str, api_id: int, api_hash: str) -> Account:
        if phone in self._accounts:
            raise ValueError(f"Account {phone} already exists.")
        acc = Account(phone=phone, api_id=api_id, api_hash=api_hash)
        self._accounts[phone] = acc
        self.save()
        logger.info("Added account: %s", phone)
        return acc

    def remove(self, phone: str) -> bool:
        if phone in self._accounts:
            del self._accounts[phone]
            self.save()
            return True
        return False

    def get_by_phone(self, phone: str) -> Optional[Account]:
        return self._accounts.get(phone)

    def get_all(self) -> List[Account]:
        return list(self._accounts.values())

    def get_active(self) -> List[Account]:
        return [a for a in self._accounts.values() if a.is_available and a.client is not None]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def total_count(self) -> int:
        return len(self._accounts)

    @property
    def active_count(self) -> int:
        return sum(1 for a in self._accounts.values() if a.is_available and a.client is not None)

    @property
    def logged_in_count(self) -> int:
        return sum(1 for a in self._accounts.values() if a.client is not None)
