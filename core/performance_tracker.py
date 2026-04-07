"""PerformanceTracker — records and persists all campaign metrics."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List

DATA_FILE = Path("data/performance.json")


@dataclass
class AccountMetrics:
    phone: str
    sent: int = 0
    success: int = 0
    failed: int = 0
    flood_waits: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success + self.failed
        return (self.success / total * 100) if total else 0.0


@dataclass
class SessionRecord:
    started_at: float
    ended_at: float = 0.0
    waves: int = 0
    total_sent: int = 0
    total_success: int = 0
    total_failed: int = 0
    mode: str = "Normal"

    @property
    def success_rate(self) -> float:
        total = self.total_success + self.total_failed
        return (self.total_success / total * 100) if total else 0.0

    @property
    def duration_minutes(self) -> float:
        end = self.ended_at or time.time()
        return (end - self.started_at) / 60

    def to_dict(self) -> dict:
        return asdict(self)


class PerformanceTracker:
    def __init__(self) -> None:
        self._accounts: Dict[str, AccountMetrics] = {}
        self._sessions: List[SessionRecord] = []
        self._current_session: SessionRecord | None = None
        self.load()

    def load(self) -> None:
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                for phone, m in data.get("accounts", {}).items():
                    self._accounts[phone] = AccountMetrics(phone=phone, **{
                        k: v for k, v in m.items() if k != "phone"
                    })
                self._sessions = [
                    SessionRecord(**s) for s in data.get("sessions", [])
                ]
            except Exception:
                pass

    def save(self) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(
            json.dumps({
                "accounts": {p: asdict(m) for p, m in self._accounts.items()},
                "sessions": [s.to_dict() for s in self._sessions[-50:]],  # keep last 50
            }, indent=2),
            encoding="utf-8",
        )

    def start_session(self, mode: str = "Normal") -> None:
        self._current_session = SessionRecord(started_at=time.time(), mode=mode)

    def end_session(self) -> None:
        if self._current_session:
            self._current_session.ended_at = time.time()
            self._sessions.append(self._current_session)
            self._current_session = None
            self.save()

    def record_send(self, phone: str, success: bool) -> None:
        if phone not in self._accounts:
            self._accounts[phone] = AccountMetrics(phone=phone)
        m = self._accounts[phone]
        m.sent += 1
        if success:
            m.success += 1
        else:
            m.failed += 1

        if self._current_session:
            self._current_session.total_sent += 1
            if success:
                self._current_session.total_success += 1
            else:
                self._current_session.total_failed += 1

        # Save every 10 sends
        if m.sent % 10 == 0:
            self.save()

    def record_flood(self, phone: str) -> None:
        if phone not in self._accounts:
            self._accounts[phone] = AccountMetrics(phone=phone)
        self._accounts[phone].flood_waits += 1

    def record_wave(self) -> None:
        if self._current_session:
            self._current_session.waves += 1

    def get_account_metrics(self) -> List[AccountMetrics]:
        return list(self._accounts.values())

    def get_sessions(self) -> List[SessionRecord]:
        return list(self._sessions)

    def get_current_session(self) -> SessionRecord | None:
        return self._current_session

    @property
    def total_sent_ever(self) -> int:
        return sum(m.sent for m in self._accounts.values())

    @property
    def overall_success_rate(self) -> float:
        total_s = sum(m.success for m in self._accounts.values())
        total_f = sum(m.failed for m in self._accounts.values())
        total = total_s + total_f
        return (total_s / total * 100) if total else 0.0
