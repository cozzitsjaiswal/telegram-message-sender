"""ForwardEngine — The single brain of Furaya Promo Engine v2.

Three sequential phases run in a single asyncio task:
  Phase 1 — Discovery : Search Telegram globally for groups by keywords
  Phase 2 — Join      : Join discovered groups with human-like delays
  Phase 3 — Forward   : Forward the promo post to every joined group, loop forever
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from telethon import TelegramClient, events
from telethon.errors import (
    ChannelPrivateError,
    ChatWriteForbiddenError,
    FloodWaitError,
    UserBannedInChannelError,
    UserNotParticipantError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat

logger = logging.getLogger(__name__)

DATA_DIR = Path("C:/FurayaPromoEngine/data")


class EngineState(str, Enum):
    IDLE = "idle"
    SEARCHING = "searching"
    JOINING = "joining"
    FORWARDING = "forwarding"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ModeConfig:
    join_delay_min: float
    join_delay_max: float
    send_delay_min: float
    send_delay_max: float
    cycle_delay_min: int   # seconds
    cycle_delay_max: int


MODE_CONFIGS = {
    "Safe":       ModeConfig(10, 20, 30, 60, 3600, 5400),
    "Normal":     ModeConfig(5, 12, 15, 30, 1800, 2700),
    "Aggressive": ModeConfig(2, 5,  5,  15, 600,  900),
}


@dataclass
class EngineStats:
    groups_found: int = 0
    groups_joined: int = 0
    already_member: int = 0
    join_failed: int = 0
    sent_this_cycle: int = 0
    send_failed: int = 0
    cycle_number: int = 0
    state: str = "idle"


class ForwardEngine:
    """The core forwarding engine."""

    def __init__(
        self,
        client: TelegramClient,
        keywords: List[str],
        promo_text: str,
        mode: str = "Normal",
        max_groups: int = 100,
        log_cb: Optional[Callable[[str, str], None]] = None,
        stats_cb: Optional[Callable[[EngineStats], None]] = None,
    ) -> None:
        self.client = client
        self.keywords = [k.strip() for k in keywords if k.strip()]
        self.promo_text = promo_text.strip()
        self.mode = MODE_CONFIGS.get(mode, MODE_CONFIGS["Normal"])
        self.max_groups = max_groups
        self._log_cb = log_cb or (lambda lvl, msg: None)
        self._stats_cb = stats_cb or (lambda s: None)
        self._stop_event = asyncio.Event()
        self._stats = EngineStats()

        # Persistence files
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._joined_file = DATA_DIR / "joined_groups.json"
        self._joined_ids: set[int] = self._load_joined()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_joined(self) -> set[int]:
        if self._joined_file.exists():
            try:
                return set(json.loads(self._joined_file.read_text()))
            except Exception:
                pass
        return set()

    def _save_joined(self) -> None:
        self._joined_file.write_text(json.dumps(list(self._joined_ids)))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        self._stop_event.clear()
        self._stats = EngineStats(state="searching")
        self._emit_stats()

        try:
            # Phase 1: Discover
            self._log("INFO", "🔍 Phase 1 — Searching for groups globally...")
            discovered = await self._phase_search()
            if self._stop_event.is_set():
                return

            # Phase 2: Join
            self._log("INFO", f"➕ Phase 2 — Joining {len(discovered)} discovered groups...")
            self._stats.state = "joining"
            self._emit_stats()
            await self._phase_join(discovered)
            if self._stop_event.is_set():
                return

            # Phase 3: Forward loop (runs forever until stopped)
            self._log("INFO", "📣 Phase 3 — Starting continuous forwarding loop...")
            self._stats.state = "forwarding"
            await self._phase_forward_loop()

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._stats.state = "error"
            self._log("ERROR", f"Engine error: {exc}")
        finally:
            self._stats.state = "stopped"
            self._emit_stats()
            self._log("INFO", "🛑 Engine stopped.")

    def stop(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Phase 1 — Search
    # ------------------------------------------------------------------

    async def _phase_search(self) -> list[dict]:
        discovered: dict[int, dict] = {}

        for keyword in self.keywords:
            if self._stop_event.is_set():
                break
            self._log("INFO", f"  🔎 Searching: '{keyword}'...")
            try:
                result = await self.client(SearchRequest(q=keyword, limit=50))
                for chat in result.chats:
                    if chat.id in discovered:
                        continue
                    if len(discovered) >= self.max_groups:
                        break
                    username = getattr(chat, "username", None) or ""
                    discovered[chat.id] = {
                        "id": chat.id,
                        "title": getattr(chat, "title", "(no name)"),
                        "username": username,
                        "entity": chat,
                    }
                self._log("INFO", f"  ✅ '{keyword}': found {len(result.chats)} results")
                await asyncio.sleep(random.uniform(1.5, 3.0))
            except FloodWaitError as e:
                self._log("WARN", f"  ⏳ FloodWait {e.seconds}s on search — waiting...")
                await asyncio.sleep(e.seconds + 2)
            except Exception as exc:
                self._log("WARN", f"  ❌ Search failed for '{keyword}': {exc}")

        results = list(discovered.values())
        self._stats.groups_found = len(results)
        self._emit_stats()
        self._log("INFO", f"🔍 Discovery complete — {len(results)} unique groups found")
        return results

    # ------------------------------------------------------------------
    # Phase 2 — Join
    # ------------------------------------------------------------------

    async def _phase_join(self, groups: list[dict]) -> None:
        for i, g in enumerate(groups):
            if self._stop_event.is_set():
                break

            entity_id = g["id"]
            title = g["title"]

            if entity_id in self._joined_ids:
                self._stats.already_member += 1
                self._log("INFO", f"  ↩ Already member: {title}")
                self._emit_stats()
                continue

            self._log("INFO", f"  ➕ Joining ({i+1}/{len(groups)}): {title}...")
            try:
                await self.client(JoinChannelRequest(g["entity"]))
                self._joined_ids.add(entity_id)
                self._save_joined()
                self._stats.groups_joined += 1
                self._log("INFO", f"  ✅ Joined: {title}")
            except FloodWaitError as e:
                self._log("WARN", f"  ⏳ FloodWait {e.seconds}s — waiting...")
                await asyncio.sleep(e.seconds + 5)
                # Retry once
                try:
                    await self.client(JoinChannelRequest(g["entity"]))
                    self._joined_ids.add(entity_id)
                    self._save_joined()
                    self._stats.groups_joined += 1
                    self._log("INFO", f"  ✅ Joined (retry): {title}")
                except Exception as e2:
                    self._stats.join_failed += 1
                    self._log("WARN", f"  ❌ Join retry failed: {title}: {e2}")
            except ChannelPrivateError:
                self._stats.join_failed += 1
                self._log("INFO", f"  🔒 Private group, skipping: {title}")
            except Exception as exc:
                self._stats.join_failed += 1
                self._log("WARN", f"  ❌ Join failed: {title}: {exc}")

            self._emit_stats()
            delay = random.uniform(self.mode.join_delay_min, self.mode.join_delay_max)
            self._log("INFO", f"  ⏱ Waiting {delay:.1f}s before next join...")
            await asyncio.sleep(delay)

        self._log("INFO", f"➕ Join phase complete — {self._stats.groups_joined} joined, {self._stats.already_member} already member")

    # ------------------------------------------------------------------
    # Phase 3 — Forward Loop
    # ------------------------------------------------------------------

    async def _phase_forward_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stats.cycle_number += 1
            self._stats.sent_this_cycle = 0
            self._stats.send_failed = 0
            joined_list = list(self._joined_ids)
            total = len(joined_list)

            self._log("INFO", f"📣 Cycle {self._stats.cycle_number} — Forwarding to {total} groups...")

            for i, group_id in enumerate(joined_list):
                if self._stop_event.is_set():
                    break

                self._log("INFO", f"  📨 Sending ({i+1}/{total}) to group ID {group_id}...")
                try:
                    # Human-like: simulate typing before sending
                    async with self.client.action(group_id, "typing"):
                        await asyncio.sleep(random.uniform(1.5, 3.5))

                    await self.client.send_message(group_id, self.promo_text)
                    self._stats.sent_this_cycle += 1
                    self._log("INFO", f"  ✅ Sent to {group_id}")

                except FloodWaitError as e:
                    self._log("WARN", f"  ⏳ FloodWait {e.seconds}s — waiting...")
                    await asyncio.sleep(e.seconds + 5)
                except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError):
                    self._log("INFO", f"  🚫 Cannot post to {group_id} — removing from list")
                    self._joined_ids.discard(group_id)
                    self._save_joined()
                    self._stats.send_failed += 1
                except Exception as exc:
                    self._stats.send_failed += 1
                    self._log("WARN", f"  ❌ Send failed to {group_id}: {exc}")

                self._emit_stats()
                # Human-like delay between sends
                delay = random.uniform(self.mode.send_delay_min, self.mode.send_delay_max)
                await asyncio.sleep(delay)

            self._log(
                "INFO",
                f"✅ Cycle {self._stats.cycle_number} complete — "
                f"Sent: {self._stats.sent_this_cycle} | Failed: {self._stats.send_failed}"
            )

            # Wait before next cycle
            wait = random.randint(self.mode.cycle_delay_min, self.mode.cycle_delay_max)
            self._log("INFO", f"⏳ Waiting {wait//60}m {wait%60}s before next cycle...")
            for _ in range(wait):
                if self._stop_event.is_set():
                    break
                await asyncio.sleep(1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, level: str, msg: str) -> None:
        logger.info("[%s] %s", level, msg)
        self._log_cb(level, msg)

    def _emit_stats(self) -> None:
        self._stats_cb(EngineStats(
            groups_found=self._stats.groups_found,
            groups_joined=self._stats.groups_joined,
            already_member=self._stats.already_member,
            join_failed=self._stats.join_failed,
            sent_this_cycle=self._stats.sent_this_cycle,
            send_failed=self._stats.send_failed,
            cycle_number=self._stats.cycle_number,
            state=self._stats.state,
        ))
