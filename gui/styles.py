"""Dark futuristic theme — Black/Red/Gold with glow accents."""

DARK_THEME = """
/* ─────────────────────────────────────────────────────── GLOBAL */
* {
    font-family: "Segoe UI", "Consolas", Arial, sans-serif;
    font-size: 13px;
    outline: none;
}
QWidget {
    background-color: #0a0a0f;
    color: #d0d0e8;
}
QMainWindow, QDialog {
    background-color: #07070d;
}

/* ─────────────────────────────────────────────────────── SIDEBAR */
#sidebar {
    background-color: #0d0d1a;
    border-right: 1px solid #1a1a30;
    min-width: 180px;
    max-width: 180px;
}
#sidebar_btn {
    background: transparent;
    color: #7080a8;
    border: none;
    border-radius: 0;
    border-left: 3px solid transparent;
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    min-width: 160px;
}
#sidebar_btn:hover {
    background-color: #121228;
    color: #c8c8f0;
    border-left: 3px solid #3a2a60;
}
#sidebar_btn[active="true"] {
    background-color: #16162e;
    color: #e05030;
    border-left: 3px solid #e05030;
}
#logo_label {
    color: #e05030;
    font-size: 18px;
    font-weight: 900;
    letter-spacing: 2px;
    padding: 20px 16px 10px;
}
#version_label {
    color: #3a3a60;
    font-size: 10px;
    padding: 0 16px 16px;
}

/* ─────────────────────────────────────────────────────── TABS */
QTabWidget::pane { border: none; }
QTabBar::tab {
    background: #0d0d1a;
    color: #5060a0;
    padding: 9px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #e05030;
    border-bottom: 2px solid #e05030;
    background: #0a0a14;
}
QTabBar::tab:hover:!selected { color: #a0a0d0; background: #0f0f20; }

/* ─────────────────────────────────────────────────────── BUTTONS */
QPushButton {
    background-color: #12122a;
    color: #a0a8d0;
    border: 1px solid #252545;
    border-radius: 5px;
    padding: 7px 18px;
    font-weight: 600;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #1a1a38;
    border-color: #404080;
    color: #d0d0f8;
}
QPushButton:pressed { background-color: #0c0c1e; }
QPushButton:disabled { background-color: #0d0d1a; color: #303050; border-color: #1a1a2e; }

QPushButton#btn_start {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a3a1a,stop:1 #0d2a0d);
    border: 1px solid #2a6a2a;
    color: #40d060;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 6px;
}
QPushButton#btn_start:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #204a20,stop:1 #123012);
    border-color: #40a040;
    color: #60f080;
}
QPushButton#btn_stop {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a0a0a,stop:1 #2a0808);
    border: 1px solid #7a2020;
    color: #e05050;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 6px;
}
QPushButton#btn_stop:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4a1010,stop:1 #380808);
    border-color: #a03030;
    color: #ff6060;
}
QPushButton#btn_danger {
    background-color: #2a0a0a;
    border: 1px solid #5a1a1a;
    color: #c04040;
}
QPushButton#btn_danger:hover { background-color: #380d0d; border-color: #8a2a2a; }

QPushButton#btn_gold {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2a2000,stop:1 #1a1400);
    border: 1px solid #705000;
    color: #d0a020;
    font-weight: 700;
}
QPushButton#btn_gold:hover { border-color: #a07820; color: #f0c030; }

/* ─────────────────────────────────────────────────────── INPUTS */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0c0c1e;
    color: #c8c8f0;
    border: 1px solid #222240;
    border-radius: 5px;
    padding: 6px 10px;
    selection-background-color: #e05030;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #504080;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow { width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background-color: #0f0f22;
    border: 1px solid #252545;
    selection-background-color: #1e1e40;
    color: #c0c0e8;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #14142a;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #1e1e3c; }

/* ─────────────────────────────────────────────────────── TABLE */
QTableWidget {
    background-color: #0b0b1c;
    border: 1px solid #1e1e38;
    gridline-color: #141428;
    border-radius: 6px;
    alternate-background-color: #0d0d20;
}
QTableWidget::item { padding: 6px 8px; }
QTableWidget::item:selected {
    background-color: #1a1a38;
    color: #e0e0ff;
}
QHeaderView::section {
    background-color: #0f0f22;
    color: #6070a8;
    font-weight: 700;
    padding: 7px;
    border: none;
    border-right: 1px solid #1a1a30;
    border-bottom: 1px solid #252545;
}
QTableWidget::item:hover { background-color: #141430; }

/* ─────────────────────────────────────────────────────── LABELS */
QLabel { color: #9090c0; }
QLabel#label_title {
    font-size: 18px;
    font-weight: 800;
    color: #e05030;
    letter-spacing: 1px;
}
QLabel#label_section {
    font-size: 12px;
    font-weight: 700;
    color: #4a4a80;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ─────────────────────────────────────────────────────── KPI CARDS */
#kpi_card {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0f0f22,stop:1 #08080f);
    border: 1px solid #202040;
    border-radius: 8px;
    padding: 12px;
}
#kpi_value {
    font-size: 28px;
    font-weight: 900;
    color: #d0a020;
}
#kpi_label {
    font-size: 11px;
    color: #404070;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ─────────────────────────────────────────────────────── GROUP BOX */
QGroupBox {
    border: 1px solid #1e1e38;
    border-radius: 7px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 700;
    color: #505090;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #706090;
}

/* ─────────────────────────────────────────────────────── SCROLLBAR */
QScrollBar:vertical {
    background: #0a0a18;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #252545;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #353565; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 8px; background: #0a0a18; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #252545; border-radius: 4px; min-width: 24px; }

/* ─────────────────────────────────────────────────────── STATUS BAR */
QStatusBar {
    background-color: #07070d;
    color: #404070;
    border-top: 1px solid #141428;
    font-size: 11px;
}

/* ─────────────────────────────────────────────────────── PROGRESS */
QProgressBar {
    background-color: #0c0c1e;
    border: 1px solid #1e1e38;
    border-radius: 4px;
    text-align: center;
    color: #d0a020;
    font-weight: 700;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e05030,stop:1 #d0a020);
    border-radius: 4px;
}

/* ─────────────────────────────────────────────────────── TOOLTIP */
QToolTip {
    background-color: #0f0f22;
    color: #c0c0e8;
    border: 1px solid #404080;
    padding: 5px;
    border-radius: 4px;
}

/* ─────────────────────────────────────────────────────── STATE BADGE */
#badge_running { color: #40d060; font-weight: 800; }
#badge_paused  { color: #d0a020; font-weight: 800; }
#badge_stopped { color: #808090; font-weight: 800; }
#badge_error   { color: #e05050; font-weight: 800; }
"""
