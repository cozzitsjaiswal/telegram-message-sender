"""CampaignController — the brain. Orchestrates all modules."""
from __future__ import annotations

import asyncio
import logging
import random
from enum import Enum
from typing import Callable, Dict, List, Optional

from core.account_manager import AccountManager
from core.adaptive_engine import AdaptiveEngine, CampaignMode
from core.group_manager import GroupManager
from core.message_engine import MessageEngine
from core.performance_tracker import PerformanceTracker
from core.promotion_engine import PromotionEngine
from core.task_queue import TaskQueue, Task

logger = logging.getLogger(__name__)


class CampaignState(str, Enum):
    IDLE         = "Idle"
    INITIALIZING = "Initializing"
    RUNNING      = "Running"
    PAUSED       = "Paused"
    STOPPING     = "Stopping"
    STOPPED      = "Stopped"
    ERROR        = "Error"


class CampaignController:
    """
    The executive brain of the system.
    Wires together: AccountManager, GroupManager, MessageEngine,
    TaskQueue, AdaptiveEngine, PerformanceTracker, PromotionEngine.
    """

    def __init__(
        self,
        account_manager: AccountManager,
        group_manager: GroupManager,
        message_engine: MessageEngine,
        performance_tracker: PerformanceTracker,
        log_cb: Optional[Callable[[str, str], None]] = None,
        metrics_cb: Optional[Callable[[dict], None]] = None,
        state_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.accounts   = account_manager
        self.groups     = group_manager
        self.messages   = message_engine
        self.perf       = performance_tracker
        self._log_cb    = log_cb    or (lambda l, m: None)
        self._metrics_cb= metrics_cb or (lambda d: None)
        self._state_cb  = state_cb  or (lambda s: None)

        self._queue   = TaskQueue()
        self._adaptive= AdaptiveEngine()
        self._engines : Dict[str, PromotionEngine] = {}

        self._state        = CampaignState.IDLE
        self._stop_event   = asyncio.Event()
        self._pause_event  = asyncio.Event()
        self._pause_event.set()   # not paused by default
        self._task: Optional[asyncio.Task] = None
        self._wave_number  = 0

    # ------------------------------------------------------------------
    # Public control API
    # ------------------------------------------------------------------

    async def start(self, mode: str = "Normal") -> None:
        if self._state in (CampaignState.RUNNING, CampaignState.INITIALIZING):
            return
        self._stop_event.clear()
        self._pause_event.set()
        self._adaptive.set_mode(CampaignMode(mode))
        self._set_state(CampaignState.INITIALIZING)
        self.perf.start_session(mode)
        self._task = asyncio.ensure_future(self._run_loop())

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()   # unblock any pause wait
        self._set_state(CampaignState.STOPPING)

    def pause(self) -> None:
        self._pause_event.clear()
        self._set_state(CampaignState.PAUSED)

    def resume(self) -> None:
        self._pause_event.set()
        self._set_state(CampaignState.RUNNING)

    @property
    def state(self) -> CampaignState:
        return self._state

    # ------------------------------------------------------------------
    # Internal run loop
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        try:
            # --- Setup engines per account ---
            active_accounts = self.accounts.get_active()
            if not active_accounts:
                self._log("ERROR", "No active accounts. Add and log in at least one account.")
                self._set_state(CampaignState.ERROR)
                return

            for acc in active_accounts:
                if acc.client:
                    self._engines[acc.phone] = PromotionEngine(acc.client, acc.phone)

            if not self._engines:
                self._log("ERROR", "No authenticated clients available.")
                self._set_state(CampaignState.ERROR)
                return

            self._set_state(CampaignState.RUNNING)
            self._log("INFO", f"🚀 Campaign started — {len(self._engines)} account(s) active")

            while not self._stop_event.is_set():
                # --- Wait if paused ---
                await self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                # --- Build task queue ---
                active_groups = self.groups.get_ranked()
                if not active_groups:
                    self._log("WARN", "⚠️ No joined groups available. Add groups first.")
                    await self._sleep(30)
                    continue

                engine_list = [
                    self.accounts.get_by_phone(p)
                    for p in self._engines.keys()
                    if self.accounts.get_by_phone(p) and self.accounts.get_by_phone(p).is_available
                ]
                if not engine_list:
                    self._log("WARN", "All accounts on cooldown. Waiting...")
                    await self._sleep(60)
                    continue

                n_built = self._queue.build(
                    engine_list,
                    active_groups,
                    lambda: self.messages.next_message(apply_variation=True),
                )
                self._log("INFO", f"📋 Queue built — {n_built} tasks")
                self._wave_number = 0

                # --- Wave loop ---
                while not self._queue.is_empty() and not self._stop_event.is_set():
                    await self._pause_event.wait()
                    self._wave_number += 1
                    wave_size = self._adaptive.wave_size

                    self._log("INFO", f"🌊 Wave {self._wave_number} — executing {wave_size} tasks")
                    self.perf.record_wave()

                    for _ in range(wave_size):
                        if self._queue.is_empty() or self._stop_event.is_set():
                            break

                        task = self._queue.next()
                        if not task:
                            break

                        await self._execute_task(task)
                        self._emit_metrics()

                        # inter-task delay
                        delay = random.uniform(
                            self._adaptive.send_delay_min,
                            self._adaptive.send_delay_max,
                        )
                        await self._sleep(delay)

                    # wave pause
                    if not self._queue.is_empty() and not self._stop_event.is_set():
                        pause = random.uniform(
                            self._adaptive.wave_pause_min,
                            self._adaptive.wave_pause_max,
                        )
                        self._log("INFO", f"⏸ Wave pause {pause:.0f}s...")
                        await self._sleep(pause)

                self._log("INFO", f"✅ All {self._queue.done_count} tasks completed. Rebuilding next cycle...")
                # Brief rest before next cycle
                await self._sleep(random.uniform(30, 60))

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("CampaignController unhandled error: %s", exc)
            self._log("ERROR", f"💥 Controller error: {exc}")
            self._set_state(CampaignState.ERROR)
        finally:
            self.perf.end_session()
            self.perf.save()
            self._set_state(CampaignState.STOPPED)
            self._log("INFO", "🛑 Campaign stopped.")

    async def _execute_task(self, task: Task) -> None:
        engine = self._engines.get(task.account_phone)
        if not engine:
            self._queue.mark_skipped(task)
            return

        success, error = await engine.send_message(task.group_username, task.message_text)

        if success:
            self._queue.mark_done(task)
            self.groups.record_success(task.group_username)
            self.perf.record_send(task.account_phone, True)
            self._adaptive.record_success()
            self.messages.record_success(task.message_text)
        else:
            if error.startswith("FloodWait:"):
                seconds = int(error.split(":")[1])
                self._log("WARN", f"⏳ FloodWait {seconds}s on {task.account_phone}")
                self.perf.record_flood(task.account_phone)
                acc = self.accounts.get_by_phone(task.account_phone)
                if acc:
                    acc.mark_flood(seconds)
                await self._sleep(min(seconds, 60))  # cap wait at 60s, requeue later
                self._queue.mark_failed(task, error)
            elif error in ("ChatWriteForbiddenError", "UserBannedInChannelError",
                           "ChannelPrivateError", "UserNotParticipantError"):
                self._queue.mark_skipped(task)
                self.groups.record_failure(task.group_username)
            else:
                self._queue.mark_failed(task, error)
                self.groups.record_failure(task.group_username)
                self.perf.record_send(task.account_phone, False)
                self._adaptive.record_failure()
                self.messages.record_failure(task.message_text)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    def _set_state(self, state: CampaignState) -> None:
        self._state = state
        self._state_cb(state.value)

    def _log(self, level: str, msg: str) -> None:
        logger.info("[%s] %s", level, msg)
        self._log_cb(level, msg)

    def _emit_metrics(self) -> None:
        self._metrics_cb({
            "state": self._state.value,
            "wave": self._wave_number,
            "pending": self._queue.pending_count,
            "done": self._queue.done_count,
            "failed": self._queue.failed_count,
            "success_rate": round(self._queue.success_rate, 1),
            "active_accounts": len(self._engines),
            "adaptive": self._adaptive.get_status(),
            "total_sent": self.perf.total_sent_ever,
        })
