"""set_icon on different targets, using locally registered icons (no network).

Covers push buttons, tab pages, list items and tree nodes. Anything else with a
setIcon works through get_icon; see the README.

Run: uv run examples/set_icon_targets.py
"""

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

from _common import add_controls
from _i18n import bind, on_change, t
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
    bind(window.setWindowTitle, "set_icon targets", "set_icon 的各类目标")
    layout = QVBoxLayout(window)

    buttons = QGroupBox()
    bind(buttons.setTitle, "Push buttons", "按钮")
    buttons_layout = QVBoxLayout(buttons)
    plain = QPushButton()
    bind(plain.setText, "Save (no hover_color: no hover effect)", "保存（未写 hover_color，悬停无效果）")
    set_icon(plain, "app:home", size=20)
    hover = QPushButton()
    bind(hover.setText, "With hover_color", "显式 hover_color")
    set_icon(hover, "app:star", size=20, color="#57606a", hover_color="#d1242f")
    buttons_layout.addWidget(plain)
    buttons_layout.addWidget(hover)
    layout.addWidget(buttons)

    tabs = QGroupBox()
    bind(tabs.setTitle, "Tab pages: set_icon(tabs, name, index)", "标签页：set_icon(tabs, name, index)")
    tabs_layout = QVBoxLayout(tabs)
    tab_widget = QTabWidget()
    for index, name in enumerate(["app:home", "app:file", "app:gear"]):
        tab_widget.addTab(QWidget(), name)
        set_icon(tab_widget, name, index, size=18)
    tabs_layout.addWidget(tab_widget)
    layout.addWidget(tabs)

    lists = QGroupBox()
    bind(
        lists.setTitle,
        "Lists and trees (refresh on download and theme change)",
        "列表与树（下载或主题变化时自动刷新）",
    )
    lists_layout = QVBoxLayout(lists)
    icon_names = [f"app:{key}" for key in ICONS["icons"]]
    list_widget = QListWidget()
    items: list[tuple[QListWidgetItem, int]] = []
    for row in range(6):
        item = QListWidgetItem()
        set_icon(item, icon_names[row % len(icon_names)], size=16)
        list_widget.addItem(item)
        items.append((item, row))
    tree = QTreeWidget()
    nodes: list[tuple[QTreeWidgetItem, int]] = []
    for row in range(4):
        node = QTreeWidgetItem(tree)
        set_icon(node, icon_names[row], size=16)
        nodes.append((node, row))

    def refresh_rows() -> None:
        """按当前语言刷新列表项与树节点文字。"""
        for item, row in items:
            item.setText(t("Item {row}", "条目 {row}", row=row))
        for node, row in nodes:
            node.setText(0, t("Node {row}", "节点 {row}", row=row))

    on_change(refresh_rows)
    lists_layout.addWidget(list_widget)
    lists_layout.addWidget(tree)
    layout.addWidget(lists)

    add_controls(window, layout)
    return window


def main() -> int:
    """运行示例。"""
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
