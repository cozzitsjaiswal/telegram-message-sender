"""AdaptiveEngine — dynamically adjusts delays and batch sizes."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class CampaignMode(str, Enum):
    SAFE       = "Safe"
    NORMAL     = "Normal"
    AGGRESSIVE = "Aggressive"


@dataclass
class ModeConfig:
    wave_size: int
    send_delay_min: float
    send_delay_max: float
    wave_pause_min: float
    wave_pause_max: float
    join_delay_min: float
    join_delay_max: float
    error_tolerance: float   # max error rate before slowing down


_BASE_CONFIGS = {
    CampaignMode.SAFE: ModeConfig(
        wave_size=3, send_delay_min=45, send_delay_max=90,
        wave_pause_min=120, wave_pause_max=180,
        join_delay_min=15, join_delay_max=25, error_tolerance=0.10,
    ),
    CampaignMode.NORMAL: ModeConfig(
        wave_size=8, send_delay_min=20, send_delay_max=45,
        wave_pause_min=60, wave_pause_max=120,
        join_delay_min=7, join_delay_max=15, error_tolerance=0.20,
    ),
    CampaignMode.AGGRESSIVE: ModeConfig(
        wave_size=20, send_delay_min=8, send_delay_max=20,
        wave_pause_min=20, wave_pause_max=40,
        join_delay_min=3, join_delay_max=7, error_tolerance=0.35,
    ),
}


class AdaptiveEngine:
    """Reads real-time error metrics and adjusts execution parameters."""

    def __init__(self, mode: CampaignMode = CampaignMode.NORMAL) -> None:
        self._mode = mode
        self._config = ModeConfig(**vars(_BASE_CONFIGS[mode]))
        self._recent_errors: list[float] = []
        self._recent_successes: list[float] = []
        self._window = 20   # look at last N results

    def set_mode(self, mode: CampaignMode) -> None:
        self._mode = mode
        self._config = ModeConfig(**vars(_BASE_CONFIGS[mode]))

    def record_success(self) -> None:
        now = time.time()
        self._recent_successes.append(now)
        self._trim(self._recent_successes)
        self._adapt()

    def record_failure(self) -> None:
        now = time.time()
        self._recent_errors.append(now)
        self._trim(self._recent_errors)
        self._adapt()

    def _trim(self, lst: list) -> None:
        while len(lst) > self._window:
            lst.pop(0)

    def _adapt(self) -> None:
        total = len(self._recent_errors) + len(self._recent_successes)
        if total < 5:
            return
        error_rate = len(self._recent_errors) / total
        base = _BASE_CONFIGS[self._mode]

        if error_rate > base.error_tolerance:
            # Slow down — scale delays up by 50%
            factor = 1.5
        elif error_rate < base.error_tolerance * 0.3:
            # Very stable — slightly speed up (max 20% faster than base)
            factor = 0.85
        else:
            factor = 1.0

        self._config.send_delay_min = max(5.0, base.send_delay_min * factor)
        self._config.send_delay_max = max(10.0, base.send_delay_max * factor)
        self._config.wave_size = max(1, int(base.wave_size / factor))

    @property
    def wave_size(self) -> int:
        return self._config.wave_size

    @property
    def send_delay_min(self) -> float:
        return self._config.send_delay_min

    @property
    def send_delay_max(self) -> float:
        return self._config.send_delay_max

    @property
    def wave_pause_min(self) -> float:
        return self._config.wave_pause_min

    @property
    def wave_pause_max(self) -> float:
        return self._config.wave_pause_max

    @property
    def join_delay_min(self) -> float:
        return self._config.join_delay_min

    @property
    def join_delay_max(self) -> float:
        return self._config.join_delay_max

    @property
    def current_error_rate(self) -> float:
        total = len(self._recent_errors) + len(self._recent_successes)
        return (len(self._recent_errors) / total) if total else 0.0

    def get_status(self) -> dict:
        return {
            "mode": self._mode.value,
            "wave_size": self.wave_size,
            "send_delay": f"{self.send_delay_min:.0f}–{self.send_delay_max:.0f}s",
            "wave_pause": f"{self.wave_pause_min:.0f}–{self.wave_pause_max:.0f}s",
            "error_rate": f"{self.current_error_rate*100:.1f}%",
        }
