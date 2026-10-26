"""SVG 到高分屏位图的渲染。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from pyside_iconify._errors import UnsupportedSvgError
from pyside_iconify.core.svg import build_svg
from pyside_iconify.core.types import IconData, RGBA
from pyside_iconify.rendering.cache import pixmap_cache, svg_cache
from pyside_iconify.rendering.motion import STATIC_FRAME, AnimationFrame


def render_pixmap(
    *,
    cache_key: str,
    data: IconData,
    width: float,
    height: float,
    device_pixel_ratio: float,
    color: RGBA | None,
    colors: Mapping[object, RGBA] | None,
    opacity: float,
    rotate: float,
    h_flip: bool = False,
    v_flip: bool = False,
    stable_scale: bool = False,
    rotate_overflow: bool = False,
    frame: AnimationFrame = STATIC_FRAME,
) -> QPixmap:
    """渲染并缓存指定参数的 SVG 位图。

    命中位图缓存时直接返回；否则生成 SVG、绘制后写入缓存。

    Args:
        cache_key: 位图缓存键
        data: 图标数据
        width: 逻辑宽度
        height: 逻辑高度
        device_pixel_ratio: 设备像素比；物理尺寸为逻辑尺寸乘以该值并取整，至少 1 像素
        color: 单色；None 表示不替换颜色
        colors: 颜色映射表；None 表示不使用
        opacity: 不透明度；超出 0 到 1 时会被截断
        rotate: 旋转角度，单位为度
        h_flip: 是否在图标数据自带翻转基础上再水平翻转
        v_flip: 是否在图标数据自带翻转基础上再垂直翻转
        stable_scale: 为 True 时按 45 度旋转计算缩放，使旋转过程中大小不变
        rotate_overflow: 为 True 时不随旋转角度缩小，保持不旋转时的大小；
            旋转后超出画布的部分会被裁掉。优先于 stable_scale
        frame: 动画取值；只用其中的 scale、offset_y、ghost_scale、ghost_opacity，
            旋转和不透明度已由调用方折算进 rotate、opacity。默认为静止

    Returns:
        设置了设备像素比的 QPixmap。

    Raises:
        UnsupportedSvgError: Qt 无法解析生成的 SVG。
    """
    cached = pixmap_cache.get(cache_key)
    if cached is not None:
        return cached
    transformed_data = replace(
        data, h_flip=data.h_flip ^ h_flip, v_flip=data.v_flip ^ v_flip
    )
    svg_material = repr(
        (transformed_data, color, tuple(sorted((colors or {}).items(), key=repr)))
    )
    svg_key = sha256(svg_material.encode("utf-8")).hexdigest()
    svg = svg_cache.get(svg_key)
    if svg is None:
        svg = build_svg(transformed_data, color=color, colors=colors)
        svg_cache.put(svg_key, svg)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise UnsupportedSvgError("Qt cannot parse the SVG")
    physical_width = max(1, round(width * device_pixel_ratio))
    physical_height = max(1, round(height * device_pixel_ratio))
    image = QImage(
        physical_width, physical_height, QImage.Format.Format_ARGB32_Premultiplied
    )
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setOpacity(max(0.0, min(1.0, opacity)))
    _render_rotated(
        painter,
        renderer,
        physical_width,
        physical_height,
        transformed_data.width,
        transformed_data.height,
        rotate,
        stable_scale,
        rotate_overflow,
        frame,
    )
    painter.end()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    pixmap_cache.put(cache_key, pixmap)
    return pixmap


def _render_rotated(
    painter: QPainter,
    renderer: QSvgRenderer,
    canvas_width: int,
    canvas_height: int,
    source_width: float,
    source_height: float,
    rotate: float,
    stable_scale: bool = False,
    rotate_overflow: bool = False,
    frame: AnimationFrame = STATIC_FRAME,
) -> None:
    """绕画布中心旋转并等比缩放；默认让旋转后的图标完整落在画布内。

    Args:
        painter: 目标画笔
        renderer: 已加载 SVG 的渲染器
        canvas_width: 画布物理像素宽度
        canvas_height: 画布物理像素高度
        source_width: SVG 源宽度
        source_height: SVG 源高度
        rotate: 旋转角度，单位为度
        stable_scale: 为 True 时按 45 度旋转计算缩放，使旋转过程中大小不变
        rotate_overflow: 为 True 时按 0 度计算缩放，旋转时不缩小；优先于 stable_scale
        frame: 动画取值；本体按 scale 缩放、按 offset_y 竖直位移，
            有水波残影时先画残影再画本体
    """
    if rotate_overflow:
        scale_angle = 0.0
    else:
        scale_angle = 45.0 if stable_scale else rotate
    radians = math.radians(scale_angle)
    cosine = abs(math.cos(radians))
    sine = abs(math.sin(radians))
    bounding_width = source_width * cosine + source_height * sine
    bounding_height = source_width * sine + source_height * cosine
    scale = min(canvas_width / bounding_width, canvas_height / bounding_height)
    if frame.ghost_opacity > 0.0 and frame.ghost_scale > 0.0:
        opacity = painter.opacity()
        painter.setOpacity(opacity * frame.ghost_opacity)
        _draw_icon(
            painter,
            renderer,
            canvas_width / 2,
            canvas_height / 2,
            source_width,
            source_height,
            rotate,
            scale * frame.ghost_scale,
        )
        painter.setOpacity(opacity)
    _draw_icon(
        painter,
        renderer,
        canvas_width / 2,
        canvas_height / 2 + canvas_height * frame.offset_y,
        source_width,
        source_height,
        rotate,
        scale * frame.scale,
    )


def _draw_icon(
    painter: QPainter,
    renderer: QSvgRenderer,
    center_x: float,
    center_y: float,
    source_width: float,
    source_height: float,
    rotate: float,
    scale: float,
) -> None:
    """以指定中心、旋转角度和缩放画一次图标，不改变画笔的其他状态。

    Args:
        painter: 目标画笔
        renderer: 已加载 SVG 的渲染器
        center_x: 图标中心的横坐标，物理像素
        center_y: 图标中心的纵坐标，物理像素
        source_width: SVG 源宽度
        source_height: SVG 源高度
        rotate: 旋转角度，单位为度
        scale: 相对 SVG 源尺寸的缩放
    """
    painter.save()
    painter.translate(center_x, center_y)
    painter.rotate(rotate)
    painter.scale(scale, scale)
    renderer.render(
        painter,
        QRectF(-source_width / 2, -source_height / 2, source_width, source_height),
    )
    painter.restore()
