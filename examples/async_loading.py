"""Async loading: a long list whose icons download in the background.

Icons are not registered locally, so each one is fetched from the Iconify API on
first use and the list repaints by itself when the data arrives. Needs network.

Run: uv run examples/async_loading.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _common import add_controls
from _i18n import bind, on_change, t
from pyside_iconify import IconWidget, set_icon
from pyside_iconify.network import load_icons

ICON_NAMES = [
    "mdi:home", "mdi:account", "mdi:cog", "mdi:star", "mdi:heart",
    "mdi:bell", "mdi:magnify", "mdi:trash-can", "mdi:email", "mdi:bookmark",
    "mdi:calendar", "mdi:cart", "mdi:chat", "mdi:cloud", "mdi:database",
]


def main() -> int:
    """运行示例。"""
    app = QApplication(sys.argv)
    window = QWidget()
    window.setMinimumSize(420, 500)
    bind(window.setWindowTitle, "Async loading", "异步加载")
    layout = QVBoxLayout(window)

    status = QLabel()
    status.setStyleSheet("color: palette(mid);")
    loaded_names: list[str] | None = None
    ok_count = 0

    def refresh_status() -> None:
        """按预加载状态刷新提示文字。"""
        if loaded_names is None:
            status.setText(
                t(
                    "Start first; icons download in the background and appear in the list.",
                    "先启动，图标在后台下载，完成后自动出现在列表里。",
                )
            )
            return
        status.setText(
            t(
                "First batch ready: {names}; {ok} succeeded",
                "首批预加载完成：{names}；成功 {ok} 个",
                names=", ".join(loaded_names),
                ok=ok_count,
            )
        )

    on_change(refresh_status)
    layout.addWidget(status)

    list_widget = QListWidget()
    rows: list[tuple[QListWidgetItem, str, int]] = []
    for row in range(300):
        name = ICON_NAMES[row % len(ICON_NAMES)]
        item = QListWidgetItem()
        set_icon(item, name, size=16)
        list_widget.addItem(item)
        rows.append((item, name, row))

    def refresh_rows() -> None:
        """按当前语言刷新列表行文字。"""
        for item, name, row in rows:
            item.setText(t("{name} - row {row}", "{name} · 行 {row}", name=name, row=row))

    on_change(refresh_rows)
    layout.addWidget(list_widget)
    layout.addWidget(IconWidget("mdi:loading", size=20, spin=True))
    add_controls(window, layout)

    def on_finished(results: dict[str, object]) -> None:
        """预加载结束后记录结果并刷新提示。

        Args:
            results: 图标名到错误的映射，None 表示成功。
        """
        nonlocal loaded_names, ok_count
        loaded_names = sorted(results)
        ok_count = sum(1 for error in results.values() if error is None)
        refresh_status()

    load_icons(ICON_NAMES[:5], on_finished=on_finished)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
