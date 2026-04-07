"""Messages Tab — manage message templates with performance scores."""
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.message_engine import MessageEngine, MessageTemplate


class EditDialog(QDialog):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Message Template")
        self.setMinimumSize(460, 280)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Message text:"))
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text)
        lay.addWidget(self.editor)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    @property
    def text(self) -> str:
        return self.editor.toPlainText().strip()


class MessagesTab(QWidget):
    messages_changed = pyqtSignal()

    def __init__(self, engine: MessageEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Message Templates")
        title.setObjectName("label_title")
        layout.addWidget(title)
        sub = QLabel("Add multiple message templates. The engine rotates them intelligently with micro-variations.")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Preview", "Used", "Score", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("➕  Add Template")
        self._btn_add.setObjectName("btn_gold")
        self._btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self._btn_add)

        self._btn_edit = QPushButton("✏️  Edit")
        self._btn_edit.clicked.connect(self._on_edit)
        btn_row.addWidget(self._btn_edit)

        self._btn_remove = QPushButton("🗑  Remove")
        self._btn_remove.setObjectName("btn_danger")
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)

        btn_row.addStretch()
        self._count_label = QLabel("0 templates")
        self._count_label.setStyleSheet("color:#4060a0;")
        btn_row.addWidget(self._count_label)
        layout.addLayout(btn_row)

    def refresh_table(self):
        templates = self.engine.get_all()
        self._table.setRowCount(len(templates))
        for row, t in enumerate(templates):
            preview = t.text[:80].replace("\n", " ") + ("…" if len(t.text) > 80 else "")
            self._table.setItem(row, 0, QTableWidgetItem(preview))
            self._table.item(row, 0).setData(Qt.UserRole, t.id)
            self._table.setItem(row, 1, QTableWidgetItem(str(t.usage_count)))
            score_item = QTableWidgetItem(f"{t.performance_score:.0f}%")
            from PyQt5.QtGui import QColor
            score_item.setForeground(
                QColor("#40d060") if t.performance_score >= 60 else QColor("#e05050")
            )
            self._table.setItem(row, 2, score_item)

            btn_del = QPushButton("🗑")
            btn_del.setObjectName("btn_danger")
            btn_del.setFixedWidth(36)
            btn_del.clicked.connect(lambda _, tid=t.id: self._remove_by_id(tid))
            self._table.setCellWidget(row, 3, btn_del)
            self._table.setRowHeight(row, 38)

        self._count_label.setText(f"{len(templates)} template(s)")

    def _on_add(self):
        dlg = EditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.text:
            self.engine.add(dlg.text)
            self.refresh_table()
            self.messages_changed.emit()

    def _on_edit(self):
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if not item:
            return
        tid = item.data(Qt.UserRole)
        tmpl = next((t for t in self.engine.get_all() if t.id == tid), None)
        if not tmpl:
            return
        dlg = EditDialog(tmpl.text, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.text:
            self.engine.update(tid, dlg.text)
            self.refresh_table()
            self.messages_changed.emit()

    def _on_remove(self):
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item:
            self._remove_by_id(item.data(Qt.UserRole))

    def _remove_by_id(self, tid: int):
        if QMessageBox.question(self, "Remove", "Remove this template?") == QMessageBox.Yes:
            self.engine.remove(tid)
            self.refresh_table()
            self.messages_changed.emit()
