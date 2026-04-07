"""
gui/forwarder_tab.py — PyQt5 tab for ContentForwarder rule management.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.account_manager import AccountManager
from core.content_forwarder import ContentForwarder, ForwardRule

logger = logging.getLogger(__name__)


class ForwarderTab(QWidget):
    def __init__(self, account_manager: AccountManager, forwarder: ContentForwarder, parent=None):
        super().__init__(parent)
        self.accounts = account_manager
        self.forwarder = forwarder
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Auto Forwarder")
        title.setObjectName("label_title")
        root.addWidget(title)

        sub = QLabel(
            "Create rules to automatically forward messages from source channels to targets. "
            "Supports keyword filtering and daily limits."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#4a5080; font-size:11px;")
        root.addWidget(sub)

        # Add rule section
        add_box = QGroupBox("Add Forwarding Rule")
        alay = QVBoxLayout(add_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Rule Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("crypto_signals")
        self._name_edit.setMaximumWidth(200)
        row1.addWidget(self._name_edit)

        row1.addWidget(QLabel("Daily Max:"))
        self._daily_max = QSpinBox()
        self._daily_max.setRange(1, 1000)
        self._daily_max.setValue(50)
        self._daily_max.setFixedWidth(70)
        row1.addWidget(self._daily_max)

        row1.addStretch()
        alay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Sources:"))
        self._sources_edit = QLineEdit()
        self._sources_edit.setPlaceholderText("@channel1, @channel2 (comma-separated)")
        row2.addWidget(self._sources_edit)
        alay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Targets:"))
        self._targets_edit = QLineEdit()
        self._targets_edit.setPlaceholderText("@my_group1, @my_group2 (comma-separated)")
        row3.addWidget(self._targets_edit)
        alay.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Keywords:"))
        self._keywords_edit = QLineEdit()
        self._keywords_edit.setPlaceholderText("buy, sell, signal (empty = forward everything)")
        row4.addWidget(self._keywords_edit)
        alay.addLayout(row4)

        btn_add = QPushButton("➕  Add Rule")
        btn_add.setObjectName("btn_start")
        btn_add.clicked.connect(self._add_rule)
        alay.addWidget(btn_add)

        root.addWidget(add_box)

        # Rules table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Sources", "Targets", "Keywords", "Daily Limit", "Status"]
        )
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

        # Controls
        ctrl_row = QHBoxLayout()

        ctrl_row.addWidget(QLabel("Account:"))
        self._acc_combo = QComboBox()
        self._acc_combo.setMinimumWidth(180)
        ctrl_row.addWidget(self._acc_combo)

        self._btn_start = QPushButton("▶  Start Monitoring")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setMinimumHeight(36)
        self._btn_start.clicked.connect(self._on_start)
        ctrl_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("⏹  Stop")
        self._btn_stop.setObjectName("btn_danger")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        ctrl_row.addWidget(self._btn_stop)

        self._btn_remove = QPushButton("🗑  Remove Selected")
        self._btn_remove.clicked.connect(self._remove_selected)
        ctrl_row.addWidget(self._btn_remove)

        ctrl_row.addStretch()

        # Stats
        self._stats_label = QLabel("📡 Idle")
        self._stats_label.setStyleSheet("color:#5ab4f0; font-size:12px; font-weight:600;")
        ctrl_row.addWidget(self._stats_label)

        root.addLayout(ctrl_row)

        # Status
        self._status = QLabel("Ready — add rules and start monitoring")
        self._status.setStyleSheet("color:#5060a0; font-size:11px;")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        root.addStretch()
        self._refresh_combo()

    def _refresh_combo(self):
        self._acc_combo.clear()
        for acc in self.accounts.get_all():
            icon = "✅" if acc.client else "❌"
            self._acc_combo.addItem(f"{icon} {acc.phone}", acc)

    def on_accounts_changed(self):
        self._refresh_combo()

    def _refresh_table(self):
        rules = self.forwarder.get_rules()
        self._table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self._table.setItem(row, 0, QTableWidgetItem(rule.name))
            self._table.setItem(row, 1, QTableWidgetItem(", ".join(rule.source_chats)))
            self._table.setItem(row, 2, QTableWidgetItem(", ".join(rule.target_chats)))
            self._table.setItem(row, 3, QTableWidgetItem(", ".join(rule.keywords) or "(all)"))
            self._table.setItem(row, 4, QTableWidgetItem(str(rule.max_daily)))
            status = "✅ Enabled" if rule.enabled else "❌ Disabled"
            si = QTableWidgetItem(status)
            si.setForeground(QColor("#40d060") if rule.enabled else QColor("#e05050"))
            self._table.setItem(row, 5, si)
            self._table.setRowHeight(row, 32)

    def _add_rule(self):
        name = self._name_edit.text().strip()
        if not name:
            self._status.setText("❌ Enter a rule name")
            return

        sources = [s.strip() for s in self._sources_edit.text().split(",") if s.strip()]
        targets = [t.strip() for t in self._targets_edit.text().split(",") if t.strip()]
        keywords = [k.strip() for k in self._keywords_edit.text().split(",") if k.strip()]

        if not sources or not targets:
            self._status.setText("❌ Add source and target chats")
            return

        rule = ForwardRule(
            name=name,
            source_chats=sources,
            target_chats=targets,
            keywords=keywords,
            max_daily=self._daily_max.value(),
        )

        if self.forwarder.add_rule(rule):
            self._refresh_table()
            self._name_edit.clear()
            self._sources_edit.clear()
            self._targets_edit.clear()
            self._keywords_edit.clear()
            self._status.setText(f"✅ Rule '{name}' added")
            self._status.setStyleSheet("color:#40d060; font-size:11px;")
        else:
            self._status.setText(f"❌ Rule '{name}' already exists")

    def _remove_selected(self):
        rows = sorted(set(i.row() for i in self._table.selectedItems()))
        rules = self.forwarder.get_rules()
        for row in reversed(rows):
            if row < len(rules):
                self.forwarder.remove_rule(rules[row].name)
        self._refresh_table()

    def _on_start(self):
        acc = self._acc_combo.currentData()
        if not acc or not acc.client:
            self._status.setText("❌ Account not logged in")
            return

        asyncio.ensure_future(self._start_forwarding(acc))

    async def _start_forwarding(self, account):
        def _log(level, msg):
            self._status.setText(msg)
            color = "#40d060" if level == "INFO" else "#e05050"
            self._status.setStyleSheet(f"color:{color}; font-size:11px;")

        await self.forwarder.start_forwarding(account.client, log_cb=_log)
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

        stats = self.forwarder.get_stats()
        self._stats_label.setText(
            f"📡 Live | Rules: {stats.rules_active} | "
            f"Forwarded: {stats.total_forwarded}"
        )

    def _on_stop(self):
        self.forwarder.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._stats_label.setText("📡 Stopped")
        self._status.setText("🛑 Forwarder stopped")
