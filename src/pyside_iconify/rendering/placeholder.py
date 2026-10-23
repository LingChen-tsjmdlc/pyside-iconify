"""内置占位图绘制。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap


def create_blank(width: int, height: int, device_pixel_ratio: float) -> QPixmap:
    """创建透明空白位图。

    Args:
        width: 逻辑宽度
        height: 逻辑高度
        device_pixel_ratio: 设备像素比；物理尺寸为逻辑尺寸乘以该值并取整，至少 1 像素

    Returns:
        已填充透明色的 QPixmap。
    """
    pixmap = QPixmap(
        max(1, round(width * device_pixel_ratio)),
        max(1, round(height * device_pixel_ratio)),
    )
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    return pixmap


def create_placeholder(width: int, height: int, device_pixel_ratio: float) -> QPixmap:
    """创建不依赖图标集合的问号占位图。

    Args:
        width: 逻辑宽度
        height: 逻辑高度
        device_pixel_ratio: 设备像素比；物理尺寸为逻辑尺寸乘以该值并取整，至少 1 像素

    Returns:
        绘有圆角边框和问号的 QPixmap。
    """
    physical_width = max(1, round(width * device_pixel_ratio))
    physical_height = max(1, round(height * device_pixel_ratio))
    pixmap = QPixmap(physical_width, physical_height)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#8a8f98")
    pen = QPen(color)
    pen.setWidthF(max(1.0, min(width, height) / 12))
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    margin = min(width, height) * 0.13
    rect = QRectF(margin, margin, width - margin * 2, height - margin * 2)
    painter.drawRoundedRect(rect, min(width, height) * 0.14, min(width, height) * 0.14)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return pixmap
