"""Long-run memory soak: rebuild lists and grids in a loop.

Run for at least 30 minutes before a release; RSS must not grow without
bound. Python-side allocations are reported via tracemalloc; check the
process RSS in Task Manager / Activity Monitor for the full picture
including Qt-native allocations.

Usage: uv run benchmarks/memory_soak.py [--minutes 30]
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
import tracemalloc

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyside_iconify import IconWidget, add_collection, get_icon

ICONS = ["soak:home", "soak:account", "soak:cog", "soak:star"]
COLORS = ["#d1242f", "#0969da", "#1a7f37", "#8250df", "#bf8700", "#57606a"]


def register_icons() -> None:
    add_collection(
        {
            "prefix": "soak",
            "width": 24,
            "height": 24,
            "icons": {
                "home": {"body": '<rect width="24" height="24" fill="currentColor"/>'},
                "account": {"body": '<circle cx="12" cy="12" r="10" fill="currentColor"/>'},
                "cog": {"body": '<circle cx="12" cy="12" r="5" fill="currentColor"/>'},
                "star": {"body": '<path d="M12 2l3 7h7l-5.5 4.5L19 21l-7-4-7 4 2.5-7.5L2 9h7z" fill="currentColor"/>'},
            },
        },
        replace=True,
    )


def build_tabs() -> tuple[QListWidget, QScrollArea]:
    list_widget = QListWidget()
    for row in range(500):
        item = QListWidgetItem(f"row {row}")
        item.setIcon(get_icon(ICONS[row % 4], size=16, color=COLORS[row % 6]))
        list_widget.addItem(item)

    host = QWidget()
    grid = QGridLayout(host)
    for i in range(600):
        grid.addWidget(
            IconWidget(ICONS[i % 4], size=32, color=COLORS[i % 6]),
            i // 25,
            i % 25,
        )
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(host)
    return list_widget, area


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=30)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    register_icons()
    tracemalloc.start()

    window = QWidget()
    window.setWindowTitle("memory soak")
    window.resize(800, 600)
    layout = QVBoxLayout(window)
    tabs = QTabWidget()
    layout.addWidget(tabs)
    window.show()

    deadline = time.monotonic() + args.minutes * 60
    cycles = 0
    while time.monotonic() < deadline:
        list_widget, area = build_tabs()
        # clear() 只移除页面、不删除页面 widget；必须显式销毁，
        # 否则旧列表/网格整链（host + 全部子控件）成为孤儿持续累积。
        while tabs.count():
            page = tabs.widget(0)
            tabs.removeTab(0)
            page.deleteLater()
        tabs.addTab(list_widget, "list")
        tabs.addTab(area, "grid")
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()
        cycles += 1
        if cycles % 5 == 0:
            current, peak = tracemalloc.get_traced_memory()
            print(
                f"cycle {cycles}: python current={current / 1e6:.1f} MB, "
                f"peak={peak / 1e6:.1f} MB",
                flush=True,
            )

    current, peak = tracemalloc.get_traced_memory()
    print(f"done after {cycles} cycles: current={current / 1e6:.1f} MB, "
          f"peak={peak / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
