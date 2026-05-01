"""
core/account.py — Account data model for Furaya.
Used by several GUI and core components to represent a Telegram account.
"""

from __future__ import annotations
from typing import Optional, Dict, Any


class Account:
    def __init__(self, phone: str, api_id: int, api_hash: str) -> None:
        self.phone = phone.strip()
        self.api_id = int(api_id)
        self.api_hash = str(api_hash).strip()
        self.status = "idle"
        self.client = None # Telethon client placeholder
        self.engine = None # TDLib engine placeholder

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "status": self.status,
        }

    @property
    def session_name(self) -> str:
        """Normalized name for Telethon session files."""
        safe = self.phone.replace("+", "").replace(" ", "").strip()
        return f"session_{safe}"

    def mark_idle(self) -> None:
        self.status = "idle"

    @property
    def is_available(self) -> bool:
        return self.status not in ("flood", "banned")

    def mark_flood(self, seconds: int) -> None:
        self.status = "flood"
        # Note: Actual timing logic is handled by AccountManager or AutoPilot
