"""列表滚动与图标选择器性能演示。

数量可调、实时重建，滚动时右侧显示当前/平均帧率。
运行：uv run tests/benchmark/list_scroll.py
"""

from __future__ import annotations

import sys
import time
from collections import deque

from PySide6.QtCore import QEvent, Qt, QTimer, QObject
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyside_iconify import IconWidget, add_collection, get_icon

ROW_ICONS = ["bench:home", "bench:account", "bench:cog", "bench:star",
             "bench:heart", "bench:bell", "bench:search", "bench:trash"]
BUTTON_COLORS = ["#d1242f", "#0969da", "#1a7f37", "#8250df", "#bf8700", "#57606a"]
WINDOW_MS = 1000  # 当前帧率的统计窗口


class FpsMeter(QObject):
    """渲染帧率表：持续渲染循环驱动，Paint 计数受屏幕刷新率节流。

    静止时 ≈ 显示器刷新率；滚动时若掉帧即为滚动开销。本工具
    常驻满帧渲染是设计使然（性能测试工具），非节能场景。
    """

    def __init__(self, label: QLabel) -> None:
        super().__init__(label)
        self._label = label
        self._stamps: deque[float] = deque()
        self._total = 0
        self._t0: float | None = None

    def watch(self, target: QWidget) -> None:
        """开始监听 target 的绘制，并以渲染泵保持其持续重绘。

        监听对象必须是真正执行绘制的控件：QListWidget 用它的
        viewport；QScrollArea 的内容页用 setWidget 进去的 host
        （内容画在子控件上，viewport 上几乎看不到 Paint）。
        """
        target.installEventFilter(self)
        pump = QTimer(target)
        pump.setTimerType(Qt.TimerType.PreciseTimer)
        pump.timeout.connect(target.update)
        pump.start(0)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Paint:
            self.tick()
        return False

    def tick(self) -> None:
        now = time.perf_counter()
        if self._t0 is None:
            self._t0 = now
        self._total += 1
        self._stamps.append(now)
        cutoff = now - WINDOW_MS / 1000
        while self._stamps and self._stamps[0] < cutoff:
            self._stamps.popleft()
        current = len(self._stamps) * 1000 / WINDOW_MS
        average = self._total / max(now - self._t0, 1e-6)
        self._label.setText(f"当前 {current:4.0f} FPS · 平均 {average:4.0f} FPS")

    def reset(self) -> None:
        self._stamps.clear()
        self._total = 0
        self._t0 = None


