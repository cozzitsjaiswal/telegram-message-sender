"""Engine tab — Keywords, promo post, mode, and the big START/STOP controls."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.forward_engine import ForwardEngine, EngineStats

logger = logging.getLogger(__name__)

DATA_DIR = Path("C:/FurayaPromoEngine/data")
PROMO_FILE = DATA_DIR / "promo_post.txt"


class EngineTab(QWidget):
    """Main control panel — keywords, promo, start/stop."""

    log_requested = pyqtSignal(str, str)      # level, message
    stats_updated = pyqtSignal(object)         # EngineStats

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._account = None
        self._engine: Optional[ForwardEngine] = None
        self._task: Optional[asyncio.Task] = None
        self._setup_ui()
        self._load_promo()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Campaign Engine")
        title.setObjectName("label_title")
        layout.addWidget(title)

        # ── Settings row ──────────────────────────────────────────────
        settings_row = QHBoxLayout()

        # Keywords
        kw_box = QGroupBox("🔍 Search Keywords  (one per line)")
        kw_layout = QVBoxLayout(kw_box)
        self._keywords_input = QPlainTextEdit()
        self._keywords_input.setPlaceholderText("crypto\nforex\ntrading\nmarketing")
        self._keywords_input.setMaximumHeight(130)
        kw_layout.addWidget(self._keywords_input)
        settings_row.addWidget(kw_box, 3)

        # Config panel
        cfg_box = QGroupBox("⚙️ Config")
        cfg_form = QFormLayout(cfg_box)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Safe", "Normal", "Aggressive"])
        self._mode_combo.setCurrentText("Normal")
        cfg_form.addRow("Mode:", self._mode_combo)

        self._max_groups_spin = QSpinBox()
        self._max_groups_spin.setRange(10, 500)
        self._max_groups_spin.setValue(100)
        cfg_form.addRow("Max Groups:", self._max_groups_spin)

        self._mode_hint = QLabel(
            "<small><b>Safe:</b> slow &amp; careful<br>"
            "<b>Normal:</b> balanced<br>"
            "<b>Aggressive:</b> fast, higher risk</small>"
        )
        self._mode_hint.setTextFormat(Qt.RichText)
        cfg_form.addRow("", self._mode_hint)

        settings_row.addWidget(cfg_box, 2)
        layout.addLayout(settings_row)

        # ── Promo post ────────────────────────────────────────────────
        promo_box = QGroupBox("📣 Promotion Post  (paste the message you want to forward)")
        promo_layout = QVBoxLayout(promo_box)
        self._promo_input = QPlainTextEdit()
        self._promo_input.setPlaceholderText(
            "Paste your promo message here...\n\n"
            "Supports text, emojis, URLs — anything you can send on Telegram."
        )
        self._promo_input.setMinimumHeight(120)
        promo_layout.addWidget(self._promo_input)
        layout.addWidget(promo_box)

        # ── Stats bar ────────────────────────────────────────────────
        stats_box = QGroupBox("📊 Live Stats")
        stats_row = QHBoxLayout(stats_box)

        def _stat(label: str, obj_name: str) -> QLabel:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #888; font-size: 10px;")
            val = QLabel("0")
            val.setObjectName(obj_name)
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet("font-size: 18px; font-weight: bold; color: #5ab4f0;")
            col.addWidget(val)
            col.addWidget(lbl)
            stats_row.addLayout(col)
            return val

        self._stat_found   = _stat("Groups Found",    "stat_found")
        self._stat_joined  = _stat("Joined",          "stat_joined")
        self._stat_sent    = _stat("Sent This Cycle", "stat_sent")
        self._stat_cycle   = _stat("Cycle #",         "stat_cycle")
        self._stat_state   = _stat("State",           "stat_state")
        self._stat_state.setStyleSheet("font-size: 14px; font-weight: bold; color: #40c080;")

        layout.addWidget(stats_box)

        # ── Start / Stop ──────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._btn_start = QPushButton("▶  START ENGINE")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setMinimumHeight(46)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("■  STOP")
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setMinimumHeight(46)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_stop)

        layout.addLayout(btn_row)

        self._account_status = QLabel("⚠️  No account connected — go to the Account tab first.")
        self._account_status.setStyleSheet("color: #f0a020; font-size: 11px;")
        layout.addWidget(self._account_status)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_promo(self) -> None:
        if PROMO_FILE.exists():
            try:
                self._promo_input.setPlainText(PROMO_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save_promo(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PROMO_FILE.write_text(self._promo_input.toPlainText(), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def set_account(self, account) -> None:
        self._account = account
        self._account_status.setText(f"✅  Account: {account.phone}")
        self._account_status.setStyleSheet("color: #40c080; font-size: 11px;")

    def clear_account(self) -> None:
        self._account = None
        self._account_status.setText("⚠️  No account connected — go to the Account tab first.")
        self._account_status.setStyleSheet("color: #f0a020; font-size: 11px;")

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if self._account is None or self._account.client is None:
            self._account_status.setText("❌  Not logged in. Go to Account tab and login first.")
            self._account_status.setStyleSheet("color: #e05050; font-size: 11px;")
            return

        keywords_raw = self._keywords_input.toPlainText().strip()
        keywords = [k.strip() for k in keywords_raw.splitlines() if k.strip()]
        if not keywords:
            self._account_status.setText("❌  Please enter at least one keyword.")
            self._account_status.setStyleSheet("color: #e05050; font-size: 11px;")
            return

        promo = self._promo_input.toPlainText().strip()
        if not promo:
            self._account_status.setText("❌  Please paste your promotion message.")
            self._account_status.setStyleSheet("color: #e05050; font-size: 11px;")
            return

        self._save_promo()

        mode = self._mode_combo.currentText()
        max_groups = self._max_groups_spin.value()

        self._engine = ForwardEngine(
            client=self._account.client,
            keywords=keywords,
            promo_text=promo,
            mode=mode,
            max_groups=max_groups,
            log_cb=lambda lvl, msg: self.log_requested.emit(lvl, msg),
            stats_cb=self._on_stats,
        )

        self._task = asyncio.ensure_future(self._engine.run())
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._stat_state.setText("🔍")
        self.log_requested.emit("INFO", f"Engine started — Mode: {mode} | Keywords: {', '.join(keywords)}")

    def _on_stop(self) -> None:
        if self._engine:
            self._engine.stop()
        if self._task:
            self._task.cancel()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._stat_state.setText("stopped")
        self.log_requested.emit("INFO", "Engine stop requested.")

    def _on_stats(self, stats: EngineStats) -> None:
        self._stat_found.setText(str(stats.groups_found))
        self._stat_joined.setText(str(stats.groups_joined))
        self._stat_sent.setText(str(stats.sent_this_cycle))
        self._stat_cycle.setText(str(stats.cycle_number))
        state_icons = {
            "searching": "🔍 Searching",
            "joining": "➕ Joining",
            "forwarding": "📣 Forwarding",
            "stopped": "■ Stopped",
            "error": "❌ Error",
            "idle": "● Idle",
        }
        self._stat_state.setText(state_icons.get(stats.state, stats.state))
        color = {
            "searching": "#5ab4f0",
            "joining":   "#f0a020",
            "forwarding":"#40c080",
            "stopped":   "#888",
            "error":     "#e05050",
        }.get(stats.state, "#5ab4f0")
        self._stat_state.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        self.stats_updated.emit(stats)
        if stats.state in ("stopped", "error"):
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)
