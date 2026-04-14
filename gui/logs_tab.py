"""
gui/logs_tab.py — Furaya v5.5
Color-coded live log viewer.
"""
from __future__ import annotations
from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton
)


LOG_COLORS = {
    "INFO":    "#507090",
    "WARN":    "#b08020",
    "WARNING": "#b08020",
    "ERROR":   "#b02030",
    "SUCCESS": "#208050",
    "DEBUG":   "#304050",
}


class LogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("LOGS")
        title.setStyleSheet("color: #00d4ff; font-size: 18px; font-weight: 800; letter-spacing: 3px;")
        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(80)
        btn_clear.setFixedHeight(30)
        btn_clear.clicked.connect(self.clear)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(btn_clear)
        lay.addLayout(hdr)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        self._view.setStyleSheet("""
            background: rgba(0,8,16,0.95);
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 8px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            color: #507090;
            padding: 8px;
        """)
        lay.addWidget(self._view)

    def append(self, level: str, msg: str):
        color = LOG_COLORS.get(level.upper(), "#507090")
        ts = datetime.now().strftime("%H:%M:%S")
        lvl_colors = {
            "INFO": "#1a3a5a", "WARN": "#3a2800", "WARNING": "#3a2800",
            "ERROR": "#3a0010", "SUCCESS": "#002010", "DEBUG": "#1a1a2a",
        }
        bg = lvl_colors.get(level.upper(), "#1a3a5a")
        self._view.append(
            f'<span style="color:#1a3a5a">[{ts}]</span> '
            f'<span style="color:{color}; font-weight:600">[{level.upper()[:4]}]</span> '
            f'<span style="color:{color}">{msg}</span>'
        )
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self):
        self._view.clear()
