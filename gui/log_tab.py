"""Log tab – colour-coded, timestamped log display."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

# Colour map for log levels
_COLOURS = {
    "INFO":    "#e0e0e0",
    "WARNING": "#f0c040",
    "ERROR":   "#e05050",
    "SUCCESS": "#40c080",
    "DEBUG":   "#8090a8",
}

_ICONS = {
    "INFO":    "ℹ",
    "WARNING": "⚠",
    "ERROR":   "✖",
    "SUCCESS": "✔",
    "DEBUG":   "·",
}


class LogTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self._log_view.setMaximumBlockCount(5000)   # cap memory usage
        self._log_view.setPlaceholderText("Log output will appear here…")
        layout.addWidget(self._log_view)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_clear = QPushButton("Clear Log")
        self._btn_clear.setObjectName("btn_danger")
        self._btn_clear.setFixedWidth(110)
        self._btn_clear.clicked.connect(self._log_view.clear)
        btn_row.addWidget(self._btn_clear)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(self, level: str, message: str) -> None:
        """Append a coloured log line. Thread-safe via Qt signal queuing."""
        level = level.upper()
        colour = _COLOURS.get(level, _COLOURS["INFO"])
        icon = _ICONS.get(level, "·")
        ts = datetime.now().strftime("%H:%M:%S")

        line = f"[{ts}] {icon} {message}"

        cursor = self._log_view.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(colour))
        cursor.setCharFormat(fmt)
        cursor.insertText(line + "\n")

        self._log_view.setTextCursor(cursor)
        self._log_view.ensureCursorVisible()
