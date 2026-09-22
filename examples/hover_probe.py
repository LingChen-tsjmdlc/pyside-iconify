"""hover 诊断探针（事件驱动版）：验证按钮悬停换图是否生效。

用法：uv run examples/hover_probe.py
把鼠标移到按钮上再移开，看控制台输出和按钮图标颜色变化。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QSize, QObject
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyside_iconify import add_collection, set_icon
from pyside_iconify.rendering.engine import IconEngine

_ORIG_SCALED = IconEngine.scaledPixmap


def _spy_scaled(self, size, mode, state, scale):
    pixmap = _ORIG_SCALED(self, size, mode, state, scale)
    image = pixmap.toImage()
    color = image.pixelColor(image.width() // 2, image.height() // 2).name()
    print(
        f"[引擎] state_mode={self._state_mode}  渲染颜色={color}",
        flush=True,
    )
    return pixmap


class HoverLogger(QObject):
    """打印按钮的 Enter/Leave 事件。"""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            print("[事件] 鼠标进入按钮", flush=True)
        elif event.type() == QEvent.Type.Leave:
            print("[事件] 鼠标离开按钮", flush=True)
        return False


def main() -> int:
    app = QApplication(sys.argv)
    IconEngine.scaledPixmap = _spy_scaled  # 观察每次渲染的状态与颜色
    add_collection(
        {
            "prefix": "app",
            "width": 24,
            "height": 24,
            "icons": {
                "home": {
                    "body": '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>'
                }
            },
        }
    )
    window = QWidget()
    window.setWindowTitle("hover 诊断探针（事件驱动）")
    window.resize(320, 120)
    layout = QVBoxLayout(window)
    button = QPushButton("把鼠标移到我上面 / 移开")

    # 库的 set_icon：自动装悬停 watcher + 自动强调
    set_icon(button, "app:home", size=20)
    button.setIconSize(QSize(20, 20))
    button.installEventFilter(HoverLogger(button))
    layout.addWidget(button)
    window.show()
    print(
        "鼠标移入/移出按钮。预期：Enter 后渲染颜色与 Leave 后不同。"
        "关闭窗口结束。",
        flush=True,
    )
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
