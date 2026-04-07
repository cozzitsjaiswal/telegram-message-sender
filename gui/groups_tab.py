"""Groups Tab — view joined groups, their stats, and manage them."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMenu,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core.group_manager import GroupManager


class GroupsTab(QWidget):
    send_to_campaign = pyqtSignal(list)

    def __init__(self, group_manager: GroupManager, parent=None):
        super().__init__(parent)
        self.manager = group_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Group Management")
        title.setObjectName("label_title")
        layout.addWidget(title)

        sub = QLabel("All discovered/joined groups. Priority score drives campaign routing.")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Stats row
        stats_row = QHBoxLayout()
        self._lbl_total  = QLabel("Total: 0")
        self._lbl_joined = QLabel("Joined: 0")
        self._lbl_active = QLabel("Active: 0")
        for lbl in [self._lbl_total, self._lbl_joined, self._lbl_active]:
            lbl.setStyleSheet("color:#6070a8; font-weight:600; padding:0 12px;")
            stats_row.addWidget(lbl)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Group", "Members", "Priority", "Success", "Failures", "Status"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            self._table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._ctx_menu)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._btn_refresh = QPushButton("🔄  Refresh")
        self._btn_refresh.clicked.connect(self.refresh_table)
        btn_row.addWidget(self._btn_refresh)

        self._btn_remove = QPushButton("🗑  Remove Selected")
        self._btn_remove.setObjectName("btn_danger")
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.refresh_table()

    def refresh_table(self):
        groups = self.manager.get_all()
        self._table.setRowCount(len(groups))
        for row, g in enumerate(groups):
            name_item = QTableWidgetItem(g.title or g.username)
            name_item.setData(Qt.UserRole, g.username)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(f"{g.member_count:,}"))
            
            # Priority bar-like display
            pri = g.priority_score
            pri_item = QTableWidgetItem(f"{pri:.0f}")
            color = QColor("#40d060") if pri >= 70 else QColor("#d0a020") if pri >= 40 else QColor("#e05050")
            pri_item.setForeground(color)
            self._table.setItem(row, 2, pri_item)

            self._table.setItem(row, 3, QTableWidgetItem(str(g.success_count)))
            self._table.setItem(row, 4, QTableWidgetItem(str(g.failure_count)))

            if g.disabled:
                status = "🚫 Disabled"
                sc = "#e05050"
            elif g.joined:
                status = "✅ Joined"
                sc = "#40d060"
            else:
                status = "⬜ Not joined"
                sc = "#505090"
            si = QTableWidgetItem(status)
            si.setForeground(QColor(sc))
            self._table.setItem(row, 5, si)

        total = len(groups)
        joined = self.manager.joined_count
        active = len(self.manager.get_active())
        self._lbl_total.setText(f"Total: {total}")
        self._lbl_joined.setText(f"Joined: {joined}")
        self._lbl_active.setText(f"Active: {active}")

    def _ctx_menu(self, pos):
        rows = list(set(i.row() for i in self._table.selectedItems()))
        if not rows:
            return
        menu = QMenu(self)
        act_remove = menu.addAction("🗑  Remove")
        act_disable = menu.addAction("🚫  Disable")
        act_enable = menu.addAction("✅  Enable")
        action = menu.exec_(self._table.viewport().mapToGlobal(pos))
        if action == act_remove:
            self._on_remove()
        elif action == act_disable:
            for row in rows:
                uname = self._table.item(row, 0).data(Qt.UserRole)
                g = self.manager.get_by_username(uname)
                if g:
                    g.disabled = True
            self.manager.save()
            self.refresh_table()
        elif action == act_enable:
            for row in rows:
                uname = self._table.item(row, 0).data(Qt.UserRole)
                g = self.manager.get_by_username(uname)
                if g:
                    g.disabled = False
                    g.priority_score = 50.0
            self.manager.save()
            self.refresh_table()

    def _on_remove(self):
        rows = list(set(i.row() for i in self._table.selectedItems()))
        for row in sorted(rows, reverse=True):
            uname = self._table.item(row, 0).data(Qt.UserRole)
            if uname in self.manager._groups:
                del self.manager._groups[uname]
        self.manager.save()
        self.refresh_table()

    def on_groups_changed(self):
        self.refresh_table()
