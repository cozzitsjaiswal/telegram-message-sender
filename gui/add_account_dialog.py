"""Add Account dialog – collects phone, API ID, API Hash."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.account import Account


class AddAccountDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Telegram Account")
        self.setMinimumWidth(360)
        self._account: Account | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        note = QLabel(
            "Enter your Telegram credentials.\n"
            "Get API ID & Hash from <b>my.telegram.org</b>."
        )
        note.setWordWrap(True)
        note.setOpenExternalLinks(True)
        layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(10)

        self._phone = QLineEdit()
        self._phone.setPlaceholderText("+1 234 567 8900")
        form.addRow("Phone number:", self._phone)

        self._api_id = QLineEdit()
        self._api_id.setPlaceholderText("12345678")
        form.addRow("API ID:", self._api_id)

        self._api_hash = QLineEdit()
        self._api_hash.setPlaceholderText("abcdef1234567890abcdef1234567890")
        form.addRow("API Hash:", self._api_hash)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        phone = self._phone.text().strip()
        api_id_str = self._api_id.text().strip()
        api_hash = self._api_hash.text().strip()

        if not phone:
            QMessageBox.warning(self, "Validation", "Phone number is required.")
            return
        try:
            api_id = int(api_id_str)
        except ValueError:
            QMessageBox.warning(self, "Validation", "API ID must be a number.")
            return
        if not api_hash:
            QMessageBox.warning(self, "Validation", "API Hash is required.")
            return

        self._account = Account(phone=phone, api_id=api_id, api_hash=api_hash)
        self.accept()

    @property
    def account(self) -> Account | None:
        return self._account
