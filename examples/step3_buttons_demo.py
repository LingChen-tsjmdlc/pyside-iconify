"""Step 3 示例三：按钮图标与悬停/选中变色（联网运行）。"""

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

from _theme import is_dark, set_theme

from pyside_iconify import get_icon, set_icon


def build_window() -> QWidget:
    """创建示例窗口。"""
    window = QWidget()
    window.setWindowTitle("Step 3 · 按钮图标与悬停变色")
    layout = QVBoxLayout(window)

    hover_group = QGroupBox(
        "悬停反馈：背景变化用 QSS（标准做法）；图标变色是可选的额外效果"
    )
    hover_layout = QHBoxLayout(hover_group)
    for name in ["mdi:home", "mdi:account", "mdi:cog", "mdi:star"]:
        button = QPushButton(name)
        set_icon(button, name, size=20)  # 不写 hover_color：图标不变色
        hover_layout.addWidget(button)
    layout.addWidget(hover_group)

    explicit_group = QGroupBox("悬停：写 hover_color 才启用（支持亮暗主题分别指定）")
    explicit_layout = QHBoxLayout(explicit_group)
    for name in ["mdi:heart", "mdi:bell", "mdi:email"]:
        button = QPushButton(name)
        set_icon(
            button,
            name,
            size=20,
            hover_color_light_theme="#0969da",
            hover_color_dark_theme="#58a6ff",
        )
        explicit_layout.addWidget(button)
    layout.addWidget(explicit_group)

    selected_group = QGroupBox("选中：列表项 selected_color（点选列表行看效果）")
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

    disabled_group = QGroupBox("禁用：图标变淡；悬停参数对禁用状态无效（禁用优先）")
    disabled_layout = QHBoxLayout(disabled_group)
    button = QPushButton("禁用按钮")
    set_icon(button, "mdi:cog", size=20, hover_color="#d1242f")
    button.setEnabled(False)
    disabled_layout.addWidget(button)
    layout.addWidget(disabled_group)

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
