"""Account dataclass representing a single Telegram user session."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AccountStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    FLOOD = "flood"       # temporary rate-limit cooldown
    BANNED = "banned"     # permanently banned/deactivated
    DISCONNECTED = "disconnected"


@dataclass
class Account:
    phone: str
    api_id: int
    api_hash: str
    # Telethon stores session in a file named <session_name>.session
    session_name: str = field(init=False)

    status: AccountStatus = field(default=AccountStatus.IDLE, init=False)
    flood_until: float = field(default=0.0, init=False)   # unix timestamp
    client: Optional[object] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        # Sanitise the phone number to use as a file-safe session name
        safe = self.phone.replace("+", "plus_").replace(" ", "_")
        self.session_name = f"session_{safe}"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when the account can be used right now."""
        if self.status == AccountStatus.BANNED:
            return False
        if self.status == AccountStatus.FLOOD:
            if time.time() >= self.flood_until:
                self.status = AccountStatus.IDLE
                return True
            return False
        return True

    @property
    def flood_remaining(self) -> int:
        """Seconds remaining on a flood cooldown (0 if not in flood)."""
        if self.status != AccountStatus.FLOOD:
            return 0
        return max(0, int(self.flood_until - time.time()))

    def mark_flood(self, seconds: int) -> None:
        self.status = AccountStatus.FLOOD
        self.flood_until = time.time() + seconds

    def mark_banned(self) -> None:
        self.status = AccountStatus.BANNED

    def mark_active(self) -> None:
        self.status = AccountStatus.ACTIVE

    def mark_idle(self) -> None:
        self.status = AccountStatus.IDLE

    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "api_id": self.api_id,
            "api_hash": self.api_hash,
        }

    @staticmethod
    def from_dict(data: dict) -> "Account":
        return Account(
            phone=data["phone"],
            api_id=int(data["api_id"]),
            api_hash=data["api_hash"],
        )

    def __str__(self) -> str:
        return f"{self.phone} [{self.status.value}]"
