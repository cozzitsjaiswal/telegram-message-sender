"""Group model and GroupManager — persists all discovered/joined groups."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

DATA_FILE = Path("data/groups.json")


@dataclass
class Group:
    username: str          # "@group" or invite hash
    title: str = ""
    member_count: int = 0
    joined: bool = False
    last_used: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    priority_score: float = 50.0
    disabled: bool = False

    def record_success(self) -> None:
        self.success_count += 1
        self.last_used = time.time()
        self.priority_score = min(100.0, self.priority_score + 2.0)

    def record_failure(self) -> None:
        self.failure_count += 1
        self.priority_score = max(0.0, self.priority_score - 5.0)
        if self.priority_score == 0:
            self.disabled = True

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total else 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Group":
        return Group(**{k: v for k, v in d.items() if k in Group.__dataclass_fields__})


class GroupManager:
    def __init__(self) -> None:
        self._groups: Dict[str, Group] = {}
        self.load()

    def load(self) -> None:
        if DATA_FILE.exists():
            try:
                raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    for d in raw:
                        g = Group.from_dict(d)
                        self._groups[g.username] = g
                elif isinstance(raw, dict):
                    for uname, d in raw.items():
                        self._groups[uname] = Group.from_dict(d)
            except Exception:
                pass

    def save(self) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(
            json.dumps([g.to_dict() for g in self._groups.values()], indent=2),
            encoding="utf-8",
        )

    def add(self, group: Group) -> bool:
        """Returns True if added (not duplicate)."""
        if group.username in self._groups:
            return False
        self._groups[group.username] = group
        self.save()
        return True

    def get_all(self) -> List[Group]:
        return list(self._groups.values())

    def get_active(self) -> List[Group]:
        return [g for g in self._groups.values() if g.joined and not g.disabled]

    def get_by_username(self, username: str) -> Optional[Group]:
        return self._groups.get(username)

    def mark_joined(self, username: str) -> None:
        if username in self._groups:
            self._groups[username].joined = True
            self.save()

    def record_success(self, username: str) -> None:
        if username in self._groups:
            self._groups[username].record_success()
            self.save()

    def record_failure(self, username: str) -> None:
        if username in self._groups:
            self._groups[username].record_failure()
            self.save()

    def get_ranked(self) -> List[Group]:
        active = self.get_active()
        return sorted(active, key=lambda g: g.priority_score, reverse=True)

    def __len__(self) -> int:
        return len(self._groups)

    @property
    def joined_count(self) -> int:
        return sum(1 for g in self._groups.values() if g.joined)
