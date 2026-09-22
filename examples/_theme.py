"""示例共用的亮暗主题切换。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

STYLE = """
QWidget { background: palette(window); color: palette(window-text); }
QPushButton { padding: 6px 10px; }
QPushButton:hover { background: palette(mid); }
QPushButton:disabled { color: palette(mid); }
QGroupBox { border: 1px solid palette(mid); border-radius: 6px; margin-top: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: palette(mid); }
QListWidget, QTreeWidget { background: palette(base); color: palette(window-text); }
QLabel { background: transparent; }
"""


def set_theme(window: QWidget, dark: bool) -> None:
    """切换应用亮暗主题。"""
    palette = QPalette()
    if dark:
        palette.setColor(QPalette.ColorRole.Window, QColor("#1d2128"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#161b22"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#2b313a"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6edf3"))
        palette.setColor(QPalette.ColorRole.Mid, QColor("#9da7b3"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#378add"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#e6edf3"))
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor("#f6f8fa"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#20242b"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#20242b"))
        palette.setColor(QPalette.ColorRole.Mid, QColor("#57606a"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#378add"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    QApplication.setPalette(palette)
    window.setStyleSheet(STYLE)


def is_dark() -> bool:
    """当前是否暗色主题。"""
    return (
        QApplication.palette()
        .color(QPalette.ColorRole.Window)
        .lightness()
        < 128
    )
