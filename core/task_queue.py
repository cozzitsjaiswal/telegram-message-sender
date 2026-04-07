"""TaskQueue — structured (account, group, message) task management."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Deque, List, Optional
from collections import deque

STATE_FILE = Path("data/state.json")


class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    RETRYING  = "retrying"


@dataclass
class Task:
    task_id: int
    account_phone: str
    group_username: str
    message_text: str
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 2
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    error: str = ""

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "account_phone": self.account_phone,
            "group_username": self.group_username,
            "message_text": self.message_text,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class TaskQueue:
    def __init__(self) -> None:
        self._queue: Deque[Task] = deque()
        self._completed: List[Task] = []
        self._failed: List[Task] = []
        self._task_counter: int = 0

    def build(self, accounts: list, groups: list, message_fn) -> int:
        """Build balanced queue: distribute groups across accounts."""
        self._queue.clear()
        self._completed.clear()
        self._failed.clear()
        if not accounts or not groups:
            return 0

        for i, group in enumerate(groups):
            account = accounts[i % len(accounts)]
            msg = message_fn()
            if not msg:
                continue
            self._task_counter += 1
            task = Task(
                task_id=self._task_counter,
                account_phone=account.phone,
                group_username=group.username,
                message_text=msg,
            )
            self._queue.append(task)

        return len(self._queue)

    def next(self) -> Optional[Task]:
        if self._queue:
            t = self._queue.popleft()
            t.status = TaskStatus.RUNNING
            return t
        return None

    def mark_done(self, task: Task) -> None:
        task.status = TaskStatus.DONE
        task.completed_at = time.time()
        self._completed.append(task)

    def mark_failed(self, task: Task, error: str) -> None:
        task.error = error
        task.retry_count += 1
        if task.can_retry():
            task.status = TaskStatus.RETRYING
            self._queue.appendleft(task)   # retry immediately next
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            self._failed.append(task)

    def mark_skipped(self, task: Task) -> None:
        task.status = TaskStatus.SKIPPED
        task.completed_at = time.time()
        self._completed.append(task)

    def requeue(self, task: Task) -> None:
        task.status = TaskStatus.PENDING
        self._queue.append(task)

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    @property
    def done_count(self) -> int:
        return len(self._completed)

    @property
    def failed_count(self) -> int:
        return len(self._failed)

    @property
    def total_count(self) -> int:
        return self.pending_count + self.done_count + self.failed_count

    @property
    def success_rate(self) -> float:
        total = self.done_count + self.failed_count
        return (self.done_count / total * 100) if total else 0.0

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def get_summary(self) -> dict:
        return {
            "pending": self.pending_count,
            "done": self.done_count,
            "failed": self.failed_count,
            "success_rate": round(self.success_rate, 1),
        }
