"""
main.py — Furaya v6.0 Enterprise Entry Point
"""

import sys
import traceback
from pathlib import Path

# ── Early pytdbot compatibility patch ──────────────────────────────────────────
try:
    from pytdbot.utils import obj_encoder as _enc
    _orig_dict_to_obj = _enc.dict_to_obj

    def _patched_dict_to_obj(dict_obj, client=None):
        try:
            return _orig_dict_to_obj(dict_obj, client)
        except AttributeError:
            return dict_obj
        except Exception:
            return dict_obj if isinstance(dict_obj, dict) else {}

    _enc.dict_to_obj = _patched_dict_to_obj
    import pytdbot.utils.obj_encoder as _mod_enc
    _mod_enc.dict_to_obj = _patched_dict_to_obj

    try:
        from pytdbot import types as _td_types
        if not hasattr(_td_types, '__getattr__'):
            def _make_stub(name):
                from dataclasses import dataclass
                @dataclass(frozen=True)
                class _Stub:
                    pass
                _Stub.__name__ = name
                return _Stub
            _td_types.__getattr__ = _make_stub
    except Exception:
        pass

except Exception as e:
    print(f"Warning: pytdbot patch failed: {e}", file=sys.stderr)

# ── Standard imports ────────────────────────────────────────────────────────────
import asyncio
import asyncio.base_events
import asyncio.runners
import asyncio.exceptions
import asyncio.coroutines
import asyncio.format_helpers
import asyncio.selector_events
import asyncio.windows_events
import logging

from PyQt5.QtWidgets import QApplication
import qasync

from gui.main_window import MainWindow
from gui.styles import STYLESHEET


def setup_logging():
    log_dir = Path.home() / "FurayaPromoEngine"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "furaya.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(fh)

    logging.info("Logging initialized — writing to %s", log_file)


def global_excepthook(exc_type, exc_value, exc_tb):
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", text)
    try:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Furaya — Fatal Error",
            f"An unexpected error occurred:\n{exc_value}\n\nCheck log: ~/FurayaPromoEngine/furaya.log")
    except Exception:
        pass


sys.excepthook = global_excepthook


def main():
    setup_logging()
    logging.info("Starting Furaya v6.0 Enterprise")

    app = QApplication(sys.argv)
    app.setApplicationName("Furaya")
    app.setApplicationVersion("6.0 Enterprise")
    app.setStyleSheet(STYLESHEET)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    def _asyncio_exception_handler(loop, context):
        exc = context.get("exception")
        msg = context.get("message", "")
        logging.error("Async exception: %s | %s", exc, msg)

    loop.set_exception_handler(_asyncio_exception_handler)

    window = MainWindow()
    window.show()

    try:
        with loop:
            loop.run_forever()
    except Exception as e:
        logging.critical("Main loop crashed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
