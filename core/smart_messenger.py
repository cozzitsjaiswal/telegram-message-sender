"""
core/smart_messenger.py

Multi-account message distributor with round-robin account rotation,
per-user deduplication, and automatic account cooldown on PeerFlood.

Usage:
    messenger = SmartMessenger(account_manager)
    results = await messenger.run_campaign(
        target_users=["@user1", "@user2", ...],
        message="Hello!",
        campaign_name="launch_v1",
        msgs_per_account=50,
        delay=(30, 90),
        on_progress=my_callback,
    )
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PeerFloodError,
    UserPrivacyRestrictedError,
    InputUserDeactivatedError,
    UserBannedInChannelError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
)

logger = logging.getLogger(__name__)
DATA_DIR = Path.home() / "FurayaPromoEngine"


@dataclass
class CampaignResult:
    campaign_name: str
    total_targets: int = 0
    sent_ok: int = 0
    sent_failed: int = 0
    skipped_dup: int = 0
    skipped_privacy: int = 0
    accounts_used: int = 0
    accounts_flooded: int = 0
    duration_sec: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.sent_ok + self.sent_failed
        return (self.sent_ok / total * 100) if total else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["success_rate"] = round(self.success_rate, 1)
        return d


class SmartMessenger:
    """Multi-account message distributor with deduplication."""

    def __init__(self, account_manager) -> None:
        self.accounts = account_manager
        self._data_dir = DATA_DIR / "messenger"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._sent_file = self._data_dir / "sent_messages.json"
        self._sent_history: Dict[str, Set[str]] = self._load_sent()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_sent(self) -> Dict[str, Set[str]]:
        if self._sent_file.exists():
            try:
                raw = json.loads(self._sent_file.read_text("utf-8"))
                return {k: set(v) for k, v in raw.items()}
            except Exception:
                pass
        return {}

    def _save_sent(self) -> None:
        data = {k: list(v) for k, v in self._sent_history.items()}
        self._sent_file.write_text(json.dumps(data, indent=2), "utf-8")

    def _is_sent(self, campaign: str, user: str) -> bool:
        return user in self._sent_history.get(campaign, set())

    def _mark_sent(self, campaign: str, user: str) -> None:
        self._sent_history.setdefault(campaign, set()).add(user)

    # ------------------------------------------------------------------
    # CSV loader
    # ------------------------------------------------------------------

    @staticmethod
    def load_users_from_csv(csv_path: str | Path) -> List[str]:
        """Load user identifiers from a CSV. First column = username/id."""
        users = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    users.append(row[0].strip())
        return users

    # ------------------------------------------------------------------
    # Campaign reset
    # ------------------------------------------------------------------

    def reset_campaign(self, campaign_name: str) -> int:
        """Clear dedup history for a campaign. Returns number of entries removed."""
        count = len(self._sent_history.pop(campaign_name, set()))
        self._save_sent()
        return count

    def get_campaigns(self) -> List[str]:
        return list(self._sent_history.keys())

    # ------------------------------------------------------------------
    # Main campaign runner
    # ------------------------------------------------------------------

    async def run_campaign(
        self,
        target_users: List[str],
        message: str,
        campaign_name: str = "default",
        accounts: Optional[List] = None,
        msgs_per_account: int = 50,
        delay: tuple = (30, 90),
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> CampaignResult:
        """
        Distribute messages across accounts with round-robin rotation.
        Handles FloodWait, PeerFlood, UserPrivacyRestricted cleanly.
        """
        start_time = time.time()
        active = accounts or self.accounts.get_active()
        if not active:
            if on_progress:
                on_progress(0, len(target_users), "❌ No active accounts")
            return CampaignResult(campaign_name)

        result = CampaignResult(
            campaign_name=campaign_name,
            total_targets=len(target_users),
            accounts_used=len(active),
        )

        # Build account rotation with send-count caps
        acc_queue: List[dict] = []
        for acc in active:
            if acc.client:
                acc_queue.append({
                    "account": acc,
                    "client": acc.client,
                    "sent": 0,
                    "flooded": False,
                })
        if not acc_queue:
            return result

        acc_idx = 0
        total = len(target_users)

        for i, user in enumerate(target_users):
            # --- Deduplication ---
            if self._is_sent(campaign_name, user):
                result.skipped_dup += 1
                if on_progress:
                    on_progress(i + 1, total, f"⏭ Skipped (already sent): {user}")
                continue

            # --- Find next available account (round-robin) ---
            acc_entry = None
            attempts = 0
            while attempts < len(acc_queue):
                candidate = acc_queue[acc_idx % len(acc_queue)]
                acc_idx += 1
                if not candidate["flooded"] and candidate["sent"] < msgs_per_account:
                    acc_entry = candidate
                    break
                attempts += 1

            if acc_entry is None:
                if on_progress:
                    on_progress(i + 1, total, "⚠️ All accounts exhausted/flooded")
                break

            phone = acc_entry["account"].phone
            client: TelegramClient = acc_entry["client"]

            if on_progress:
                on_progress(i + 1, total, f"📨 [{phone}] → {user}...")

            # --- Send ---
            try:
                async with client.action(user, "typing"):
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                await client.send_message(user, message)
                result.sent_ok += 1
                acc_entry["sent"] += 1
                self._mark_sent(campaign_name, user)
                if on_progress:
                    on_progress(i + 1, total, f"✅ [{phone}] Sent to {user}")

            except FloodWaitError as e:
                logger.warning("[%s] FloodWait %ds", phone, e.seconds)
                if on_progress:
                    on_progress(i + 1, total, f"⏳ [{phone}] FloodWait {e.seconds}s — pausing")
                acc_entry["account"].mark_flood(e.seconds)
                await asyncio.sleep(min(e.seconds + 5, 120))
                # Retry once
                try:
                    await client.send_message(user, message)
                    result.sent_ok += 1
                    acc_entry["sent"] += 1
                    self._mark_sent(campaign_name, user)
                except Exception:
                    result.sent_failed += 1

            except PeerFloodError:
                logger.error("[%s] PeerFlood — marking as flooded", phone)
                acc_entry["flooded"] = True
                acc_entry["account"].mark_flood(3600)  # 1 hour cooldown
                result.accounts_flooded += 1
                result.sent_failed += 1
                if on_progress:
                    on_progress(i + 1, total, f"🔴 [{phone}] PeerFlood — account on cooldown")

            except UserPrivacyRestrictedError:
                result.skipped_privacy += 1
                if on_progress:
                    on_progress(i + 1, total, f"🔒 {user} — privacy restricted")

            except (InputUserDeactivatedError, UsernameNotOccupiedError, UsernameInvalidError):
                result.sent_failed += 1
                if on_progress:
                    on_progress(i + 1, total, f"❌ {user} — user not found/deactivated")

            except Exception as exc:
                result.sent_failed += 1
                logger.error("[%s] Send error to %s: %s", phone, user, exc)

            # --- Delay ---
            wait = random.uniform(delay[0], delay[1])
            if on_progress:
                on_progress(i + 1, total, f"⏱ Waiting {wait:.0f}s...")
            await asyncio.sleep(wait)

        # Final save
        self._save_sent()
        result.duration_sec = time.time() - start_time

        # Save campaign result
        result_file = self._data_dir / f"result_{campaign_name}.json"
        result_file.write_text(json.dumps(result.to_dict(), indent=2), "utf-8")

        if on_progress:
            on_progress(total, total,
                        f"🏁 Done — ✅ {result.sent_ok} | ❌ {result.sent_failed} | "
                        f"⏭ {result.skipped_dup} dups | 🔒 {result.skipped_privacy} privacy")

        return result
