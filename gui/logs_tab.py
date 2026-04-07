"""Logs Tab — color-coded live log viewer."""
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)


class LogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("System Log")
        title.setObjectName("label_title")
        hdr.addWidget(title)
        hdr.addStretch()

        self._count = QLabel("0 entries")
        self._count.setStyleSheet("color:#303060; font-size:11px;")
        hdr.addWidget(self._count)

        btn_clear = QPushButton("🗑 Clear")
        btn_clear.clicked.connect(self._clear)
        hdr.addWidget(btn_clear)
        layout.addLayout(hdr)

        legend = QHBoxLayout()
        for text, color in [("● INFO", "#4060a0"), ("● SUCCESS", "#306030"),
                             ("● WARN", "#b07820"), ("● ERROR", "#a03030")]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color:{color}; font-size:11px;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "background:#06060e; color:#4050a0; "
            "font-family:Consolas,monospace; font-size:12px; "
            "border:1px solid #141430; border-radius:6px;"
        )
        layout.addWidget(self._log)

        self._entry_count = 0

    def append(self, level: str, msg: str):
        colors = {
            "INFO":    "#3a5090",
            "SUCCESS": "#306040",
            "WARN":    "#907030",
            "WARNING": "#907030",
            "ERROR":   "#904040",
        }
        color = colors.get(level.upper(), "#3a5090")
        from PyQt5.QtCore import QDateTime
        ts = QDateTime.currentDateTime().toString("hh:mm:ss")
        html = f'<span style="color:#222240;">[{ts}]</span> <span style="color:{color};">[{level}] {msg}</span>'
        self._log.appendHtml(html)
        self._entry_count += 1
        self._count.setText(f"{self._entry_count} entries")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear(self):
        self._log.clear()
        self._entry_count = 0
        self._count.setText("0 entries")
