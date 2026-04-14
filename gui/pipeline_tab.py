"""
gui/pipeline_tab.py — Furaya v5.5
The Autonomous Pipeline Control Center.

Shows the 3-phase flow: DISCOVER → JOIN → PROMOTE
with live stats, phase indicators, and a single START button.
"""

from __future__ import annotations
import asyncio
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QGridLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QGroupBox, QSizePolicy,
)
from PyQt5.QtGui import QColor, QPalette


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("border: none; border-top: 1px solid rgba(0,212,255,0.08);")
    return f


class PhaseIndicator(QWidget):
    """Visual pill showing a pipeline phase with status."""

    def __init__(self, number: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(14)

        self._num = QLabel(number)
        self._num.setFixedSize(36, 36)
        self._num.setAlignment(Qt.AlignCenter)
        self._num.setStyleSheet("""
            background: rgba(0,212,255,0.08);
            color: #00d4ff;
            border: 1px solid rgba(0,212,255,0.25);
            border-radius: 18px;
            font-size: 14px;
            font-weight: 800;
        """)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(1)
        self._title = QLabel(title)
        self._title.setStyleSheet("color: #c8d8e8; font-weight: 700; font-size: 13px;")
        self._desc = QLabel(desc)
        self._desc.setStyleSheet("color: #405060; font-size: 11px;")
        text_lay.addWidget(self._title)
        text_lay.addWidget(self._desc)

        self._status = QLabel("WAITING")
        self._status.setFixedWidth(80)
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("""
            color: #304050;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 0;
        """)

        lay.addWidget(self._num)
        lay.addLayout(text_lay, 1)
        lay.addWidget(self._status)

        self.setStyleSheet("""
            background: rgba(0,20,40,0.4);
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 8px;
        """)

    def set_active(self):
        self._num.setStyleSheet("""
            background: rgba(0,212,255,0.20);
            color: #ffffff;
            border: 1px solid #00d4ff;
            border-radius: 18px;
            font-size: 14px;
            font-weight: 800;
        """)
        self._status.setText("RUNNING")
        self._status.setStyleSheet("""
            color: #00ff88;
            background: rgba(0,255,136,0.10);
            border: 1px solid rgba(0,255,136,0.30);
            border-radius: 10px;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 0;
        """)
        self.setStyleSheet("""
            background: rgba(0,212,255,0.06);
            border: 1px solid rgba(0,212,255,0.20);
            border-radius: 8px;
        """)

    def set_done(self, count: int = 0):
        self._num.setStyleSheet("""
            background: rgba(0,255,136,0.15);
            color: #00ff88;
            border: 1px solid rgba(0,255,136,0.40);
            border-radius: 18px;
            font-size: 14px;
            font-weight: 800;
        """)
        self._status.setText(f"DONE ({count})" if count else "DONE")
        self._status.setStyleSheet("""
            color: #00ff88;
            background: rgba(0,255,136,0.08);
            border: 1px solid rgba(0,255,136,0.20);
            border-radius: 10px;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 0;
        """)
        self.setStyleSheet("""
            background: rgba(0,255,136,0.03);
            border: 1px solid rgba(0,255,136,0.10);
            border-radius: 8px;
        """)

    def reset(self):
        self._num.setStyleSheet("""
            background: rgba(0,212,255,0.08);
            color: #00d4ff;
            border: 1px solid rgba(0,212,255,0.25);
            border-radius: 18px;
            font-size: 14px;
            font-weight: 800;
        """)
        self._status.setText("WAITING")
        self._status.setStyleSheet("""
            color: #304050;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 0;
        """)
        self.setStyleSheet("""
            background: rgba(0,20,40,0.4);
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 8px;
        """)


class KpiCard(QWidget):
    """A single KPI metric card."""

    def __init__(self, label: str, value: str = "0", color: str = "#00d4ff", parent=None):
        super().__init__(parent)
        self._color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        self._val = QLabel(value)
        self._val.setAlignment(Qt.AlignCenter)
        self._val.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 800;")

        self._lbl = QLabel(label)
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setStyleSheet("color: #304050; font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;")

        lay.addWidget(self._val)
        lay.addWidget(self._lbl)

        self.setStyleSheet(f"""
            background: rgba(0,20,40,0.6);
            border: 1px solid rgba(0,212,255,0.10);
            border-top: 3px solid {color};
            border-radius: 8px;
        """)

    def set_value(self, v):
        self._val.setText(str(v))


class PipelineTab(QWidget):
    """
    Main autonomous pipeline control center.
    Configure keywords + messages → click START → watch it run.
    """

    log_requested = pyqtSignal(str, str)

    def __init__(self, account_manager, pipeline, parent=None):
        super().__init__(parent)
        self._accounts = account_manager
        self._pipeline = pipeline
        self._running = False
        self._setup_ui()
        self._connect_pipeline()

        # Heartbeat to update KPIs
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_kpis)
        self._timer.start(1000)

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── LEFT: Config panel ────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)

        # Header
        hdr = QLabel("AUTONOMOUS PIPELINE")
        hdr.setStyleSheet("color: #00d4ff; font-size: 18px; font-weight: 800; letter-spacing: 3px;")
        sub = QLabel("Configure → Start → Watch it run automatically")
        sub.setStyleSheet("color: #405060; font-size: 11px;")
        left.addWidget(hdr)
        left.addWidget(sub)
        left.addWidget(_sep())

        # Phase indicators
        self._phase1 = PhaseIndicator("1", "DISCOVER GROUPS", "Search Telegram for keywords")
        self._phase2 = PhaseIndicator("2", "JOIN GROUPS", "Auto-join the best results")
        self._phase3 = PhaseIndicator("3", "SEND PROMOTIONS", "Rotate messages across groups")
        for ph in (self._phase1, self._phase2, self._phase3):
            left.addWidget(ph)

        left.addWidget(_sep())

        # ── Keywords ──────────────────────────────────────────
        kw_lbl = QLabel("KEYWORDS  (one per line)")
        kw_lbl.setStyleSheet("color: #00d4ff; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        left.addWidget(kw_lbl)

        self._keywords_edit = QTextEdit()
        self._keywords_edit.setPlaceholderText("crypto trading\nNFT community\ndefi group\n...")
        self._keywords_edit.setMaximumHeight(90)
        left.addWidget(self._keywords_edit)

        # ── Delay config ──────────────────────────────────────
        delay_lay = QHBoxLayout()
        delay_lay.setSpacing(8)

        min_lay = QVBoxLayout()
        min_lay.setSpacing(3)
        min_lbl = QLabel("MIN DELAY (s)")
        min_lbl.setStyleSheet("color: #405060; font-size: 10px;")
        self._min_delay = QDoubleSpinBox()
        self._min_delay.setRange(10, 600)
        self._min_delay.setValue(30)
        self._min_delay.setSuffix("s")
        min_lay.addWidget(min_lbl)
        min_lay.addWidget(self._min_delay)

        max_lay = QVBoxLayout()
        max_lay.setSpacing(3)
        max_lbl = QLabel("MAX DELAY (s)")
        max_lbl.setStyleSheet("color: #405060; font-size: 10px;")
        self._max_delay = QDoubleSpinBox()
        self._max_delay.setRange(20, 1200)
        self._max_delay.setValue(90)
        self._max_delay.setSuffix("s")
        max_lay.addWidget(max_lbl)
        max_lay.addWidget(self._max_delay)

        grp_lay = QVBoxLayout()
        grp_lay.setSpacing(3)
        grp_lbl = QLabel("MAX GROUPS")
        grp_lbl.setStyleSheet("color: #405060; font-size: 10px;")
        self._max_groups = QSpinBox()
        self._max_groups.setRange(1, 100)
        self._max_groups.setValue(20)
        grp_lay.addWidget(grp_lbl)
        grp_lay.addWidget(self._max_groups)

        delay_lay.addLayout(min_lay)
        delay_lay.addLayout(max_lay)
        delay_lay.addLayout(grp_lay)
        left.addLayout(delay_lay)

        # ── Control buttons ───────────────────────────────────
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(8)

        self._btn_start = QPushButton("▶  START PIPELINE")
        self._btn_start.setObjectName("btn_primary")
        self._btn_start.setMinimumHeight(42)
        self._btn_start.clicked.connect(self._toggle)

        self._btn_stop = QPushButton("■  STOP")
        self._btn_stop.setObjectName("btn_danger")
        self._btn_stop.setMinimumHeight(42)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)

        btn_lay.addWidget(self._btn_start, 2)
        btn_lay.addWidget(self._btn_stop, 1)
        left.addLayout(btn_lay)
        left.addStretch()

        # ── RIGHT: Stats + Logs ───────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(12)

        # Account status bar
        self._acct_bar = QLabel("● 0 accounts connected")
        self._acct_bar.setStyleSheet("""
            background: rgba(0,20,40,0.5);
            border: 1px solid rgba(0,212,255,0.10);
            border-radius: 6px;
            color: #305050;
            padding: 8px 14px;
            font-size: 11px;
        """)
        right.addWidget(self._acct_bar)

        # KPI cards
        kpi_lay = QGridLayout()
        kpi_lay.setSpacing(8)
        self._kpi_found = KpiCard("FOUND", "0", "#00d4ff")
        self._kpi_joined = KpiCard("JOINED", "0", "#ffd700")
        self._kpi_sent = KpiCard("SENT", "0", "#00ff88")
        self._kpi_flood = KpiCard("FLOOD WAITS", "0", "#ff6644")

        kpi_lay.addWidget(self._kpi_found, 0, 0)
        kpi_lay.addWidget(self._kpi_joined, 0, 1)
        kpi_lay.addWidget(self._kpi_sent, 1, 0)
        kpi_lay.addWidget(self._kpi_flood, 1, 1)
        right.addLayout(kpi_lay)

        # ── Promo messages ────────────────────────────────────
        msg_lbl = QLabel("PROMO MESSAGES  (one per line)")
        msg_lbl.setStyleSheet("color: #00d4ff; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        right.addWidget(msg_lbl)

        self._messages_edit = QTextEdit()
        self._messages_edit.setPlaceholderText(
            "🚀 Join our crypto signals community! t.me/example\n\n"
            "💎 Best NFT drops — get in early! t.me/example2"
        )
        self._messages_edit.setMaximumHeight(110)
        right.addWidget(self._messages_edit)

        # Live log
        log_lbl = QLabel("PIPELINE LOG")
        log_lbl.setStyleSheet("color: #00d4ff; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        right.addWidget(log_lbl)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setStyleSheet("""
            background: rgba(0,8,16,0.9);
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 6px;
            font-family: 'Consolas', monospace;
            font-size: 11px;
            color: #507090;
        """)
        right.addWidget(self._log_view, 1)

        # Assemble
        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(340)

        right_w = QWidget()
        right_w.setLayout(right)

        root.addWidget(left_w)
        root.addWidget(right_w, 1)

    def _connect_pipeline(self):
        self._pipeline.log_cb = self._on_pipeline_log
        self._pipeline.metrics_cb = self._on_metrics
        self._pipeline.status_cb = self._on_status

    # ── Controls ───────────────────────────────────────────────────────

    def _toggle(self):
        if self._running:
            return
        self._start()

    def _start(self):
        keywords = [k.strip() for k in self._keywords_edit.toPlainText().splitlines() if k.strip()]
        messages = [m.strip() for m in self._messages_edit.toPlainText().split("\n\n") if m.strip()]

        if not keywords:
            self._append_log("ERROR", "Enter at least one keyword")
            return
        if not messages:
            self._append_log("ERROR", "Enter at least one promo message")
            return

        active = self._accounts.get_active_engines()
        if not active:
            self._append_log("ERROR", "❌ No accounts connected — go to Accounts tab and login first")
            return

        self._pipeline.configure(
            keywords=keywords,
            messages=messages,
            min_delay=self._min_delay.value(),
            max_delay=self._max_delay.value(),
            max_groups=self._max_groups.value(),
        )

        self._running = True
        self._btn_start.setEnabled(False)
        self._btn_start.setText("⏳  RUNNING...")
        self._btn_stop.setEnabled(True)

        # Reset phase indicators
        self._phase1.reset()
        self._phase2.reset()
        self._phase3.reset()

        self._log_view.clear()
        self._pipeline.start()

    def _stop(self):
        self._pipeline.stop()
        self._running = False
        self._btn_start.setEnabled(True)
        self._btn_start.setText("▶  START PIPELINE")
        self._btn_stop.setEnabled(False)

    # ── Callbacks from pipeline ────────────────────────────────────────

    def _on_pipeline_log(self, level: str, msg: str):
        self._append_log(level, msg)
        self.log_requested.emit(level, msg)

    def _on_metrics(self, metrics: dict):
        self._kpi_found.set_value(metrics.get("discovered", 0))
        self._kpi_joined.set_value(metrics.get("joined", 0))
        self._kpi_sent.set_value(metrics.get("sent", 0))
        self._kpi_flood.set_value(metrics.get("flood_waits", 0))

        if metrics.get("sent", 0) > 0 and not self._running:
            self._btn_start.setText("▶  START PIPELINE")
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)

    def _on_status(self, phase: str):
        phase_lower = phase.lower()
        if "discover" in phase_lower:
            self._phase1.set_active()
        elif "join" in phase_lower:
            self._phase1.set_done()
            self._phase2.set_active()
        elif "promot" in phase_lower or "send" in phase_lower:
            self._phase2.set_done()
            self._phase3.set_active()
        elif "done" in phase_lower:
            self._phase3.set_done(self._pipeline._stats.get("sent", 0))
            self._running = False
            self._btn_start.setEnabled(True)
            self._btn_start.setText("▶  START PIPELINE")
            self._btn_stop.setEnabled(False)
        elif "error" in phase_lower or "idle" in phase_lower:
            self._running = False
            self._btn_start.setEnabled(True)
            self._btn_start.setText("▶  START PIPELINE")
            self._btn_stop.setEnabled(False)

    def _append_log(self, level: str, msg: str):
        from datetime import datetime
        colors = {
            "INFO": "#507090",
            "WARN": "#a07820",
            "ERROR": "#a03040",
            "SUCCESS": "#207050",
        }
        c = colors.get(level.upper(), "#507090")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_view.append(
            f'<span style="color:#1a3a5a">[{ts}]</span> '
            f'<span style="color:{c}">{msg}</span>'
        )
        # Auto-scroll
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _update_kpis(self):
        n_connected = self._accounts.logged_in_count
        n_total = self._accounts.total_count
        if n_connected > 0:
            self._acct_bar.setText(f"● {n_connected}/{n_total} accounts connected")
            self._acct_bar.setStyleSheet("""
                background: rgba(0,255,136,0.04);
                border: 1px solid rgba(0,255,136,0.15);
                border-radius: 6px;
                color: #00ff88;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 700;
            """)
        else:
            self._acct_bar.setText(f"● No accounts connected — add accounts first")
            self._acct_bar.setStyleSheet("""
                background: rgba(255,50,80,0.04);
                border: 1px solid rgba(255,50,80,0.15);
                border-radius: 6px;
                color: #703040;
                padding: 8px 14px;
                font-size: 11px;
            """)
