"""Step 3 示例二：异步加载大列表（联网运行）。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _theme import is_dark, set_theme

from pyside_iconify import IconWidget, set_icon
from pyside_iconify.network import load_icons

ICON_NAMES = [
    "mdi:home", "mdi:account", "mdi:cog", "mdi:star", "mdi:heart",
    "mdi:bell", "mdi:search", "mdi:trash", "mdi:email", "mdi:bookmark",
    "mdi:calendar", "mdi:cart", "mdi:chat", "mdi:cloud", "mdi:database",
]


def main() -> int:
    """运行示例。"""
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("Step 3 · 异步加载")
    window.setMinimumSize(420, 500)
    layout = QVBoxLayout(window)

    status = QLabel("先启动，图标在后台下载，完成后自动出现在列表里。")
    status.setStyleSheet("color: palette(mid);")
    layout.addWidget(status)

    list_widget = QListWidget()
    for row in range(300):
        name = ICON_NAMES[row % len(ICON_NAMES)]
        item = QListWidgetItem(f"{name} · 行 {row}")
        set_icon(item, name, size=16)
        list_widget.addItem(item)
    layout.addWidget(list_widget)

    spinner = IconWidget("mdi:loading", size=20, spin=True)
    layout.addWidget(spinner)

    theme_button = QPushButton("切换亮暗主题")
    layout.addWidget(theme_button)
    theme_button.clicked.connect(lambda: set_theme(window, not is_dark()))
    set_theme(window, False)

    # 预加载首批图标并汇报结果
    request = load_icons(
        ICON_NAMES[:5],
        on_finished=lambda results: status.setText(
            "首批预加载完成：" + "，".join(sorted(results))
        ),
    )
    request.finished.connect(
        lambda results: status.setText(
            status.text()
            + f"；成功 {sum(1 for e in results.values() if e is None)} 个"
        )
    )

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
