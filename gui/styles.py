"""
gui/styles.py — Furaya v5.5
Tech-savvy dark glassmorphism theme. Electric cyan on near-black.
"""

STYLESHEET = """
/* ═══════════════════════════════════════════════════
   FURAYA v5.5 — Dark Tech Theme
   Background: #0a0d14  Accent: #00d4ff  Gold: #ffd700
   ═══════════════════════════════════════════════════ */

QMainWindow, QWidget {
    background-color: #0a0d14;
    color: #c8d8e8;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}

/* ── Sidebar ──────────────────────────────────────── */

#sidebar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #060810, stop:1 #0d1220);
    border-right: 1px solid rgba(0,212,255,0.12);
    min-width: 195px;
    max-width: 195px;
}

#logo_label {
    color: #00d4ff;
    font-size: 22px;
    font-weight: 900;
    letter-spacing: 4px;
    padding: 28px 20px 4px 20px;
}

#version_label {
    color: #ffd700;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    padding: 0px 20px 16px 20px;
}

#sidebar_btn {
    background: transparent;
    color: #6a8aa8;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 12px 16px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
}

#sidebar_btn:hover {
    background: rgba(0,212,255,0.06);
    color: #a8c8e8;
    border-left: 3px solid rgba(0,212,255,0.3);
}

#sidebar_btn[active="true"] {
    background: rgba(0,212,255,0.10);
    color: #00d4ff;
    border-left: 3px solid #00d4ff;
    font-weight: 700;
}

/* ── Status indicators ────────────────────────────── */

#status_dot {
    font-size: 10px;
    padding: 6px 20px;
    color: #506070;
}

/* ── Panels / Glass cards ─────────────────────────── */

#glass_panel {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(0,212,255,0.10);
    border-radius: 10px;
}

#card {
    background: rgba(0,20,40,0.6);
    border: 1px solid rgba(0,212,255,0.12);
    border-radius: 8px;
    padding: 14px;
}

/* ── Buttons ──────────────────────────────────────── */

QPushButton {
    background: rgba(0,212,255,0.08);
    color: #00d4ff;
    border: 1px solid rgba(0,212,255,0.30);
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.5px;
}

QPushButton:hover {
    background: rgba(0,212,255,0.18);
    border-color: #00d4ff;
    color: #ffffff;
}

QPushButton:pressed {
    background: rgba(0,212,255,0.30);
}

QPushButton:disabled {
    background: rgba(255,255,255,0.02);
    color: #2a3a4a;
    border-color: rgba(255,255,255,0.05);
}

#btn_primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00a8d4, stop:1 #0088ff);
    color: #ffffff;
    border: none;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 28px;
    border-radius: 6px;
    letter-spacing: 1px;
}
#btn_primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00c4f0, stop:1 #00aaff);
}
#btn_primary:disabled { background: #1a2a3a; color: #304050; }

#btn_danger {
    background: rgba(255,50,80,0.12);
    color: #ff3366;
    border: 1px solid rgba(255,50,80,0.35);
}
#btn_danger:hover {
    background: rgba(255,50,80,0.25);
    border-color: #ff3366;
}

#btn_gold {
    background: rgba(255,215,0,0.10);
    color: #ffd700;
    border: 1px solid rgba(255,215,0,0.30);
}
#btn_gold:hover {
    background: rgba(255,215,0,0.20);
    border-color: #ffd700;
}

#btn_success {
    background: rgba(0,255,136,0.10);
    color: #00ff88;
    border: 1px solid rgba(0,255,136,0.30);
}
#btn_success:hover {
    background: rgba(0,255,136,0.20);
    border-color: #00ff88;
}

/* ── Inputs ───────────────────────────────────────── */

QLineEdit, QTextEdit, QPlainTextEdit {
    background: rgba(0,20,40,0.8);
    color: #c8d8e8;
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: rgba(0,212,255,0.30);
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: rgba(0,212,255,0.50);
    background: rgba(0,30,55,0.9);
}

QTextEdit, QPlainTextEdit {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

QSpinBox, QDoubleSpinBox {
    background: rgba(0,20,40,0.8);
    color: #c8d8e8;
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 6px;
    padding: 6px 10px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: rgba(0,212,255,0.08);
    border: none;
}

/* ── Labels ───────────────────────────────────────── */

#section_header {
    color: #00d4ff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 6px 0 4px 0;
}

#kpi_value {
    color: #00d4ff;
    font-size: 26px;
    font-weight: 800;
}

#kpi_label {
    color: #406080;
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

#status_connected { color: #00ff88; font-weight: 700; }
#status_connecting { color: #ffd700; font-weight: 700; }
#status_failed { color: #ff3366; font-weight: 700; }
#status_pending { color: #6a8aa8; }
#status_disconnected { color: #304050; }

/* ── Tables ───────────────────────────────────────── */

QTableWidget {
    background: rgba(0,15,30,0.7);
    color: #a0b8d0;
    border: 1px solid rgba(0,212,255,0.08);
    border-radius: 6px;
    gridline-color: rgba(0,212,255,0.05);
    selection-background-color: rgba(0,212,255,0.15);
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(0,212,255,0.04);
}

QTableWidget::item:selected {
    background: rgba(0,212,255,0.15);
}

QHeaderView::section {
    background: rgba(0,30,60,0.8);
    color: #00d4ff;
    border: none;
    border-bottom: 1px solid rgba(0,212,255,0.15);
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}

/* ── ScrollBars ───────────────────────────────────── */

QScrollBar:vertical {
    background: rgba(0,20,40,0.5);
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: rgba(0,212,255,0.25);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0,212,255,0.45);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: rgba(0,20,40,0.5);
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: rgba(0,212,255,0.25);
    border-radius: 3px;
}

/* ── Tab panels ───────────────────────────────────── */

QTabWidget::pane {
    background: rgba(0,15,30,0.6);
    border: 1px solid rgba(0,212,255,0.10);
    border-radius: 8px;
}

QTabBar::tab {
    background: rgba(0,20,40,0.5);
    color: #6a8aa8;
    border: 1px solid rgba(0,212,255,0.08);
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
}

QTabBar::tab:selected {
    background: rgba(0,212,255,0.12);
    color: #00d4ff;
    border-color: rgba(0,212,255,0.25);
}

/* ── Progress bar ─────────────────────────────────── */

QProgressBar {
    background: rgba(0,20,40,0.8);
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0088ff, stop:1 #00d4ff);
    border-radius: 4px;
}

/* ── Status bar ───────────────────────────────────── */

QStatusBar {
    background: #060810;
    color: #304050;
    border-top: 1px solid rgba(0,212,255,0.08);
    font-size: 11px;
}

/* ── ComboBox ─────────────────────────────────────── */

QComboBox {
    background: rgba(0,20,40,0.8);
    color: #a0b8d0;
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 6px;
    padding: 7px 12px;
}

QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background: #0d1220;
    color: #a0b8d0;
    border: 1px solid rgba(0,212,255,0.20);
    selection-background-color: rgba(0,212,255,0.20);
}

/* ── Dialogs ──────────────────────────────────────── */

QDialog {
    background: #0d1220;
    border: 1px solid rgba(0,212,255,0.20);
    border-radius: 10px;
}

/* ── CheckBox ─────────────────────────────────────── */

QCheckBox {
    spacing: 8px;
    color: #8aa8c0;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    background: rgba(0,20,40,0.8);
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 4px;
}
QCheckBox::indicator:checked {
    background: rgba(0,212,255,0.30);
    border-color: #00d4ff;
    image: none;
}

/* ── Splitter ─────────────────────────────────────── */

QSplitter::handle {
    background: rgba(0,212,255,0.05);
}
"""
