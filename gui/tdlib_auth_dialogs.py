from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import pyqtSignal, QEventLoop

class TDLibOTPDialog(QDialog):
    submitted = pyqtSignal(str)
    def __init__(self, phone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Telegram Login – {phone}")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Enter OTP sent to {phone}:"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("12345")
        layout.addWidget(self.code_input)
        btn = QPushButton("Verify")
        btn.clicked.connect(self._on_ok)
        layout.addWidget(btn)
        self.setLayout(layout)
    
    def _on_ok(self):
        self.submitted.emit(self.code_input.text())
        self.accept()

class TDLib2FADialog(QDialog):
    submitted = pyqtSignal(str)
    def __init__(self, phone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"2FA Required – {phone}")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter your 2FA password:"))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.pwd_input)
        btn = QPushButton("Login")
        btn.clicked.connect(self._on_ok)
        layout.addWidget(btn)
        self.setLayout(layout)
    
    def _on_ok(self):
        self.submitted.emit(self.pwd_input.text())
        self.accept()
