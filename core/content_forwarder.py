"""
core/content_forwarder.py

Rule-based auto-forwarder that monitors source chats and forwards
matching messages to target chats. Runs as a persistent background
event handler via Telethon's @client.on(events.NewMessage).

Rules are persisted in JSON. Duplicate detection via deque of last 10k IDs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional

from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    ChannelPrivateError,
    UserBannedInChannelError,
)

logger = logging.getLogger(__name__)
DATA_DIR = Path.home() / "FurayaPromoEngine" / "forwarder"


@dataclass
class ForwardRule:
    """A single forwarding rule."""
    name: str
    source_chats: List[str]       # usernames or IDs to monitor
    target_chats: List[str]       # usernames or IDs to forward to
    keywords: List[str] = field(default_factory=list)  # empty = forward all
    max_daily: int = 100          # cap per day
    enabled: bool = True

    # Runtime counters (not persisted)
    forwarded_today: int = field(default=0, init=False, repr=False)
    last_reset_day: str = field(default="", init=False, repr=False)

    def matches(self, text: str) -> bool:
        """True if message matches keywords (or no keywords = match all)."""
        if not self.keywords:
            return True
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)

    def can_forward(self) -> bool:
        today = time.strftime("%Y-%m-%d")
        if self.last_reset_day != today:
            self.forwarded_today = 0
            self.last_reset_day = today
        return self.forwarded_today < self.max_daily

    def record_forward(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self.last_reset_day != today:
            self.forwarded_today = 0
            self.last_reset_day = today
        self.forwarded_today += 1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source_chats": self.source_chats,
            "target_chats": self.target_chats,
            "keywords": self.keywords,
            "max_daily": self.max_daily,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(d: dict) -> "ForwardRule":
        return ForwardRule(
            name=d["name"],
            source_chats=d.get("source_chats", []),
            target_chats=d.get("target_chats", []),
            keywords=d.get("keywords", []),
            max_daily=d.get("max_daily", 100),
            enabled=d.get("enabled", True),
        )


@dataclass
class ForwardStats:
    total_forwarded: int = 0
    total_failed: int = 0
    total_skipped_dup: int = 0
    total_skipped_limit: int = 0
    rules_active: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class ContentForwarder:
    """
    Manages forwarding rules and registers Telethon event handlers.

    Sample rule JSON:
    {
        "name": "crypto_signals",
        "source_chats": ["@crypto_signals_vip", "@btc_analysis"],
        "target_chats": ["@my_group1", "@my_group2"],
        "keywords": ["buy", "sell", "signal", "alert"],
        "max_daily": 50,
        "enabled": true
    }
    """

    def __init__(self) -> None:
        self._data_dir = DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._rules_file = self._data_dir / "forward_rules.json"
        self._stats_file = self._data_dir / "forward_stats.json"

        self._rules: Dict[str, ForwardRule] = {}
        self._seen_ids: Deque[int] = deque(maxlen=10_000)
        self._client: Optional[TelegramClient] = None
        self._handler = None
        self._running = False
        self._stats = ForwardStats()
        self._log_cb: Optional[Callable[[str, str], None]] = None

        self._load_rules()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_rules(self) -> None:
        if self._rules_file.exists():
            try:
                raw = json.loads(self._rules_file.read_text("utf-8"))
                for d in raw:
                    rule = ForwardRule.from_dict(d)
                    self._rules[rule.name] = rule
                logger.info("Loaded %d forward rules", len(self._rules))
            except Exception as e:
                logger.error("Failed to load forward rules: %s", e)

    def _save_rules(self) -> None:
        data = [r.to_dict() for r in self._rules.values()]
        self._rules_file.write_text(json.dumps(data, indent=2), "utf-8")

    def _save_stats(self) -> None:
        self._stats_file.write_text(json.dumps(self._stats.to_dict(), indent=2), "utf-8")

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: ForwardRule) -> bool:
        if rule.name in self._rules:
            return False
        self._rules[rule.name] = rule
        self._save_rules()
        logger.info("Added forward rule: %s", rule.name)
        return True

    def remove_rule(self, name: str) -> bool:
        if name in self._rules:
            del self._rules[name]
            self._save_rules()
            return True
        return False

    def update_rule(self, name: str, **kwargs) -> bool:
        rule = self._rules.get(name)
        if not rule:
            return False
        for k, v in kwargs.items():
            if hasattr(rule, k):
                setattr(rule, k, v)
        self._save_rules()
        return True

    def get_rules(self) -> List[ForwardRule]:
        return list(self._rules.values())

    def get_rule(self, name: str) -> Optional[ForwardRule]:
        return self._rules.get(name)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    async def start_forwarding(
        self,
        client: TelegramClient,
        log_cb: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Register the event handler to start monitoring source chats."""
        self._client = client
        self._log_cb = log_cb
        self._running = True

        # Collect all source chats across all enabled rules
        source_chats = set()
        active = 0
        for rule in self._rules.values():
            if rule.enabled:
                active += 1
                for sc in rule.source_chats:
                    source_chats.add(sc)
        self._stats.rules_active = active

        if not source_chats:
            self._log("WARN", "No source chats configured in any rule")
            return

        # Register a single handler that checks all rules
        @client.on(events.NewMessage(chats=list(source_chats)))
        async def _on_new_message(event):
            if not self._running:
                return
            await self._handle_message(event)

        self._handler = _on_new_message
        self._log("INFO", f"📡 Forwarder started — monitoring {len(source_chats)} source chats, {active} rules active")

    def stop(self) -> None:
        """Unregister the event handler."""
        self._running = False
        if self._client and self._handler:
            try:
                self._client.remove_event_handler(self._handler)
            except Exception:
                pass
        self._save_stats()
        self._log("INFO", "🛑 Forwarder stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def _handle_message(self, event) -> None:
        """Process an incoming message against all rules."""
        msg_id = event.message.id
        text = event.message.message or ""

        # Duplicate check
        if msg_id in self._seen_ids:
            self._stats.total_skipped_dup += 1
            return
        self._seen_ids.append(msg_id)

        sender_chat = event.chat_id

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Check if source matches
            source_match = False
            for sc in rule.source_chats:
                try:
                    entity = await self._client.get_input_entity(sc)
                    if hasattr(entity, "channel_id") and entity.channel_id == sender_chat:
                        source_match = True
                        break
                    if hasattr(entity, "chat_id") and entity.chat_id == sender_chat:
                        source_match = True
                        break
                except Exception:
                    # Fallback: string match
                    if str(sender_chat) in str(sc):
                        source_match = True
                        break

            if not source_match:
                continue

            # Keyword filter
            if not rule.matches(text):
                continue

            # Daily limit
            if not rule.can_forward():
                self._stats.total_skipped_limit += 1
                self._log("INFO", f"⚠️ [{rule.name}] Daily limit ({rule.max_daily}) reached")
                continue

            # Forward to all targets
            for target in rule.target_chats:
                asyncio.create_task(self._forward_to(event, target, rule))

    async def _forward_to(self, event, target: str, rule: ForwardRule) -> None:
        """Forward a single message to a target chat."""
        try:
            await asyncio.sleep(random.uniform(1.0, 3.0))  # human-like delay
            await self._client.forward_messages(target, event.message)
            rule.record_forward()
            self._stats.total_forwarded += 1
            self._save_stats()
            self._log("INFO", f"✅ [{rule.name}] Forwarded to {target}")

        except FloodWaitError as e:
            self._log("WARN", f"⏳ [{rule.name}] FloodWait {e.seconds}s forwarding to {target}")
            await asyncio.sleep(e.seconds + 2)
            try:
                await self._client.forward_messages(target, event.message)
                rule.record_forward()
                self._stats.total_forwarded += 1
            except Exception:
                self._stats.total_failed += 1

        except (ChatWriteForbiddenError, ChannelPrivateError, UserBannedInChannelError) as e:
            self._stats.total_failed += 1
            self._log("WARN", f"🚫 [{rule.name}] Cannot forward to {target}: {type(e).__name__}")

        except Exception as e:
            self._stats.total_failed += 1
            logger.error("[%s] Forward error to %s: %s", rule.name, target, e)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> ForwardStats:
        return self._stats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, level: str, msg: str) -> None:
        logger.info("[%s] %s", level, msg)
        if self._log_cb:
            self._log_cb(level, msg)