def register_bench_icons() -> None:
    """注册演示用的离线图标。"""
    bodies = [
        '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>',
        '<circle cx="12" cy="8" r="4" fill="currentColor"/><path d="M4 20c0-3 4-5 8-5s8 2 8 5v1H4z" fill="currentColor"/>',
        '<path d="M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8m8.94 5.41-.81 1.63.28 2.05-1.88.66-1.09 1.75-2.02-.4-1.78 1.05L12 21l-1.64 1.15-1.78-1.05-2.02.4-1.09-1.75-1.88-.66.28-2.05-.81-1.63 1.31-1.6L3.02 9.6l1.53-1.37.53-2 1.99-.33L8.87 4.2 10.8 5l1.2-1.8 1.2 1.8 1.93-.8.8 1.7 1.99.33.53 2 1.53 1.37-.59 2.02z" fill="currentColor"/>',
        '<path d="M12 2l2.9 6.26L21.5 9.3l-4.75 4.4 1.15 6.6L12 17.2l-5.9 3.1 1.15-6.6L2.5 9.3l6.6-1.04z" fill="currentColor"/>',
        '<path d="M12 21s-8-5.5-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 5.5-8 11-8 11z" fill="currentColor"/>',
        '<path d="M12 3a1 1 0 0 1 1 1v2h3.2l3.3 5.8-4.2 2.4.9 1.6L22 11 17.6 3H13a1 1 0 0 1-1-1z" fill="currentColor"/><path d="M5 7h6v10H5z" fill="currentColor"/>',
        '<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16.5 16.5L21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
        '<path d="M9 3h6l1 3h3v14H5V6h3zM8 10h8M8 14h8" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    ]
    for icon_name, body in zip(ROW_ICONS, bodies):
        add_collection(
            {
                "prefix": "bench",
                "width": 24,
                "height": 24,
                "icons": {icon_name.split(":")[1]: {"body": body}},
            },
            replace=True,
        )


def build_list_tab() -> QWidget:
    """列表滚动页：行数可调，实时重建，滚动测帧率。"""
    root = QWidget()
    layout = QVBoxLayout(root)

    controls = QHBoxLayout()
    controls.addWidget(QLabel("行数"))
    rows_box = QSpinBox()
    rows_box.setRange(100, 20000)
    rows_box.setValue(1000)
    rows_box.setSingleStep(500)
    build_button = QPushButton("重建列表")
    elapsed = QLabel("—")
    fps_label = QLabel("当前 — FPS · 平均 — FPS")
    controls.addWidget(rows_box)
    controls.addWidget(build_button)
    controls.addWidget(elapsed)
    controls.addStretch()
    controls.addWidget(fps_label)
    layout.addLayout(controls)

    list_widget = QListWidget()
    layout.addWidget(list_widget)
    meter = FpsMeter(fps_label)
    meter.watch(list_widget.viewport())

    def rebuild() -> None:
        rows = rows_box.value()
        start = time.perf_counter()
        list_widget.clear()
        for row in range(rows):
            item = QListWidgetItem(f"行 {row}")
            item.setIcon(
                get_icon(
                    ROW_ICONS[row % len(ROW_ICONS)],
                    size=16,
                    color=BUTTON_COLORS[row % len(BUTTON_COLORS)],
                )
            )
            list_widget.addItem(item)
        cost = (time.perf_counter() - start) * 1000
        elapsed.setText(f"{rows} 行构建耗时 {cost:.0f} ms")
        meter.reset()

    build_button.clicked.connect(rebuild)
    rows_box.editingFinished.connect(rebuild)
    rebuild()
    return root


def build_sheet_tab() -> QWidget:
    """图标选择器页：网格规模可调，实时重建，滚动测帧率。

    注意：此页的渲染泵每帧强制全视口重绘（测屏幕帧率用），
    成本正比于可见图标数——这比真实应用严苛。真实应用没有
    渲染泵：静止零成本，滚动走位块搬移只重绘新暴露的行
    （实测 2400 图标网格 2.9ms/步）。大规模网格的推荐形态
    是 item view + get_icon（见列表滚动页）。
    """
    root = QWidget()
    layout = QVBoxLayout(root)

    controls = QHBoxLayout()
    controls.addWidget(QLabel("列数"))
    columns_box = QSpinBox()
    columns_box.setRange(4, 60)
    columns_box.setValue(16)
    controls.addWidget(columns_box)
    controls.addWidget(QLabel("行数"))
    rows_box = QSpinBox()
    rows_box.setRange(4, 200)
    rows_box.setValue(30)
    build_button = QPushButton("重建选择器")
    elapsed = QLabel("—")
    fps_label = QLabel("当前 — FPS · 平均 — FPS")
    controls.addWidget(rows_box)
    controls.addWidget(build_button)
    controls.addWidget(elapsed)
    controls.addStretch()
    controls.addWidget(fps_label)
    layout.addLayout(controls)

    area = QScrollArea()
    area.setWidgetResizable(True)
    layout.addWidget(area)
    meter = FpsMeter(fps_label)

    def rebuild() -> None:
        columns, rows = columns_box.value(), rows_box.value()
        start = time.perf_counter()
        host = QWidget()
        grid = QGridLayout(host)
        grid.setSpacing(4)
        index = 0
        for row in range(rows):
            for column in range(columns):
                grid.addWidget(
                    IconWidget(
                        ROW_ICONS[index % len(ROW_ICONS)],
                        size=32,
                        color=BUTTON_COLORS[index % len(BUTTON_COLORS)],
                    ),
                    row,
                    column,
                )
                index += 1
        area.setWidget(host)
        meter.watch(host)
        cost = (time.perf_counter() - start) * 1000
        count = columns * rows
        elapsed.setText(f"{count} 个图标构建耗时 {cost:.0f} ms")
        meter.reset()

    build_button.clicked.connect(rebuild)
    columns_box.valueChanged.connect(rebuild)
    rows_box.valueChanged.connect(rebuild)
    rebuild()
    return root


def main() -> int:
    """运行性能演示窗口。"""
    app = QApplication(sys.argv)
    register_bench_icons()

    window = QWidget()
    window.setWindowTitle("性能演示 · 列表滚动 / 图标选择器")
    window.resize(560, 640)
    root = QVBoxLayout(window)
    tabs = QTabWidget()
    tabs.addTab(build_list_tab(), "列表滚动")
    tabs.addTab(build_sheet_tab(), "图标选择器")
    root.addWidget(tabs)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
