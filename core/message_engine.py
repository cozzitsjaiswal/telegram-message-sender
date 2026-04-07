"""MessageEngine — stores templates, rotates, adds micro-variations."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

DATA_FILE = Path("data/messages.json")

# Small sets of decorative elements for variation
_EMOJIS = ["🔥", "💥", "⚡", "✅", "🚀", "💎", "🎯", "💯", "👉", "🌟"]
_SPACERS = ["", " ", "\n"]


@dataclass
class MessageTemplate:
    id: int
    text: str
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @property
    def performance_score(self) -> float:
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total else 50.0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "MessageTemplate":
        return MessageTemplate(
            id=d.get("id", 0),
            text=d.get("text", ""),
            usage_count=d.get("usage_count", 0),
            success_count=d.get("success_count", 0),
            failure_count=d.get("failure_count", 0),
        )


class MessageEngine:
    def __init__(self) -> None:
        self._templates: List[MessageTemplate] = []
        self._last_index: int = -1
        self.load()

    def load(self) -> None:
        if DATA_FILE.exists():
            try:
                raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    self._templates = [MessageTemplate.from_dict(d) for d in raw]
            except Exception:
                pass

    def save(self) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(
            json.dumps([t.to_dict() for t in self._templates], indent=2),
            encoding="utf-8",
        )

    def add(self, text: str) -> MessageTemplate:
        new_id = max((t.id for t in self._templates), default=0) + 1
        tmpl = MessageTemplate(id=new_id, text=text)
        self._templates.append(tmpl)
        self.save()
        return tmpl

    def remove(self, template_id: int) -> bool:
        before = len(self._templates)
        self._templates = [t for t in self._templates if t.id != template_id]
        if len(self._templates) < before:
            self.save()
            return True
        return False

    def update(self, template_id: int, new_text: str) -> bool:
        for t in self._templates:
            if t.id == template_id:
                t.text = new_text
                self.save()
                return True
        return False

    def get_all(self) -> List[MessageTemplate]:
        return list(self._templates)

    def next_message(self, apply_variation: bool = True) -> Optional[str]:
        """Return next message in rotation — never repeats consecutively."""
        if not self._templates:
            return None
        # choose index different from last
        available = [i for i in range(len(self._templates)) if i != self._last_index]
        if not available:
            available = list(range(len(self._templates)))
        idx = random.choice(available)
        self._last_index = idx
        tmpl = self._templates[idx]
        tmpl.usage_count += 1
        text = tmpl.text
        if apply_variation:
            text = self._vary(text)
        return text

    def _vary(self, text: str) -> str:
        """Apply subtle micro-variation to avoid identical sends."""
        variation = random.randint(0, 2)
        if variation == 0:
            # Append a random emoji at end
            text = text.rstrip() + " " + random.choice(_EMOJIS)
        elif variation == 1:
            # Add a blank line at start or end
            text = random.choice(["", "\n"]) + text
        # variation == 2: no change
        return text

    def record_success(self, text: str) -> None:
        for t in self._templates:
            if t.text in text or text in t.text:
                t.success_count += 1
                self.save()
                break

    def record_failure(self, text: str) -> None:
        for t in self._templates:
            if t.text in text or text in t.text:
                t.failure_count += 1
                self.save()
                break

    def __len__(self) -> int:
        return len(self._templates)
