"""Campaign Tab — start/stop/pause controller with mode + batch config."""
from __future__ import annotations

import asyncio
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout, QWidget,
)

from core.campaign_controller import CampaignController, CampaignState

logger = logging.getLogger(__name__)


class CampaignTab(QWidget):
    log_requested   = pyqtSignal(str, str)
    metrics_updated = pyqtSignal(dict)
    state_changed   = pyqtSignal(str)

    def __init__(self, controller: CampaignController, parent=None):
        super().__init__(parent)
        self._ctrl = controller
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("Campaign Control")
        title.setObjectName("label_title")
        layout.addWidget(title)

        # ── Mode config ──────────────────────────────────────────────
        cfg_box = QGroupBox("⚙️  Configuration")
        form = QFormLayout(cfg_box)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Safe", "Normal", "Aggressive"])
        self._mode_combo.setCurrentText("Normal")
        form.addRow("Campaign Mode:", self._mode_combo)

        mode_desc = QLabel(
            "<small>"
            "<b>Safe</b>: 3 tasks/wave | 45-90s delays | Very stable<br>"
            "<b>Normal</b>: 8 tasks/wave | 20-45s delays | Balanced<br>"
            "<b>Aggressive</b>: 20 tasks/wave | 8-20s delays | Fast, higher risk"
            "</small>"
        )
        mode_desc.setTextFormat(__import__("PyQt5.QtCore", fromlist=["Qt"]).Qt.RichText)
        mode_desc.setWordWrap(True)
        form.addRow("", mode_desc)
        layout.addWidget(cfg_box)

        # ── Controls ────────────────────────────────────────────────
        ctrl_box = QGroupBox("🎮  Controls")
        ctrl_lay = QVBoxLayout(ctrl_box)

        btn_row1 = QHBoxLayout()
        self._btn_start = QPushButton("▶  START CAMPAIGN")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setMinimumHeight(48)
        self._btn_start.clicked.connect(self._on_start)
        btn_row1.addWidget(self._btn_start)

        self._btn_stop = QPushButton("■  STOP")
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setMinimumHeight(48)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row1.addWidget(self._btn_stop)
        ctrl_lay.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self._btn_pause = QPushButton("⏸  Pause")
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause)
        btn_row2.addWidget(self._btn_pause)

        self._btn_resume = QPushButton("▶  Resume")
        self._btn_resume.setEnabled(False)
        self._btn_resume.clicked.connect(self._on_resume)
        btn_row2.addWidget(self._btn_resume)
        ctrl_lay.addLayout(btn_row2)

        layout.addWidget(ctrl_box)

        # ── State display ───────────────────────────────────────────
        self._state_label = QLabel("State: Idle")
        self._state_label.setObjectName("badge_stopped")
        self._state_label.setStyleSheet("font-size:15px; font-weight:800; padding:8px; color:#505090;")
        layout.addWidget(self._state_label)

        # ── Quick stats ─────────────────────────────────────────────
        stats_box = QGroupBox("📊  Quick Stats")
        stats_row = QHBoxLayout(stats_box)
        self._stat_labels = {}
        for k in ["Done", "Failed", "Pending", "Wave", "Success Rate"]:
            col = QVBoxLayout()
            val = QLabel("—")
            val.setStyleSheet("font-size:20px; font-weight:800; color:#d0a020; text-align:center;")
            lbl = QLabel(k)
            lbl.setStyleSheet("color:#404070; font-size:10px; text-align:center;")
            col.addWidget(val)
            col.addWidget(lbl)
            stats_row.addLayout(col)
            self._stat_labels[k] = val
        layout.addWidget(stats_box)

        layout.addStretch()

    def _on_start(self):
        mode = self._mode_combo.currentText()
        asyncio.ensure_future(self._ctrl.start(mode))
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_pause.setEnabled(True)

    def _on_stop(self):
        self._ctrl.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_pause.setEnabled(False)
        self._btn_resume.setEnabled(False)

    def _on_pause(self):
        self._ctrl.pause()
        self._btn_pause.setEnabled(False)
        self._btn_resume.setEnabled(True)

    def _on_resume(self):
        self._ctrl.resume()
        self._btn_pause.setEnabled(True)
        self._btn_resume.setEnabled(False)

    def on_metrics(self, m: dict):
        self._stat_labels["Done"].setText(str(m.get("done", "—")))
        self._stat_labels["Failed"].setText(str(m.get("failed", "—")))
        self._stat_labels["Pending"].setText(str(m.get("pending", "—")))
        self._stat_labels["Wave"].setText(str(m.get("wave", "—")))
        self._stat_labels["Success Rate"].setText(f"{m.get('success_rate', 0)}%")

    def on_state_changed(self, state: str):
        state_colors = {
            "Running": "#40d060", "Paused": "#d0a020",
            "Stopped": "#606080", "Error": "#e05050",
            "Initializing": "#5ab4f0",
        }
        color = state_colors.get(state, "#606080")
        self._state_label.setText(f"State:  {state}")
        self._state_label.setStyleSheet(f"font-size:15px; font-weight:800; padding:8px; color:{color};")

        if state in ("Stopped", "Error"):
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)
            self._btn_pause.setEnabled(False)
            self._btn_resume.setEnabled(False)
