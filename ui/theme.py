"""A single Qt style sheet for a clean, modern look."""

from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"

# A calm light theme with a teal accent. Kept in one place so the whole app
# shares one visual language.
def get_stylesheet() -> str:
    arrow_path = (_ASSETS / "arrow_down.svg").as_posix()
    return _STYLESHEET_TEMPLATE.replace("__ARROW_PATH__", arrow_path)


_STYLESHEET_TEMPLATE = """
* {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: #1f2933;
}

QMainWindow, QWidget {
    background-color: #f4f6f8;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #dce1e6;
    border-radius: 8px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: #e9edf1;
    color: #52606d;
    padding: 9px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0b7285;
    border: 1px solid #dce1e6;
    border-bottom: 2px solid #ffffff;
}
QTabBar::tab:hover:!selected {
    background: #dfe6eb;
}

/* Group boxes */
QGroupBox {
    background: #ffffff;
    border: 1px solid #dce1e6;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
    font-weight: 700;
    color: #323f4b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #0b7285;
}

/* Inputs */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #cbd2d9;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #63c7d6;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0b7285;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #cbd2d9;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background: #eef1f4;
}
QComboBox::drop-down:hover {
    background: #dfe6eb;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
    image: url("__ARROW_PATH__");
}
QComboBox::down-arrow:hover, QComboBox:on::down-arrow {
    image: url("__ARROW_PATH__");
}

/* Buttons */
QPushButton {
    background: #e4e9ed;
    border: 1px solid #cbd2d9;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    color: #323f4b;
}
QPushButton:hover { background: #d6dde2; }
QPushButton:pressed { background: #c3ccd3; }
QPushButton:disabled { color: #9aa5b1; background: #eef1f4; }

QPushButton#primary {
    background: #0b7285;
    color: #ffffff;
    border: none;
    padding: 10px 20px;
    font-size: 14px;
}
QPushButton#primary:hover { background: #0a6273; }
QPushButton#primary:pressed { background: #085261; }
QPushButton#primary:disabled { background: #9fbcc2; }

QPushButton#danger {
    background: #ffffff;
    color: #c0392b;
    border: 1px solid #e0a9a2;
}
QPushButton#danger:hover { background: #fbeae8; }

/* Progress bar */
QProgressBar {
    border: 1px solid #cbd2d9;
    border-radius: 6px;
    background: #eef1f4;
    text-align: center;
    height: 20px;
    color: #323f4b;
}
QProgressBar::chunk {
    background-color: #0b7285;
    border-radius: 5px;
}

/* Log console */
QPlainTextEdit {
    background: #0f1720;
    color: #cbd5e1;
    border: 1px solid #1f2933;
    border-radius: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    padding: 8px;
}

/* Checkboxes */
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid #cbd2d9;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #0b7285;
    border: 1px solid #0b7285;
    image: none;
}

/* Status bar */
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #dce1e6;
    color: #52606d;
}

QScrollArea { border: none; background: transparent; }
QLabel#hint { color: #7b8794; font-weight: 400; }
"""
