"""
gui/styles.py — Furaya v6.0 Enterprise
Premium dark glassmorphism — Electric Cyan on near-black.
"""

STYLESHEET = """
/* ════════════════════════════════════════════════════════════
   FURAYA v6.0 ENTERPRISE — Premium Dark Glassmorphism
   Background: #08090f   Accent: #00d4ff   Gold: #ffd700
   Green: #00ff88        Danger: #ff3366
   ════════════════════════════════════════════════════════════ */

* { outline: none; }

QMainWindow, QWidget {
    background-color: #08090f;
    color: #c8d8e8;
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    font-size: 13px;
}

/* ── Sidebar ──────────────────────────────────────────── */

#sidebar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #050610, stop:1 #0a0e1c);
    border-right: 1px solid rgba(0,212,255,0.14);
    min-width: 200px;
    max-width: 200px;
}

#logo_label {
    color: #00d4ff;
    font-size: 24px;
    font-weight: 900;
    letter-spacing: 5px;
    padding: 30px 22px 4px 22px;
}

#version_label {
    color: #ffd700;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 0px 22px 20px 22px;
}

#sidebar_btn {
    background: transparent;
    color: #5a7a98;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 13px 18px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.3px;
}

#sidebar_btn:hover {
    background: rgba(0,212,255,0.07);
    color: #9ac8e8;
    border-left: 3px solid rgba(0,212,255,0.35);
}

#sidebar_btn[active="true"] {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(0,212,255,0.14), stop:1 rgba(0,212,255,0.03));
    color: #00d4ff;
    border-left: 3px solid #00d4ff;
    font-weight: 700;
}

#status_dot { font-size: 11px; padding: 6px 20px; color: #506070; }

/* ── Glass Panels ─────────────────────────────────────── */

#glass_panel {
    background: rgba(255,255,255,0.024);
    border: 1px solid rgba(0,212,255,0.11);
    border-radius: 12px;
}

#card {
    background: rgba(0,20,42,0.55);
    border: 1px solid rgba(0,212,255,0.13);
    border-radius: 10px;
    padding: 16px;
}

/* ── Buttons ──────────────────────────────────────────── */

QPushButton {
    background: rgba(0,212,255,0.09);
    color: #00d4ff;
    border: 1px solid rgba(0,212,255,0.32);
    border-radius: 7px;
    padding: 9px 22px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.4px;
}
QPushButton:hover {
    background: rgba(0,212,255,0.20);
    border-color: rgba(0,212,255,0.80);
    color: #ffffff;
}
QPushButton:pressed { background: rgba(0,212,255,0.32); }
QPushButton:disabled {
    background: rgba(255,255,255,0.018);
    color: #253545;
    border-color: rgba(255,255,255,0.04);
}

#btn_primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #007ec6, stop:1 #00b8e6);
    color: #ffffff;
    border: none;
    font-size: 13px;
    font-weight: 700;
    padding: 11px 30px;
    border-radius: 7px;
    letter-spacing: 0.8px;
}
#btn_primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #009ad4, stop:1 #00d4ff);
}
#btn_primary:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #006aac, stop:1 #0090c8);
}
#btn_primary:disabled { background: #131e2a; color: #2a3c4e; border: none; }

#btn_danger {
    background: rgba(255,50,80,0.10);
    color: #ff3366;
    border: 1px solid rgba(255,50,80,0.32);
    border-radius: 7px;
}
#btn_danger:hover { background: rgba(255,50,80,0.22); border-color: #ff3366; }

#btn_gold {
    background: rgba(255,215,0,0.09);
    color: #ffd700;
    border: 1px solid rgba(255,215,0,0.28);
    border-radius: 7px;
}
#btn_gold:hover { background: rgba(255,215,0,0.20); border-color: #ffd700; }

#btn_success {
    background: rgba(0,255,136,0.09);
    color: #00ff88;
    border: 1px solid rgba(0,255,136,0.28);
    border-radius: 7px;
}
#btn_success:hover { background: rgba(0,255,136,0.20); border-color: #00ff88; }

/* ── Inputs ───────────────────────────────────────────── */

QLineEdit, QTextEdit, QPlainTextEdit {
    background: rgba(0,18,38,0.85);
    color: #d0e4f4;
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 7px;
    padding: 9px 14px;
    selection-background-color: rgba(0,212,255,0.28);
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: rgba(0,212,255,0.58);
    background: rgba(0,28,55,0.95);
}
QTextEdit, QPlainTextEdit {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

QSpinBox, QDoubleSpinBox {
    background: rgba(0,18,38,0.85);
    color: #d0e4f4;
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 7px;
    padding: 7px 12px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: rgba(0,212,255,0.09);
    border: none;
    width: 18px;
}

/* ── Tables ───────────────────────────────────────────── */

QTableWidget {
    background: rgba(0,12,28,0.75);
    color: #a0b8d0;
    border: 1px solid rgba(0,212,255,0.09);
    border-radius: 8px;
    gridline-color: rgba(0,212,255,0.05);
    selection-background-color: rgba(0,212,255,0.16);
    selection-color: #ffffff;
    alternate-background-color: rgba(0,212,255,0.025);
}
QTableWidget::item { padding: 9px 12px; border-bottom: 1px solid rgba(0,212,255,0.04); }
QTableWidget::item:selected { background: rgba(0,212,255,0.16); }
QTableWidget::item:hover { background: rgba(0,212,255,0.08); }

QHeaderView::section {
    background: rgba(0,25,55,0.85);
    color: #00d4ff;
    border: none;
    border-bottom: 1px solid rgba(0,212,255,0.18);
    border-right: 1px solid rgba(0,212,255,0.05);
    padding: 9px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── ScrollBars ───────────────────────────────────────── */

QScrollBar:vertical {
    background: rgba(0,18,38,0.5);
    width: 7px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(0,212,255,0.22);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: rgba(0,212,255,0.42); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: rgba(0,18,38,0.5);
    height: 7px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: rgba(0,212,255,0.22);
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Progress bar ─────────────────────────────────────── */

QProgressBar {
    background: rgba(0,18,38,0.8);
    border: 1px solid rgba(0,212,255,0.16);
    border-radius: 5px;
    height: 7px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0066cc, stop:1 #00d4ff);
    border-radius: 5px;
}

/* ── Status bar ───────────────────────────────────────── */

QStatusBar {
    background: #04050c;
    color: #2a3c4e;
    border-top: 1px solid rgba(0,212,255,0.09);
    font-size: 11px;
}

/* ── ComboBox ─────────────────────────────────────────── */

QComboBox {
    background: rgba(0,18,38,0.85);
    color: #a0b8d0;
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 7px;
    padding: 8px 14px;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #0c1220;
    color: #a0b8d0;
    border: 1px solid rgba(0,212,255,0.22);
    selection-background-color: rgba(0,212,255,0.22);
}

/* ── Dialogs ──────────────────────────────────────────── */

QDialog {
    background: #0c1020;
    border: 1px solid rgba(0,212,255,0.22);
    border-radius: 12px;
}

/* ── CheckBox / RadioButton ───────────────────────────── */

QCheckBox { spacing: 9px; color: #8aa8c0; }
QCheckBox::indicator {
    width: 17px; height: 17px;
    background: rgba(0,18,38,0.85);
    border: 1px solid rgba(0,212,255,0.28);
    border-radius: 4px;
}
QCheckBox::indicator:checked {
    background: rgba(0,212,255,0.28);
    border-color: #00d4ff;
}

QRadioButton { spacing: 9px; color: #8aa8c0; }
QRadioButton::indicator {
    width: 15px; height: 15px;
    background: rgba(0,18,38,0.85);
    border: 1px solid rgba(0,212,255,0.28);
    border-radius: 8px;
}
QRadioButton::indicator:checked {
    background: rgba(0,212,255,0.30);
    border-color: #00d4ff;
}

/* ── Splitter ─────────────────────────────────────────── */

QSplitter::handle { background: rgba(0,212,255,0.06); }

/* ── Tooltip ──────────────────────────────────────────── */

QToolTip {
    background: #0d1622;
    color: #a0c8e8;
    border: 1px solid rgba(0,212,255,0.30);
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 12px;
}

/* ── GroupBox ─────────────────────────────────────────── */

QGroupBox {
    background: rgba(0,18,38,0.40);
    border: 1px solid rgba(0,212,255,0.12);
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 8px;
    font-weight: 600;
    color: #6a9ab8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #00d4ff;
    font-size: 11px;
    letter-spacing: 1px;
}

/* ── Tab widget ───────────────────────────────────────── */

QTabWidget::pane {
    background: rgba(0,12,28,0.6);
    border: 1px solid rgba(0,212,255,0.10);
    border-radius: 9px;
}
QTabBar::tab {
    background: rgba(0,18,38,0.5);
    color: #5a7a98;
    border: 1px solid rgba(0,212,255,0.08);
    border-bottom: none;
    padding: 9px 18px;
    margin-right: 2px;
    border-radius: 7px 7px 0 0;
}
QTabBar::tab:selected {
    background: rgba(0,212,255,0.12);
    color: #00d4ff;
    border-color: rgba(0,212,255,0.24);
}
QTabBar::tab:hover { background: rgba(0,212,255,0.07); color: #7ab8d8; }
"""
