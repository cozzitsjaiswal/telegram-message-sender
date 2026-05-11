"""
main.py — Furaya v5.5 Entry Point
"""

import sys
import traceback
from pathlib import Path

# ── Early pytdbot compatibility patch ────────────────────────────────────────
# Patch must run BEFORE pytdbot is imported anywhere else.
try:
    from pytdbot.utils import obj_encoder as _enc

    _orig_dict_to_obj = _enc.dict_to_obj

    def _patched_dict_to_obj(dict_obj, client=None):
        try:
            return _orig_dict_to_obj(dict_obj, client)
        except AttributeError as e:
            # Unknown TDLib type — return raw dict to avoid crash
            type_name = dict_obj.get("@type") if isinstance(dict_obj, dict) else "?"
            # We'll log later after logging is configured
            return dict_obj
        except Exception:
            # Any other error — return raw dict to avoid crash
            return dict_obj if isinstance(dict_obj, dict) else {}

    _enc.dict_to_obj = _patched_dict_to_obj

    # Also patch at module level
    import pytdbot.utils.obj_encoder as _mod_enc
    _mod_enc.dict_to_obj = _patched_dict_to_obj

    # Also patch at module level
    import pytdbot.utils.obj_encoder as _mod_enc
    _mod_enc.dict_to_obj = _patched_dict_to_obj

    # Provide stub for any missing TDLib types
    try:
        from pytdbot import types as _td_types
        from pytdbot.utils import utils as _td_utils

        _orig_to_camel = _td_utils.to_camel_case

        def _patched_to_camel(snake_str):
            try:
                return _orig_to_camel(snake_str)
            except Exception:
                return snake_str

        _td_utils.to_camel_case = _patched_to_camel

        _orig_from_dict = getattr(_td_types, 'Base', object).__dict__.get('from_dict') if hasattr(_td_types, 'Base') else None

        def _make_unknown_type_class(type_name):
            from dataclasses import dataclass
            @dataclass(frozen=True)
            class UnknownType:
                """Dynamic placeholder for unknown TDLib types."""
                @classmethod
                def from_dict(cls, data):
                    return data
            UnknownType.__name__ = type_name
            return UnknownType

        _orig_getattr = getattr(_td_types, '__getattribute__', None)

        def _patched_getattr(self, name):
            try:
                return _orig_getattr(name) if _orig_getattr else object.__getattribute__(self, name)
            except AttributeError:
                return _make_unknown_type_class(name)

        if not hasattr(_td_types, '__getattr__'):
            _td_types.__getattr__ = lambda name: _make_unknown_type_class(name)

    except Exception:
        pass
    try:
        from pytdbot import types as _td_types

        if not hasattr(_td_types, "TextEntityTypeDateTime"):
            from dataclasses import dataclass

            @dataclass(frozen=True)
            class TextEntityTypeDateTime:
                """Placeholder for TDLib textEntityTypeDateTime."""

                pass

            setattr(_td_types, "TextEntityTypeDateTime", TextEntityTypeDateTime)
    except Exception:
        pass

except Exception as e:
    # Can't log yet; will write to stderr
    print(f"Warning: pytdbot patch failed: {e}", file=sys.stderr)

# ── Standard imports ───────────────────────────────────────────────────────────
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


# ── Global logging setup (file + console) ────────────────────────────────────
def setup_logging():
    log_dir = Path.home() / "FurayaPromoEngine"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "furaya.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(sh)

    # File
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(fh)

    logging.info("Logging initialized — writing to %s", log_file)


# ── Global exception hook ────────────────────────────────────────────────────
def global_excepthook(exc_type, exc_value, exc_tb):
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", text)
    # Also show a message box if possible
    try:
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.critical(
            None,
            "Furaya — Fatal Error",
            f"An unexpected error occurred:\n{exc_value}\n\nSee log file for details.",
        )
    except Exception:
        pass


sys.excepthook = global_excepthook

logging.basicConfig(level=logging.DEBUG)


def main():
    setup_logging()
    logging.info("Starting Furaya v6.0 Enterprise")

    app = QApplication(sys.argv)
    app.setApplicationName("Furaya")
    app.setApplicationVersion("6.0 Enterprise")
    app.setStyleSheet(STYLESHEET)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Handle unhandled async task exceptions
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
