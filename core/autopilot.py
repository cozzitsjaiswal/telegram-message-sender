"""
core/autopilot.py  — Enterprise TDLib Engine v5.0

Full autonomous 24/7 engine using local TDLib processes instead of MTProto.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.account_manager import AccountManager
from core.group_manager import GroupManager, Group
from core.message_engine import MessageEngine

logger = logging.getLogger(__name__)
STATE_DIR = Path.home() / "FurayaPromoEngine" / "autopilot"

class Phase(str, Enum):
    IDLE      = "Idle"
    DISCOVER  = "🔍 Discovering"
    JOIN      = "➕ Joining"
    PROMOTE   = "📨 Promoting"
    ANALYZE   = "📊 Analyzing"
    REST      = "😴 Resting"
    PAUSED    = "⏸ Paused"
    ERROR     = "❌ Error"

@dataclass
class AutoPilotStats:
    cycles_completed: int = 0
    total_discovered: int = 0
    total_joined: int = 0
    total_promoted: int = 0
    total_forwarded: int = 0
    total_errors: int = 0
    total_uptime_sec: float = 0.0
    last_cycle_time: str = ""
    current_phase: str = "Idle"
    consecutive_failures: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_uptime_hours"] = round(self.total_uptime_sec / 3600, 2)
        return d

@dataclass
class CycleConfig:
    keywords: List[str] = field(default_factory=list)
    discovery_limit: int = 50
    join_delay: int = 6
    send_delay_min: int = 30
    send_delay_max: int = 90
    rest_min: int = 300
    rest_max: int = 1800
    max_promote_per_cycle: int = 50

class AutoPilot:
    def __init__(
        self,
        account_manager: AccountManager,
        group_manager: GroupManager,
        message_engine: MessageEngine,
        on_event: Optional[Callable[[str, str], None]] = None,
        on_phase: Optional[Callable[[str], None]] = None,
        on_stats: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._accounts = account_manager
        self._groups = group_manager
        self._messages = message_engine
        self._on_event = on_event
        self._on_phase = on_phase
        self._on_stats = on_stats

        self._config = CycleConfig()
        self._stats = AutoPilotStats()
        self._running = False
        self._paused = False
        self._start_time = 0.0

        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._state_file = STATE_DIR / "tdlib_autopilot_state.json"

    def configure(self, **kw):
        for k, v in kw.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)

    @property
    def config(self): return self._config
    @property
    def stats(self): return self._stats
    @property
    def is_running(self): return self._running
    @property
    def is_paused(self): return self._paused
    @property
    def current_phase(self): return self._stats.current_phase

    def _emit(self, level: str, msg: str):
        if self._on_event: self._on_event(level, msg)

    def _set_phase(self, phase: Phase):
        self._stats.current_phase = phase.value
        if self._on_phase: self._on_phase(phase.value)
        self._emit_stats()

    def _emit_stats(self):
        if self._running and self._start_time > 0:
            self._stats.total_uptime_sec = time.time() - self._start_time
        if self._on_stats:
            d = self._stats.to_dict()
            self._on_stats(d)
        
        with open(self._state_file, 'w', encoding='utf-8') as f:
            json.dump(self._stats.to_dict(), f)

    def pause(self):
        self._paused = True
        self._set_phase(Phase.PAUSED)
        self._emit("WARN", "AutoPilot paused by user.")

    def resume(self):
        self._paused = False
        self._emit("INFO", "AutoPilot resumed.")

    def stop(self):
        self._running = False
        self._paused = False
        self._set_phase(Phase.IDLE)
        self._emit("WARN", "AutoPilot stopped.")

    async def run(self):
        if self._running:
            return
            
        if not self._config.keywords:
            self._emit("ERROR", "No keywords configured for discovery!")
            return

        self._running = True
        self._start_time = time.time()
        self._emit("INFO", "🚀 Enterprise TDLib AutoPilot ENGAGED")

        while self._running:
            try:
                active_engines = []
                for acc in self._accounts.get_active():
                    if acc.get('engine'):
                        active_engines.append((acc, acc['engine']))

                if not active_engines:
                    self._emit("WARN", "No active TDLib accounts available! Sleeping 30s...")
                    await self._sleep_check(30)
                    continue

                self._emit("INFO", f"Starting cycle #{self._stats.cycles_completed + 1} with {len(active_engines)} accounts")

                await self._phase_discover(active_engines)
                await self._phase_join(active_engines)
                await self._phase_promote(active_engines)

                self._stats.cycles_completed += 1
                self._stats.consecutive_failures = 0
                self._emit_stats()

                rest_sec = random.randint(self._config.rest_min, self._config.rest_max)
                self._set_phase(Phase.REST)
                self._emit("INFO", f"Cycle complete. Resting for {rest_sec} seconds...")
                await self._sleep_check(rest_sec)

            except Exception as e:
                import traceback
                traceback.print_exc()
                self._emit("ERROR", f"CRITICAL LOOP ERROR: {e}")
                self._stats.consecutive_failures += 1
                self._stats.total_errors += 1
                backoff = min(600, 30 * (2 ** self._stats.consecutive_failures))
                self._emit("WARN", f"Engine recovering in {backoff} seconds...")
                await self._sleep_check(backoff)

        self._emit("INFO", "⏹ AutoPilot shutdown complete.")

    async def _sleep_check(self, seconds: int):
        for _ in range(seconds):
            if not self._running: break
            while self._paused and self._running:
                await asyncio.sleep(1)
            await asyncio.sleep(1)

    async def _phase_discover(self, engines):
        self._set_phase(Phase.DISCOVER)
        self._emit("INFO", "🔍 Gathering groups via TDLib...")
        kw = random.choice(self._config.keywords)
        acc, engine = random.choice(engines)
        
        self._emit("INFO", f"   >> Keyword: {kw} with {acc.get('phone')}")
        
        try:
            # Note: Tdlib searchPublicChats uses searchChatsOnServer, or searchPublicChat for single entities.
            # To get multiple, we use searchPublicChats
            chat_ids = await engine.search_public_chats(kw)
            
            found = 0
            for cid in chat_ids:
                chat_info = await engine.client.invoke({
                    "@type": "getChat",
                    "chat_id": cid
                }) if hasattr(engine, 'client') and engine.client else {}
                
                title = chat_info.get("title", f"Chat_{cid}")
                if chat_info.get("@type") == "chat":
                    self._emit("INFO", f"   • Found: {title} ({cid})")
                    found += 1
                    # we mock a username or use the id as string since TDLib tracks by integer id
                    self._groups.add(Group(username=str(cid), title=title))
                    
            self._stats.total_discovered += found
            self._emit_stats()
            
        except Exception as e:
            self._emit("ERROR", f"Discovery error: {e}")
            self._stats.total_errors += 1

    async def _phase_join(self, engines):
        self._set_phase(Phase.JOIN)
        unjoined = [g for g in self._groups.get_all() if not g.joined and not g.disabled]
        if not unjoined:
            self._emit("INFO", "⏭ No groups to join")
            return
            
        target = random.choice(unjoined)
        acc, engine = random.choice(engines)
        
        self._emit("INFO", f"➕ Joining {target.title}...")
        try:
            cid = str(target.username)
            # engine.join_chat returns bool
            success = await engine.join_chat(cid)
            if success:
                target.joined = True
                self._stats.total_joined += 1
                self._emit("INFO", "   ✅ Registered Join!")
            else:
                self._emit("ERROR", "Failed to join")
                target.disabled = True
                target.record_failure()
        except:
            target.disabled = True
            
        self._groups.save()
        self._emit_stats()
        await self._sleep_check(self._config.join_delay)

    def get_full_status(self) -> dict:
        d = self._stats.to_dict()
        d["health_score"] = self.get_health_score()
        d["accounts_online"] = len(self._accounts.get_active())
        d["accounts_total"] = self._accounts.total_count
        d["accounts_flooded"] = 0 # Handled internally by TDLib
        d["is_running"] = self._running
        d["is_paused"] = self._paused
        return d

    def get_health_score(self) -> int:
        score = 0
        active = len(self._accounts.get_active())
        total = self._accounts.total_count
        if total > 0:
            score += int((active / total) * 70)
        else:
            return 0
        if self._stats.consecutive_failures == 0:
            score += 30
        elif self._stats.consecutive_failures == 1:
            score += 15
        return min(100, score)

    async def _phase_promote(self, engines):
        self._set_phase(Phase.PROMOTE)
        promotable = [g for g in self._groups.get_active() if g.joined]
        if not promotable:
            self._emit("INFO", "⏭ No groups ready to promote in")
            return

        to_promote = random.sample(promotable, min(len(promotable), self._config.max_promote_per_cycle))
        self._emit("INFO", f"📨 Broadcasting to {len(to_promote)} groups...")

        for target in to_promote:
            if not self._running: break
            
            acc, engine = random.choice(engines)
            msg = self._messages.next_message()
            if not msg:
                break

            try:
                cid = int(target.username)
                res = await engine.send_message(cid, msg.text)
                
                if res and res.get("@type") == "message":
                    target.record_success()
                    self._stats.total_promoted += 1
                    self._emit("INFO", f"   ✅ Sent to {target.title} via {acc.get('phone')}")
                else:
                    self._emit("WARN", f"   ❌ Failed {target.title}: Could not send")
                    target.record_failure()
            except Exception as e:
                self._emit("ERROR", f"Send Error: {e}")
                target.record_failure()
                
            self._emit_stats()
            delay = random.randint(self._config.send_delay_min, self._config.send_delay_max)
            await self._sleep_check(delay)
