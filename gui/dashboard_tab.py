"""Dashboard Tab — live KPI cards, system health, event feed."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPlainTextEdit, QProgressBar, QVBoxLayout, QWidget,
)


def _kpi_card(label: str) -> tuple[QWidget, QLabel]:
    card = QWidget()
    card.setObjectName("kpi_card")
    lay = QVBoxLayout(card)
    lay.setSpacing(4)
    val_lbl = QLabel("—")
    val_lbl.setObjectName("kpi_value")
    val_lbl.setAlignment(Qt.AlignCenter)
    lbl = QLabel(label)
    lbl.setObjectName("kpi_label")
    lbl.setAlignment(Qt.AlignCenter)
    lay.addWidget(val_lbl)
    lay.addWidget(lbl)
    return card, val_lbl


class DashboardTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(14)

        title = QLabel("Dashboard")
        title.setObjectName("label_title")
        root.addWidget(title)

        # ── KPI Row ──────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        card1, self._kpi_state     = _kpi_card("State")
        card2, self._kpi_accounts  = _kpi_card("Active Accounts")
        card3, self._kpi_sent      = _kpi_card("Total Sent")
        card4, self._kpi_rate      = _kpi_card("Success Rate")
        card5, self._kpi_wave      = _kpi_card("Current Wave")
        card6, self._kpi_pending   = _kpi_card("Pending Tasks")
        for c in [card1, card2, card3, card4, card5, card6]:
            kpi_row.addWidget(c)
        root.addLayout(kpi_row)

        # ── Health bar ──────────────────────────────────────────────
        health_box = QGroupBox("System Health")
        hlay = QVBoxLayout(health_box)
        self._health_bar = QProgressBar()
        self._health_bar.setRange(0, 100)
        self._health_bar.setValue(100)
        self._health_bar.setFormat("Health: %p%")
        self._health_bar.setFixedHeight(22)
        hlay.addWidget(self._health_bar)

        # Adaptive row beneath health bar
        self._adaptive_label = QLabel("Mode: — | Wave size: — | Send delay: — | Error rate: —")
        self._adaptive_label.setStyleSheet("color: #505090; font-size: 11px;")
        hlay.addWidget(self._adaptive_label)
        root.addWidget(health_box)

        # ── Bottom row: event feed + progress ────────────────────────
        bottom = QHBoxLayout()

        feed_box = QGroupBox("📡  Live Event Feed")
        flay = QVBoxLayout(feed_box)
        self._event_feed = QPlainTextEdit()
        self._event_feed.setReadOnly(True)
        self._event_feed.setMaximumHeight(220)
        self._event_feed.setStyleSheet(
            "background:#07070d; color:#5060a0; font-family:Consolas,monospace; font-size:11px;"
        )
        flay.addWidget(self._event_feed)
        bottom.addWidget(feed_box, 2)

        stats_box = QGroupBox("📊  Queue Progress")
        slay = QVBoxLayout(stats_box)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("Completed: %p%")
        slay.addWidget(self._progress_bar)

        self._stats_grid = QGridLayout()
        pairs = [("Done", "—"), ("Failed", "—"), ("Mode", "—"), ("Wave Pause", "—")]
        self._stat_vals = {}
        for i, (lbl, default) in enumerate(pairs):
            ql = QLabel(lbl + ":")
            ql.setStyleSheet("color:#404070; font-size:11px;")
            qv = QLabel(default)
            qv.setStyleSheet("color:#a0a0d0; font-weight:600;")
            self._stats_grid.addWidget(ql, i, 0)
            self._stats_grid.addWidget(qv, i, 1)
            self._stat_vals[lbl] = qv
        slay.addLayout(self._stats_grid)
        slay.addStretch()
        bottom.addWidget(stats_box, 1)
        root.addLayout(bottom)

    # ------------------------------------------------------------------
    # Update slots
    # ------------------------------------------------------------------

    def on_metrics(self, m: dict) -> None:
        state = m.get("state", "—")
        colors = {
            "Running": "#40d060", "Paused": "#d0a020",
            "Stopped": "#808090", "Error": "#e05050",
        }
        color = colors.get(state, "#6070a8")
        self._kpi_state.setText(state)
        self._kpi_state.setStyleSheet(f"font-size:20px; font-weight:900; color:{color};")
        self._kpi_accounts.setText(str(m.get("active_accounts", "—")))
        self._kpi_sent.setText(str(m.get("total_sent", "—")))
        rate = m.get("success_rate", 0)
        self._kpi_rate.setText(f"{rate}%")
        self._kpi_rate.setStyleSheet(
            f"font-size:24px; font-weight:900; color:{'#40d060' if rate >= 70 else '#e05050'};"
        )
        self._kpi_wave.setText(str(m.get("wave", "—")))
        self._kpi_pending.setText(str(m.get("pending", "—")))

        done = m.get("done", 0)
        failed = m.get("failed", 0)
        total = done + failed + m.get("pending", 0)
        if total:
            self._progress_bar.setValue(int((done + failed) / total * 100))

        self._stat_vals["Done"].setText(str(done))
        self._stat_vals["Failed"].setText(str(failed))

        if adp := m.get("adaptive"):
            self._stat_vals["Mode"].setText(adp.get("mode", "—"))
            self._stat_vals["Wave Pause"].setText(adp.get("wave_pause", "—"))
            self._adaptive_label.setText(
                f"Mode: {adp.get('mode')} | "
                f"Wave: {adp.get('wave_size')} | "
                f"Send delay: {adp.get('send_delay')} | "
                f"Error rate: {adp.get('error_rate')}"
            )
        # health
        health = max(0, 100 - int(m.get("success_rate", 100) < 50) * 50)
        self._health_bar.setValue(int(rate))

    def on_state_changed(self, state: str) -> None:
        pass  # handled in on_metrics

    def add_event(self, level: str, msg: str) -> None:
        colors = {"INFO": "#4060a0", "WARN": "#b07820", "ERROR": "#a03030", "SUCCESS": "#306030"}
        color = colors.get(level, "#506090")
        html = f'<span style="color:{color};">[{level}] {msg}</span>'
        self._event_feed.appendHtml(html)
        sb = self._event_feed.verticalScrollBar()
        sb.setValue(sb.maximum())
