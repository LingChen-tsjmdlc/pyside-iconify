"""Button and list-item states: hover color, selected color, disabled.

Hover and selected colors are opt-in. Without them an icon behaves like a plain
QIcon. Needs network (the icons are fetched from the Iconify API).

Run: uv run examples/button_states.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _common import add_controls
from _i18n import bind
from pyside_iconify import get_icon, set_icon


def build_window() -> QWidget:
    """创建示例窗口。"""
    window = QWidget()
    bind(window.setWindowTitle, "Button and item states", "按钮与列表项状态")
    layout = QVBoxLayout(window)

    plain_group = QGroupBox()
    bind(
        plain_group.setTitle,
        "No hover_color: icon stays the same (background hover is done with QSS)",
        "不写 hover_color：图标不变色（背景悬停效果用 QSS 实现）",
    )
    plain_layout = QHBoxLayout(plain_group)
    for name in ["mdi:home", "mdi:account", "mdi:cog", "mdi:star"]:
        button = QPushButton(name)
        set_icon(button, name, size=20)
        plain_layout.addWidget(button)
    layout.addWidget(plain_group)

    hover_group = QGroupBox()
    bind(
        hover_group.setTitle,
        "hover_color enables hover recoloring (separate light/dark values)",
        "写 hover_color 才启用悬停变色（可分别指定亮暗主题）",
    )
    hover_layout = QHBoxLayout(hover_group)
    for name in ["mdi:heart", "mdi:bell", "mdi:email"]:
        button = QPushButton(name)
        set_icon(
            button,
            name,
            size=20,
            hover_color_light_theme="#0969da",
            hover_color_dark_theme="#58a6ff",
        )
        hover_layout.addWidget(button)
    layout.addWidget(hover_group)

    selected_group = QGroupBox()
    bind(
        selected_group.setTitle,
        "selected_color on list items (click a row)",
        "列表项 selected_color（点选某一行查看效果）",
    )
    selected_layout = QVBoxLayout(selected_group)
    list_widget = QListWidget()
    for name in ["mdi:home", "mdi:account", "mdi:cog"]:
        item = QListWidgetItem(name)
        item.setIcon(
            get_icon(
                name,
                size=16,
                selected_color_light_theme="#0969da",
                selected_color_dark_theme="#58a6ff",
            )
        )
        list_widget.addItem(item)
    selected_layout.addWidget(list_widget)
    layout.addWidget(selected_group)

    disabled_group = QGroupBox()
    bind(
        disabled_group.setTitle,
        "Disabled: icon fades; hover settings are ignored",
        "禁用：图标变淡；悬停参数对禁用状态无效",
    )
    disabled_layout = QHBoxLayout(disabled_group)
    disabled_button = QPushButton()
    bind(disabled_button.setText, "Disabled button", "禁用按钮")
    set_icon(disabled_button, "mdi:cog", size=20, hover_color="#d1242f")
    disabled_button.setEnabled(False)
    disabled_layout.addWidget(disabled_button)
    layout.addWidget(disabled_group)

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
