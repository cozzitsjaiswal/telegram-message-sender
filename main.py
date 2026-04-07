"""Furaya Campaign System — Entry point."""
from __future__ import annotations

import logging
import sys
import os
from pathlib import Path

# ── Data directory ───────────────────────────────────────────────────
# Use the user's home folder — always writable, no admin rights needed.
BASE_DIR = Path.home() / "FurayaPromoEngine"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Change working dir so all relative Path("data/...") calls resolve here.
os.chdir(str(BASE_DIR))

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

import asyncio
import qasync
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import DARK_THEME


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Furaya Campaign System")
    app.setStyleSheet(DARK_THEME)

    for ico in [Path(sys.executable).parent / "furaya.ico", Path(__file__).parent / "furaya.ico"]:
        if ico.exists():
            app.setWindowIcon(QIcon(str(ico)))
            break

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
