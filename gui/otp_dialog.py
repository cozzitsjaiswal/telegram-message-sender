"""OTP dialog – shown during account login when Telegram sends a code."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class OtpDialog(QDialog):
    def __init__(self, phone: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Telegram Login")
        self.setMinimumWidth(300)
        self._code = ""
        self._password = ""
        self._setup_ui(phone)

    def _setup_ui(self, phone: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(f"A verification code was sent to <b>{phone}</b>.\nEnter it below.")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self._otp_input = QLineEdit()
        self._otp_input.setPlaceholderText("5-digit code")
        form.addRow("Verification code:", self._otp_input)

        self._pw_input = QLineEdit()
        self._pw_input.setEchoMode(QLineEdit.Password)
        self._pw_input.setPlaceholderText("Only if 2FA is enabled")
        form.addRow("2FA Password (optional):", self._pw_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self._code = self._otp_input.text().strip()
        self._password = self._pw_input.text().strip()
        self.accept()

    @property
    def code(self) -> str:
        return self._code

    @property
    def password(self) -> str:
        return self._password
