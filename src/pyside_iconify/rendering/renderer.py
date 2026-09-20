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
) -> QPixmap:
    """渲染并缓存指定参数的 SVG 位图。"""
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
) -> None:
    scale_angle = 45.0 if stable_scale else rotate
    radians = math.radians(scale_angle)
    cosine = abs(math.cos(radians))
    sine = abs(math.sin(radians))
    bounding_width = source_width * cosine + source_height * sine
    bounding_height = source_width * sine + source_height * cosine
    scale = min(canvas_width / bounding_width, canvas_height / bounding_height)
    painter.translate(canvas_width / 2, canvas_height / 2)
    painter.rotate(rotate)
    painter.scale(scale, scale)
    renderer.render(
        painter,
        QRectF(-source_width / 2, -source_height / 2, source_width, source_height),
    )
