"""Step 3 示例一：本地图标 + set_icon 各类目标。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _theme import is_dark, set_theme

from pyside_iconify import add_collection, set_icon

ICONS = {
    "prefix": "app",
    "width": 24,
    "height": 24,
    "icons": {
        "home": {"body": '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>'},
        "file": {"body": '<path d="M6 2h9l5 5v15H6zM14 2v6h6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'},
        "star": {"body": '<path d="M12 2l2.9 6.26L21.5 9.3l-4.75 4.4 1.15 6.6L12 17.2l-5.9 3.1 1.15-6.6L2.5 9.3l6.6-1.04z" fill="currentColor"/>'},
        "gear": {"body": '<circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'},
    },
}


def build_window() -> QWidget:
    """创建示例窗口。"""
    add_collection(ICONS)

    window = QWidget()
    window.setWindowTitle("Step 3 · 本地图标与 set_icon")
    layout = QVBoxLayout(window)

    buttons = QGroupBox("按钮与 QAction（set_icon）")
    buttons_layout = QVBoxLayout(buttons)
    save = QPushButton("保存（未写 hover_color，悬停无效果）")
    set_icon(save, "app:home", size=20)
    star = QPushButton("显式 hover_color")
    set_icon(star, "app:star", size=20, color="#57606a", hover_color="#d1242f")
    buttons_layout.addWidget(save)
    buttons_layout.addWidget(star)
    layout.addWidget(buttons)

    tabs = QGroupBox("标签页（set_icon(tabs, name, index)）")
    tabs_layout = QVBoxLayout(tabs)
    tab_widget = QTabWidget()
    for index, name in enumerate(["app:home", "app:file", "app:gear"]):
        tab_widget.addTab(QWidget(), name)
        set_icon(tab_widget, name, index, size=18)
    tabs_layout.addWidget(tab_widget)
    layout.addWidget(tabs)

    lists = QGroupBox("列表与树（下载/主题变化自动刷新）")
    lists_layout = QVBoxLayout(lists)
    list_widget = QListWidget()
    icon_names = [f"app:{key}" for key in ICONS["icons"]]
    for row in range(6):
        item = QListWidgetItem(f"条目 {row}")
        set_icon(item, icon_names[row % len(icon_names)], size=16)
        list_widget.addItem(item)
    tree = QTreeWidget()
    for row in range(4):
        node = QTreeWidgetItem(tree, [f"节点 {row}"])
        set_icon(node, icon_names[row], size=16)
    lists_layout.addWidget(list_widget)
    lists_layout.addWidget(tree)
    layout.addWidget(lists)

    theme_button = QPushButton("切换亮暗主题")
    layout.addWidget(theme_button)
    theme_button.clicked.connect(lambda: set_theme(window, not is_dark()))
    set_theme(window, False)
    return window


def main() -> int:
    """运行示例。"""
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
