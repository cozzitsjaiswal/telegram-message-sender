"""
core/member_adder.py

Smart member adder with hard 20-adds/hour rate cap, admin/invite fallback,
CSV bulk import, and auto-save of failed users.
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

from telethon import TelegramClient
from telethon.errors import (
    ChatAdminRequiredError,
    FloodWaitError,
    PeerFloodError,
    UserAlreadyParticipantError,
    UserBannedInChannelError,
    UserPrivacyRestrictedError,
    UserNotMutualContactError,
    InputUserDeactivatedError,
)
from telethon.tl.functions.channels import InviteToChannelRequest

logger = logging.getLogger(__name__)
DATA_DIR = Path.home() / "FurayaPromoEngine" / "member_adder"


@dataclass
class AddStats:
    total: int = 0
    added_ok: int = 0
    already_member: int = 0
    privacy_blocked: int = 0
    failed: int = 0
    peer_flooded: bool = False
    duration_sec: float = 0.0

    @property
    def success_rate(self) -> float:
        done = self.added_ok + self.failed
        return (self.added_ok / done * 100) if done else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["success_rate"] = round(self.success_rate, 1)
        return d


class SmartMemberAdder:
    """
    Adds users to a group with:
    - Hard limit: 20 adds / hour / account
    - Admin invite fallback
    - CSV bulk import
    - Failed-user persistence
    """

    HOURLY_LIMIT = 20

    def __init__(self, client: TelegramClient, phone: str) -> None:
        self.client = client
        self.phone = phone
        self._data_dir = DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._failed_file = self._data_dir / f"failed_{phone}.json"
        self._failed_users: List[dict] = self._load_failed()
        self._add_timestamps: List[float] = []

    # ------------------------------------------------------------------
    # Rate limiter
    # ------------------------------------------------------------------

    def _can_add(self) -> bool:
        """Enforce 20 adds/hour hard limit."""
        now = time.time()
        cutoff = now - 3600
        self._add_timestamps = [t for t in self._add_timestamps if t > cutoff]
        return len(self._add_timestamps) < self.HOURLY_LIMIT

    def _record_add(self) -> None:
        self._add_timestamps.append(time.time())

    def _wait_until_slot(self) -> float:
        """Returns seconds to wait until next slot opens."""
        if self._can_add():
            return 0
        cutoff = time.time() - 3600
        self._add_timestamps = [t for t in self._add_timestamps if t > cutoff]
        if self._add_timestamps:
            return self._add_timestamps[0] + 3600 - time.time() + 1
        return 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_failed(self) -> List[dict]:
        if self._failed_file.exists():
            try:
                return json.loads(self._failed_file.read_text("utf-8"))
            except Exception:
                pass
        return []

    def _save_failed(self) -> None:
        self._failed_file.write_text(json.dumps(self._failed_users, indent=2), "utf-8")

    # ------------------------------------------------------------------
    # Single add
    # ------------------------------------------------------------------

    async def add_to_group(
        self,
        group_id,
        user_id,
    ) -> tuple[bool, str]:
        """
        Try direct InviteToChannel (admin). On ChatAdminRequired, skip.
        Always respects hourly rate cap.
        """
        if not self._can_add():
            wait = self._wait_until_slot()
            return False, f"RateLimit:wait_{int(wait)}s"

        try:
            user_entity = await self.client.get_input_entity(user_id)
            await self.client(InviteToChannelRequest(group_id, [user_entity]))
            self._record_add()
            logger.info("[%s] ✅ Added %s to group", self.phone, user_id)
            return True, ""

        except UserAlreadyParticipantError:
            return True, "AlreadyMember"

        except FloodWaitError as e:
            logger.warning("[%s] FloodWait %ds adding member", self.phone, e.seconds)
            await asyncio.sleep(min(e.seconds + 5, 120))
            try:
                user_entity = await self.client.get_input_entity(user_id)
                await self.client(InviteToChannelRequest(group_id, [user_entity]))
                self._record_add()
                return True, ""
            except Exception as e2:
                return False, f"RetryFailed:{e2}"

        except PeerFloodError:
            return False, "PeerFlood"

        except ChatAdminRequiredError:
            return False, "AdminRequired"

        except UserPrivacyRestrictedError:
            return False, "PrivacyRestricted"

        except UserNotMutualContactError:
            return False, "NotMutualContact"

        except UserBannedInChannelError:
            return False, "UserBanned"

        except InputUserDeactivatedError:
            return False, "Deactivated"

        except Exception as e:
            return False, str(type(e).__name__)

    # ------------------------------------------------------------------
    # Bulk add from CSV
    # ------------------------------------------------------------------

    async def bulk_add_from_csv(
        self,
        csv_path: str | Path,
        group_id,
        delay: tuple = (10, 20),
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> AddStats:
        """
        Load users from CSV (first column) and add them to group.
        Enforces 20/hour hard limit with automatic waiting.
        """
        users = []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if row and row[0].strip():
                    users.append(row[0].strip())

        return await self.bulk_add(users, group_id, delay, on_progress)

    async def bulk_add(
        self,
        users: List[str],
        group_id,
        delay: tuple = (10, 20),
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> AddStats:
        """Bulk add a list of user identifiers."""
        stats = AddStats(total=len(users))
        start = time.time()

        for i, user in enumerate(users):
            if on_progress:
                on_progress(i + 1, len(users), f"Adding {user}...")

            # Rate limit enforcement
            if not self._can_add():
                wait = self._wait_until_slot()
                if on_progress:
                    on_progress(i + 1, len(users), f"⏳ Rate limit — waiting {int(wait)}s")
                await asyncio.sleep(wait)

            ok, err = await self.add_to_group(group_id, user)

            if ok:
                if err == "AlreadyMember":
                    stats.already_member += 1
                    if on_progress:
                        on_progress(i + 1, len(users), f"↩ {user} already member")
                else:
                    stats.added_ok += 1
                    if on_progress:
                        on_progress(i + 1, len(users), f"✅ Added {user}")
            else:
                if err == "PrivacyRestricted":
                    stats.privacy_blocked += 1
                elif err == "PeerFlood":
                    stats.peer_flooded = True
                    if on_progress:
                        on_progress(i + 1, len(users), "🔴 PeerFlood — stopping")
                    break
                else:
                    stats.failed += 1

                self._failed_users.append({
                    "user": user, "error": err,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                if on_progress:
                    on_progress(i + 1, len(users), f"❌ {user}: {err}")

            # Delay
            wait = random.uniform(delay[0], delay[1])
            await asyncio.sleep(wait)

        stats.duration_sec = time.time() - start
        self._save_failed()

        # Save stats
        stats_file = self._data_dir / f"stats_{self.phone}.json"
        stats_file.write_text(json.dumps(stats.to_dict(), indent=2), "utf-8")

        if on_progress:
            on_progress(len(users), len(users),
                        f"🏁 Done — ✅ {stats.added_ok} | ❌ {stats.failed} | "
                        f"🔒 {stats.privacy_blocked}")

        return stats

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict:
        stats_file = self._data_dir / f"stats_{self.phone}.json"
        if stats_file.exists():
            try:
                return json.loads(stats_file.read_text("utf-8"))
            except Exception:
                pass
        return {"total": 0, "added_ok": 0, "failed": 0}

    def get_failed_users(self) -> List[dict]:
        return list(self._failed_users)

    def clear_failed(self) -> int:
        count = len(self._failed_users)
        self._failed_users.clear()
        self._save_failed()
        return count
