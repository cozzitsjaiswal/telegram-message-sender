"""
gui/autopilot_tab.py — Command center for the fully autonomous 24/7 engine.

Displays:
  • Phase pipeline with live indicators
  • Real-time stats (cycles, discovered, joined, promoted)
  • Health score gauge
  • Account health matrix
  • Live event log
  • Full configuration panel
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPlainTextEdit, QProgressBar,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.group_manager import GroupManager
from core.message_engine import MessageEngine
from core.autopilot import AutoPilot

logger = logging.getLogger(__name__)


# ─── Phase badge helper ───────────────────────────────────────────────
_PHASE_COLORS = {
    "🔍 Discovering": "#5ab4f0",
    "➕ Joining":     "#d0a020",
    "📨 Promoting":   "#40d060",
    "📡 Forwarding":  "#c080f0",
    "📊 Analyzing":   "#f08040",
    "😴 Resting":     "#606090",
    "⏸ Paused":      "#d0a020",
    "❌ Error":       "#e05050",
    "Idle":           "#404060",
}


class AutoPilotTab(QWidget):
    _sig_event = pyqtSignal(str, str)
    _sig_phase = pyqtSignal(str)
    _sig_stats = pyqtSignal(dict)

    def __init__(
        self,
        account_manager: AccountManager,
        group_manager: GroupManager,
        message_engine: MessageEngine,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._accounts = account_manager
        self._groups = group_manager
        self._messages = message_engine
        self._pilot: Optional[AutoPilot] = None
        self._pilot_task: Optional[asyncio.Task] = None

        self._setup_ui()
        self._connect_signals()

        # Periodic stats refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_health)
        self._timer.start(5000)   # every 5s

    def _connect_signals(self):
        self._sig_event.connect(self._on_event)
        self._sig_phase.connect(self._on_phase)
        self._sig_stats.connect(self._on_stats)

    # ------------------------------------------------------------------
    # UI Build
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("⚡ AUTOPILOT")
        title.setStyleSheet(
            "font-size:22px; font-weight:900; letter-spacing:2px; color:#e05030;"
        )
        hdr.addWidget(title)

        self._phase_badge = QLabel("● Idle")
        self._phase_badge.setStyleSheet(
            "font-size:14px; font-weight:700; color:#404060; "
            "background:#0d0d1e; padding:6px 16px; border-radius:12px; "
            "border:1px solid #252545;"
        )
        hdr.addWidget(self._phase_badge)
        hdr.addStretch()

        self._uptime_label = QLabel("Uptime: 0h 0m")
        self._uptime_label.setStyleSheet("color:#505090; font-size:12px;")
        hdr.addWidget(self._uptime_label)
        root.addLayout(hdr)

        sub = QLabel(
            "Fully autonomous 24/7 engine — Discover → Join → Promote → Analyze → Rest → Repeat. "
            "Self-healing: auto-reconnects accounts, adapts to rate limits, exponential backoff on failures."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#4a5080; font-size:11px;")
        root.addWidget(sub)

        # ── Phase Pipeline ────────────────────────────────────────────
        pipe_box = QGroupBox("Phase Pipeline")
        pipe_lay = QHBoxLayout(pipe_box)
        self._phase_labels = {}
        phases = ["🔍 Discover", "➕ Join", "📨 Promote", "📊 Analyze", "😴 Rest"]
        for i, name in enumerate(phases):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "background:#0d0d1e; color:#404060; font-weight:700; font-size:12px; "
                "padding:8px 4px; border-radius:6px; border:1px solid #1e1e38;"
            )
            lbl.setMinimumWidth(100)
            pipe_lay.addWidget(lbl)
            self._phase_labels[name.split(" ", 1)[-1]] = lbl
            if i < len(phases) - 1:
                arrow = QLabel("→")
                arrow.setAlignment(Qt.AlignCenter)
                arrow.setStyleSheet("color:#303050; font-size:16px; font-weight:900;")
                arrow.setFixedWidth(24)
                pipe_lay.addWidget(arrow)
        root.addWidget(pipe_box)

        # ── Stats + Health side-by-side ───────────────────────────────
        mid = QHBoxLayout()

        # Stats grid
        stats_box = QGroupBox("📊 Lifetime Stats")
        sg = QGridLayout(stats_box)
        self._stat_labels = {}
        stat_items = [
            ("Cycles", "cycles_completed"),
            ("Discovered", "total_discovered"),
            ("Joined", "total_joined"),
            ("Promoted", "total_promoted"),
            ("Errors", "total_errors"),
            ("Uptime (h)", "total_uptime_hours"),
        ]
        for i, (display, key) in enumerate(stat_items):
            val = QLabel("0")
            val.setStyleSheet("font-size:20px; font-weight:900; color:#d0a020;")
            val.setAlignment(Qt.AlignCenter)
            lbl = QLabel(display)
            lbl.setStyleSheet("color:#404070; font-size:10px;")
            lbl.setAlignment(Qt.AlignCenter)
            sg.addWidget(val, 0, i)
            sg.addWidget(lbl, 1, i)
            self._stat_labels[key] = val
        mid.addWidget(stats_box, 3)

        # Health gauge
        health_box = QGroupBox("🛡️ System Health")
        hlay = QVBoxLayout(health_box)
        self._health_bar = QProgressBar()
        self._health_bar.setRange(0, 100)
        self._health_bar.setValue(0)
        self._health_bar.setFixedHeight(24)
        self._health_bar.setFormat("Health: %v%")
        self._health_bar.setStyleSheet("""
            QProgressBar { background:#0c0c1e; border:1px solid #1e1e38; border-radius:6px; color:#d0a020; font-weight:700; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #40d060,stop:1 #20a040); border-radius:6px; }
        """)
        hlay.addWidget(self._health_bar)

        self._health_detail = QLabel("Accounts: 0/0 online | Reconnects: 0")
        self._health_detail.setStyleSheet("color:#505090; font-size:11px;")
        hlay.addWidget(self._health_detail)

        # Account health mini-table
        self._acc_table = QTableWidget(0, 3)
        self._acc_table.setHorizontalHeaderLabels(["Phone", "Status", "Health"])
        self._acc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._acc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._acc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._acc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._acc_table.setAlternatingRowColors(True)
        self._acc_table.verticalHeader().setVisible(False)
        self._acc_table.setMaximumHeight(130)
        hlay.addWidget(self._acc_table)

        mid.addWidget(health_box, 2)
        root.addLayout(mid)

        # ── Controls ──────────────────────────────────────────────────
        ctrl_box = QGroupBox("🎮 Controls")
        ctrl_lay = QHBoxLayout(ctrl_box)

        self._btn_engage = QPushButton("🚀  ENGAGE AUTOPILOT")
        self._btn_engage.setObjectName("btn_start")
        self._btn_engage.setMinimumHeight(44)
        self._btn_engage.setStyleSheet(
            "font-size:15px; font-weight:900; letter-spacing:1px;"
        )
        self._btn_engage.clicked.connect(self._on_engage)
        ctrl_lay.addWidget(self._btn_engage)

        self._btn_pause = QPushButton("⏸  Pause")
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause)
        ctrl_lay.addWidget(self._btn_pause)

        self._btn_resume = QPushButton("▶  Resume")
        self._btn_resume.setEnabled(False)
        self._btn_resume.clicked.connect(self._on_resume)
        ctrl_lay.addWidget(self._btn_resume)

        self._btn_stop = QPushButton("■  DISENGAGE")
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setMinimumHeight(44)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        ctrl_lay.addWidget(self._btn_stop)

        root.addWidget(ctrl_box)

        # ── Configuration ─────────────────────────────────────────────
        cfg_box = QGroupBox("⚙️ Configuration (set before engaging)")
        cfg_lay = QGridLayout(cfg_box)

        cfg_lay.addWidget(QLabel("Keywords:"), 0, 0)
        self._kw_edit = QTextEdit()
        self._kw_edit.setPlaceholderText("crypto, forex, usdt, trading, bank account india...")
        self._kw_edit.setMaximumHeight(50)
        self._kw_edit.setStyleSheet(
            "background:#0c0c1e; color:#c8c8f0; border:1px solid #222240; border-radius:5px; padding:4px;"
        )
        cfg_lay.addWidget(self._kw_edit, 0, 1, 1, 5)

        cfg_lay.addWidget(QLabel("Discovery limit:"), 1, 0)
        self._cfg_disc = QSpinBox()
        self._cfg_disc.setRange(10, 200)
        self._cfg_disc.setValue(50)
        cfg_lay.addWidget(self._cfg_disc, 1, 1)

        cfg_lay.addWidget(QLabel("Join delay (s):"), 1, 2)
        self._cfg_jdelay = QSpinBox()
        self._cfg_jdelay.setRange(3, 60)
        self._cfg_jdelay.setValue(6)
        cfg_lay.addWidget(self._cfg_jdelay, 1, 3)

        cfg_lay.addWidget(QLabel("Max promote/cycle:"), 1, 4)
        self._cfg_promo = QSpinBox()
        self._cfg_promo.setRange(5, 200)
        self._cfg_promo.setValue(50)
        cfg_lay.addWidget(self._cfg_promo, 1, 5)

        cfg_lay.addWidget(QLabel("Send delay (s):"), 2, 0)
        self._cfg_smin = QSpinBox()
        self._cfg_smin.setRange(10, 300)
        self._cfg_smin.setValue(30)
        cfg_lay.addWidget(self._cfg_smin, 2, 1)
        cfg_lay.addWidget(QLabel("–"), 2, 2)
        self._cfg_smax = QSpinBox()
        self._cfg_smax.setRange(30, 600)
        self._cfg_smax.setValue(90)
        cfg_lay.addWidget(self._cfg_smax, 2, 3)

        cfg_lay.addWidget(QLabel("Rest (min):"), 2, 4)
        self._cfg_rest = QSpinBox()
        self._cfg_rest.setRange(1, 120)
        self._cfg_rest.setValue(5)
        cfg_lay.addWidget(self._cfg_rest, 2, 5)

        root.addWidget(cfg_box)

        # ── Live Event Log ────────────────────────────────────────────
        log_box = QGroupBox("📡 Live AutoPilot Feed")
        llay = QVBoxLayout(log_box)
        self._log_feed = QPlainTextEdit()
        self._log_feed.setReadOnly(True)
        self._log_feed.setMaximumHeight(180)
        self._log_feed.setStyleSheet(
            "background:#06060e; color:#5060a0; font-family:Consolas; font-size:11px; "
            "border:1px solid #141430; border-radius:6px;"
        )
        llay.addWidget(self._log_feed)
        root.addWidget(log_box)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_engage(self):
        # Parse keywords
        raw = self._kw_edit.toPlainText().strip()
        keywords = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
        if not keywords:
            self._on_event("ERROR", "❌ Enter at least one keyword")
            return

        active = self._accounts.get_active()
        if not active:
            # Try all accounts — health monitor will reconnect them
            all_accs = self._accounts.get_all()
            if not all_accs:
                self._on_event("ERROR", "❌ No accounts added — go to Accounts tab")
                return
            self._on_event("WARN", "⚠️ No accounts online — HealthMonitor will auto-reconnect")

        msgs = self._messages.get_all()
        if not msgs:
            self._on_event("WARN", "⚠️ No message templates — promote phase will skip")

        # Create AutoPilot
        self._pilot = AutoPilot(
            self._accounts,
            self._groups,
            self._messages,
            on_event=lambda lvl, msg: self._sig_event.emit(lvl, msg),
            on_phase=lambda p: self._sig_phase.emit(p),
            on_stats=lambda s: self._sig_stats.emit(s),
        )

        self._pilot.configure(
            keywords=keywords,
            discovery_limit=self._cfg_disc.value(),
            join_delay=self._cfg_jdelay.value(),
            send_delay_min=self._cfg_smin.value(),
            send_delay_max=self._cfg_smax.value(),
            rest_min=self._cfg_rest.value() * 60,
            rest_max=self._cfg_rest.value() * 60 * 3,
            max_promote_per_cycle=self._cfg_promo.value(),
        )

        self._pilot_task = asyncio.ensure_future(self._pilot.run())

        self._btn_engage.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_pause.setEnabled(True)
        self._kw_edit.setReadOnly(True)

    def _on_pause(self):
        if self._pilot:
            self._pilot.pause()
        self._btn_pause.setEnabled(False)
        self._btn_resume.setEnabled(True)

    def _on_resume(self):
        if self._pilot:
            self._pilot.resume()
        self._btn_pause.setEnabled(True)
        self._btn_resume.setEnabled(False)

    def _on_stop(self):
        if self._pilot:
            self._pilot.stop()
        if self._pilot_task and not self._pilot_task.done():
            self._pilot_task.cancel()
        self._btn_engage.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_pause.setEnabled(False)
        self._btn_resume.setEnabled(False)
        self._kw_edit.setReadOnly(False)
        self._phase_badge.setText("● Idle")
        self._phase_badge.setStyleSheet(
            "font-size:14px; font-weight:700; color:#404060; "
            "background:#0d0d1e; padding:6px 16px; border-radius:12px; "
            "border:1px solid #252545;"
        )

    def shutdown(self):
        """Called when the app is closing."""
        if self._pilot:
            self._pilot.stop()
        if self._pilot_task and not self._pilot_task.done():
            self._pilot_task.cancel()

    # ------------------------------------------------------------------
    # Signal handlers (Qt main thread)
    # ------------------------------------------------------------------

    def _on_event(self, level: str, msg: str):
        colors = {
            "INFO": "#4060a0", "WARN": "#b07820",
            "ERROR": "#a03030", "SUCCESS": "#306030",
        }
        color = colors.get(level, "#506090")
        import time as _t
        ts = _t.strftime("%H:%M:%S")
        html = f'<span style="color:#222240;">[{ts}]</span> <span style="color:{color};">{msg}</span>'
        self._log_feed.appendHtml(html)
        sb = self._log_feed.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_phase(self, phase: str):
        color = _PHASE_COLORS.get(phase, "#404060")
        self._phase_badge.setText(f"● {phase}")
        self._phase_badge.setStyleSheet(
            f"font-size:14px; font-weight:700; color:{color}; "
            f"background:#0d0d1e; padding:6px 16px; border-radius:12px; "
            f"border:1px solid {color}40;"
        )

        # Highlight active pipeline step
        phase_map = {
            "🔍 Discovering": "Discover",
            "➕ Joining": "Join",
            "📨 Promoting": "Promote",
            "📊 Analyzing": "Analyze",
            "😴 Resting": "Rest",
        }
        active_name = phase_map.get(phase, "")
        for name, lbl in self._phase_labels.items():
            if name == active_name:
                p_color = _PHASE_COLORS.get(phase, "#5ab4f0")
                lbl.setStyleSheet(
                    f"background:{p_color}30; color:{p_color}; font-weight:800; font-size:12px; "
                    f"padding:8px 4px; border-radius:6px; border:2px solid {p_color};"
                )
            else:
                lbl.setStyleSheet(
                    "background:#0d0d1e; color:#404060; font-weight:700; font-size:12px; "
                    "padding:8px 4px; border-radius:6px; border:1px solid #1e1e38;"
                )

        QApplication.processEvents()

    def _on_stats(self, stats: dict):
        for key, label in self._stat_labels.items():
            val = stats.get(key, 0)
            if isinstance(val, float):
                label.setText(f"{val:.1f}")
            else:
                label.setText(str(val))

        # Uptime
        hours = stats.get("total_uptime_hours", 0)
        h = int(hours)
        m = int((hours - h) * 60)
        self._uptime_label.setText(f"Uptime: {h}h {m}m | Cycles: {stats.get('cycles_completed', 0)}")

        QApplication.processEvents()

    def _refresh_health(self):
        """Periodic health table + gauge refresh."""
        if not self._pilot:
            return

        status = self._pilot.get_full_status()

        # Health bar
        score = status.get("health_score", 0)
        self._health_bar.setValue(score)
        if score >= 80:
            chunk_color = "#40d060"
        elif score >= 50:
            chunk_color = "#d0a020"
        else:
            chunk_color = "#e05050"
        self._health_bar.setStyleSheet(f"""
            QProgressBar {{ background:#0c0c1e; border:1px solid #1e1e38; border-radius:6px; color:#d0a020; font-weight:700; }}
            QProgressBar::chunk {{ background: {chunk_color}; border-radius:6px; }}
        """)

        self._health_detail.setText(
            f"Accounts: {status.get('accounts_online', 0)}/{status.get('accounts_total', 0)} online | "
            f"Flooded: {status.get('accounts_flooded', 0)}"
        )

        # Mini account table
        all_acc = self._accounts.get_all()
        self._acc_table.setRowCount(len(all_acc))
        for row, acc in enumerate(all_acc):
            self._acc_table.setItem(row, 0, QTableWidgetItem(acc.get("phone")))

            if acc.get('engine'):
                s_text = "✅ Online"
                s_color = "#40d060"
            elif acc.status.value == "flood":
                s_text = f"⏳ Flood ({acc.flood_remaining}s)"
                s_color = "#d0a020"
            elif acc.status.value == "banned":
                s_text = "🚫 Banned"
                s_color = "#e05050"
            else:
                s_text = "❌ Offline"
                s_color = "#606080"

            si = QTableWidgetItem(s_text)
            si.setForeground(QColor(s_color))
            self._acc_table.setItem(row, 1, si)

            health = "●●●" if acc.get('engine') else "●○○"
            hi = QTableWidgetItem(health)
            hi.setForeground(QColor(s_color))
            self._acc_table.setItem(row, 2, hi)
            self._acc_table.setRowHeight(row, 28)

    def on_accounts_changed(self):
        self._refresh_health()
