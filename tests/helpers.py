"""测试中的 Qt 绘制辅助函数。"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication, QWidget


def show_widget(
    qtbot: object, widget: QWidget, width: int = 24, height: int = 24
) -> QWidget:
    """显示顶层控件，以便抓取稳定的渲染结果。

    移出 (0,0)：offscreen 平台鼠标位于原点，控件盖在鼠标上会进入悬停态。
    """
    widget.resize(width, height)
    widget.move(400, 400)
    qtbot.addWidget(widget)
    widget.show()
    QApplication.processEvents()
    return widget


def widget_color(widget: QWidget, x: int, y: int) -> QColor:
    """读取控件截图中的像素颜色。"""
    QApplication.processEvents()
    return widget.grab().toImage().pixelColor(x, y)


def icon_color(
    icon: QIcon,
    x: int = 12,
    y: int = 12,
    mode: QIcon.Mode = QIcon.Mode.Normal,
) -> QColor:
    """读取标准 QIcon 的 24 像素位图颜色。"""
    return icon.pixmap(QSize(24, 24), mode).toImage().pixelColor(x, y)


def assert_color(color: QColor, expected: str) -> None:
    """断言颜色名称匹配。"""
    assert color.name() == expected
