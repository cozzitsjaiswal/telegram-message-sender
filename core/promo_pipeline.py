"""
core/promo_pipeline.py — Furaya v5.5
The autonomous 3-phase pipeline:
  Phase 1: DISCOVER  — Find relevant Telegram groups by keyword
  Phase 2: JOIN      — Join the discovered groups (rate-limited)
  Phase 3: PROMOTE   — Send promotional messages to joined groups

All phases run autonomously. The GUI just shows the status.
"""

import asyncio
import logging
import random
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PipelinePhase(Enum):
    IDLE = "Idle"
    DISCOVERING = "Discovering Groups"
    JOINING = "Joining Groups"
    PROMOTING = "Sending Promotions"
    PAUSED = "Paused"
    DONE = "Done"
    ERROR = "Error"


class PromoPipeline:
    """
    Autonomous 3-phase Telegram promotion pipeline.
    Find groups → Join groups → Send promos.
    Handles flood waits, account rotation, and rate limiting automatically.
    """

    def __init__(
        self,
        account_manager,
        log_cb: Optional[Callable] = None,
        metrics_cb: Optional[Callable] = None,
        status_cb: Optional[Callable] = None,
    ):
        self.account_manager = account_manager
        self.log_cb = log_cb or (lambda level, msg: logger.info(msg))
        self.metrics_cb = metrics_cb or (lambda m: None)
        self.status_cb = status_cb or (lambda phase: None)

        # Config (set before run())
        self.keywords: List[str] = []
        self.messages: List[str] = []
        self.min_delay: float = 30.0        # seconds between messages
        self.max_delay: float = 90.0
        self.join_delay: float = 5.0        # seconds between joins
        self.max_groups_to_discover: int = 50
        self.max_groups_to_join: int = 20
        self.messages_per_group: int = 1

        # State
        self.phase = PipelinePhase.IDLE
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._discovered: List[Dict] = []   # {id, title, username, member_count}
        self._joined: List[Dict] = []       # groups we successfully joined
        self._stats = {
            "discovered": 0,
            "joined": 0,
            "sent": 0,
            "failed": 0,
            "flood_waits": 0,
            "started_at": None,
            "phase": PipelinePhase.IDLE.value,
        }

    def _log(self, level: str, msg: str):
        self.log_cb(level, msg)

    def _set_phase(self, phase: PipelinePhase):
        self.phase = phase
        self._stats["phase"] = phase.value
        self.status_cb(phase.value)
        self._emit_metrics()
        self._log("INFO", f"━━ Phase: {phase.value} ━━")

    def _emit_metrics(self):
        self.metrics_cb({**self._stats})

    # ── Public controls ────────────────────────────────────────────────

    def configure(
        self,
        keywords: List[str],
        messages: List[str],
        min_delay: float = 30,
        max_delay: float = 90,
        max_groups: int = 20,
    ):
        self.keywords = [k.strip() for k in keywords if k.strip()]
        self.messages = [m.strip() for m in messages if m.strip()]
        self.min_delay = max(10.0, float(min_delay))
        self.max_delay = max(self.min_delay + 10, float(max_delay))
        self.max_groups_to_join = max(1, int(max_groups))
        self.max_groups_to_discover = self.max_groups_to_join * 3

    def start(self):
        """Launch the pipeline in the background."""
        if self._running:
            self._log("WARN", "Pipeline already running")
            return
        if not self.keywords:
            self._log("ERROR", "No keywords set — configure the pipeline first")
            return
        if not self.messages:
            self._log("ERROR", "No promo messages set")
            return

        self._stats = {
            "discovered": 0, "joined": 0, "sent": 0,
            "failed": 0, "flood_waits": 0,
            "started_at": datetime.now().isoformat(),
            "phase": PipelinePhase.IDLE.value,
        }
        self._discovered = []
        self._joined = []
        self._running = True
        self._task = asyncio.ensure_future(self._run())

    def stop(self):
        """Stop the pipeline gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._set_phase(PipelinePhase.IDLE)

    def pause(self):
        self._set_phase(PipelinePhase.PAUSED)

    # ── Internal pipeline ──────────────────────────────────────────────

    async def _run(self):
        try:
            engines = self.account_manager.get_active_engines()
            if not engines:
                self._log("ERROR", "❌ No connected accounts! Login at least one account first.")
                self._set_phase(PipelinePhase.ERROR)
                return

            self._log("INFO", f"🚀 Pipeline starting with {len(engines)} account(s)")
            self._log("INFO", f"📋 Keywords: {', '.join(self.keywords)}")

            # ── Phase 1: Discover ──────────────────────────────────────
            if self._running:
                await self._phase_discover(engines)

            # ── Phase 2: Join ──────────────────────────────────────────
            if self._running and self._discovered:
                await self._phase_join(engines)

            # ── Phase 3: Promote ───────────────────────────────────────
            if self._running and self._joined:
                await self._phase_promote(engines)

            if self._running:
                self._set_phase(PipelinePhase.DONE)
                self._log("INFO", f"✅ Pipeline complete — {self._stats['sent']} messages sent to {self._stats['joined']} groups")

        except asyncio.CancelledError:
            self._log("INFO", "Pipeline stopped by user")
        except Exception as e:
            self._log("ERROR", f"Pipeline error: {e}")
            self._set_phase(PipelinePhase.ERROR)
        finally:
            self._running = False

    # ── Phase 1: Discover groups ───────────────────────────────────────

    async def _phase_discover(self, engines):
        self._set_phase(PipelinePhase.DISCOVERING)
        seen_ids = set()

        for keyword in self.keywords:
            if not self._running:
                break

            self._log("INFO", f"🔍 Searching groups for: '{keyword}'")

            # Round-robin across accounts for discovery
            for engine in engines:
                if not self._running:
                    break
                try:
                    groups = await engine.search_groups(keyword, limit=20)
                    new = 0
                    for g in groups:
                        gid = g.get("id")
                        if gid and gid not in seen_ids:
                            seen_ids.add(gid)
                            self._discovered.append(g)
                            new += 1
                            self._stats["discovered"] += 1

                    if new:
                        self._log("INFO", f"  Found {new} new groups for '{keyword}' ({self._stats['discovered']} total)")
                        self._emit_metrics()

                    await asyncio.sleep(2.0)  # Be nice to the API

                    if len(self._discovered) >= self.max_groups_to_discover:
                        break

                except Exception as e:
                    self._log("WARN", f"Search failed: {e}")
                    continue

            if len(self._discovered) >= self.max_groups_to_discover:
                break

        self._log("INFO", f"✅ Discovery done — {self._stats['discovered']} groups found")

    # ── Phase 2: Join groups ───────────────────────────────────────────

    async def _phase_join(self, engines):
        self._set_phase(PipelinePhase.JOINING)
        to_join = self._discovered[:self.max_groups_to_join]

        # Sort by member count descending (bigger = better audience)
        to_join.sort(key=lambda g: g.get("member_count", 0), reverse=True)

        self._log("INFO", f"📥 Joining {len(to_join)} groups...")

        engine_idx = 0
        for group in to_join:
            if not self._running:
                break

            engine = engines[engine_idx % len(engines)]
            engine_idx += 1

            username = group.get("username", "")
            title = group.get("title", str(group.get("id", "?")))

            if not username:
                self._log("WARN", f"  Skipping '{title}' — no username")
                continue

            try:
                self._log("INFO", f"  Joining @{username} ({title})...")
                success = await engine.join_chat(f"@{username}")
                if success:
                    self._joined.append(group)
                    self._stats["joined"] += 1
                    self._log("INFO", f"  ✅ Joined @{username}")
                else:
                    self._log("WARN", f"  ⚠️ Failed to join @{username}")

                self._emit_metrics()
                await asyncio.sleep(self.join_delay + random.uniform(0, 3))

            except Exception as e:
                err = str(e).lower()
                if "flood" in err:
                    wait = self._extract_flood_wait(str(e))
                    self._stats["flood_waits"] += 1
                    self._log("WARN", f"  ⏳ Flood wait {wait}s — pausing...")
                    await asyncio.sleep(wait)
                else:
                    self._log("WARN", f"  Join error for @{username}: {e}")

        self._log("INFO", f"✅ Join phase done — {self._stats['joined']} groups joined")

    # ── Phase 3: Promote ───────────────────────────────────────────────

    async def _phase_promote(self, engines):
        self._set_phase(PipelinePhase.PROMOTING)
        msg_idx = 0
        engine_idx = 0

        self._log("INFO", f"📣 Sending promotions to {len(self._joined)} groups...")

        for group in self._joined:
            if not self._running:
                break

            engine = engines[engine_idx % len(engines)]
            engine_idx += 1

            message = self.messages[msg_idx % len(self.messages)]
            msg_idx += 1

            chat_id = group.get("id")
            title = group.get("title", "?")

            if not chat_id:
                continue

            try:
                self._log("INFO", f"  📨 Sending to {title}...")
                success = await engine.send_message(chat_id, message)
                if success:
                    self._stats["sent"] += 1
                    self._log("INFO", f"  ✅ Sent to {title}")
                else:
                    self._stats["failed"] += 1
                    self._log("WARN", f"  ⚠️ Send failed to {title}")

                self._emit_metrics()

                # Human-like randomized delay
                delay = random.uniform(self.min_delay, self.max_delay)
                self._log("INFO", f"  ⏱ Waiting {delay:.0f}s...")
                await asyncio.sleep(delay)

            except Exception as e:
                err = str(e).lower()
                if "flood" in err:
                    wait = self._extract_flood_wait(str(e))
                    self._stats["flood_waits"] += 1
                    self._log("WARN", f"  ⏳ Flood wait {wait}s — pausing...")
                    await asyncio.sleep(wait)
                elif "banned" in err or "blocked" in err:
                    self._log("ERROR", f"  ❌ Account banned/blocked from {title}")
                else:
                    self._stats["failed"] += 1
                    self._log("WARN", f"  Send error to {title}: {e}")

        self._log("INFO", f"✅ Promotion done — {self._stats['sent']} sent, {self._stats['failed']} failed")

    def _extract_flood_wait(self, error_str: str) -> float:
        """Extract flood wait seconds from error message."""
        import re
        m = re.search(r"(\d+)", error_str)
        return float(m.group(1)) if m else 60.0
