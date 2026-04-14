"""
main.py — Furaya v5.5 Entry Point
"""
import sys
import asyncio
import logging

from PyQt5.QtWidgets import QApplication
import qasync

from gui.main_window import MainWindow
from gui.styles import STYLESHEET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Furaya")
    app.setApplicationVersion("5.5")
    app.setStyleSheet(STYLESHEET)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
