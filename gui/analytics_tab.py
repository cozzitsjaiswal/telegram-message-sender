"""Analytics Tab — account performance table and session history."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core.performance_tracker import PerformanceTracker


class AnalyticsTab(QWidget):
    def __init__(self, tracker: PerformanceTracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Analytics")
        title.setObjectName("label_title")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        self._btn_refresh = QPushButton("🔄  Refresh")
        self._btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(self._btn_refresh)
        btn_row.addStretch()
        self._overall_label = QLabel("")
        self._overall_label.setStyleSheet("color:#d0a020; font-weight:600;")
        btn_row.addWidget(self._overall_label)
        layout.addLayout(btn_row)

        # Account table
        layout.addWidget(QLabel("Account Performance"))
        self._acc_table = QTableWidget(0, 5)
        self._acc_table.setHorizontalHeaderLabels(["Phone", "Sent", "Success", "Failed", "Rate"])
        self._acc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 5):
            self._acc_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self._acc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._acc_table.setAlternatingRowColors(True)
        self._acc_table.verticalHeader().setVisible(False)
        layout.addWidget(self._acc_table)

        # Session table
        layout.addWidget(QLabel("Session History"))
        self._ses_table = QTableWidget(0, 6)
        self._ses_table.setHorizontalHeaderLabels(["Mode", "Duration", "Waves", "Sent", "Success", "Rate"])
        self._ses_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for c in range(1, 6):
            self._ses_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self._ses_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._ses_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._ses_table.setAlternatingRowColors(True)
        self._ses_table.verticalHeader().setVisible(False)
        layout.addWidget(self._ses_table)

        self.refresh()

    def refresh(self):
        # Accounts
        metrics = self.tracker.get_account_metrics()
        self._acc_table.setRowCount(len(metrics))
        for row, m in enumerate(metrics):
            self._acc_table.setItem(row, 0, QTableWidgetItem(m.phone))
            self._acc_table.setItem(row, 1, QTableWidgetItem(str(m.sent)))
            self._acc_table.setItem(row, 2, QTableWidgetItem(str(m.success)))
            self._acc_table.setItem(row, 3, QTableWidgetItem(str(m.failed)))
            rate = m.success_rate
            ri = QTableWidgetItem(f"{rate:.1f}%")
            ri.setForeground(QColor("#40d060") if rate >= 70 else QColor("#e05050"))
            self._acc_table.setItem(row, 4, ri)

        # Sessions
        sessions = self.tracker.get_sessions()[-20:]   # last 20
        self._ses_table.setRowCount(len(sessions))
        for row, s in enumerate(reversed(sessions)):
            self._ses_table.setItem(row, 0, QTableWidgetItem(s.mode))
            self._ses_table.setItem(row, 1, QTableWidgetItem(f"{s.duration_minutes:.1f} min"))
            self._ses_table.setItem(row, 2, QTableWidgetItem(str(s.waves)))
            self._ses_table.setItem(row, 3, QTableWidgetItem(str(s.total_sent)))
            self._ses_table.setItem(row, 4, QTableWidgetItem(str(s.total_success)))
            rate = s.success_rate
            ri = QTableWidgetItem(f"{rate:.1f}%")
            ri.setForeground(QColor("#40d060") if rate >= 70 else QColor("#e05050"))
            self._ses_table.setItem(row, 5, ri)

        # Overall
        self._overall_label.setText(
            f"Total sent: {self.tracker.total_sent_ever:,}  |  "
            f"Overall rate: {self.tracker.overall_success_rate:.1f}%"
        )

    def on_metrics(self, m: dict):
        # Called on each metrics event — refresh every 5 waves
        self.refresh()
