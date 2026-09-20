"""标准 QIcon 使用的自定义绘制引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from collections.abc import Mapping

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPalette, QPixmap
from PySide6.QtWidgets import QApplication

from pyside_iconify._errors import (
    IconNotFoundError,
    InvalidIconNameError,
    UnsupportedSvgError,
)
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.registry import registry
from pyside_iconify.core.types import IconName, RGBA, SizeSpec
from pyside_iconify.rendering.placeholder import create_placeholder
from pyside_iconify.rendering.qt_adapter import (
    NormalizedColorValue,
    require_main_thread,
)
from pyside_iconify.rendering.renderer import render_pixmap


@dataclass(frozen=True, slots=True)
class IconOptions:
    """图标渲染选项。"""

    size: SizeSpec
    color: NormalizedColorValue | None
    light_color: NormalizedColorValue | None
    dark_color: NormalizedColorValue | None
    opacity: float
    disabled_opacity: float
    spin: bool
    spin_period: float
    rotate: float
    h_flip: bool
    v_flip: bool


class IconEngine(QIconEngine):
    """按当前注册表数据绘制图标的 QIconEngine。"""

    def __init__(self, name: IconName, options: IconOptions) -> None:
        super().__init__()
        self._name = name
        self._options = options

    def clone(self) -> QIconEngine:
        return IconEngine(self._name, self._options)

    def key(self) -> str:
        return "pyside_iconify"

    def actualSize(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QSize:
        if self._options.size.is_em:
            return size
        return QSize(round(self._options.size.width), round(self._options.size.height))

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(
        self, size: QSize, mode: QIcon.Mode, state: QIcon.State, scale: float
    ) -> QPixmap:
        require_main_thread()
        width = max(1, size.width())
        height = max(1, size.height())
        render_name = self._name
        if registry.is_pending(render_name):
            from pyside_iconify.rendering.placeholder import create_blank

            return create_blank(width, height, scale)
        try:
            data = registry.get(render_name)
            version = registry.version(render_name)
        except IconNotFoundError:
            from pyside_iconify._config import get_default_config

            fallback = get_default_config().fallback
            if fallback is None:
                return create_placeholder(width, height, scale)
            try:
                render_name = parse_icon_name(fallback)
                data = registry.get(render_name)
                version = registry.version(render_name)
            except (IconNotFoundError, InvalidIconNameError):
                return create_placeholder(width, height, scale)
        color, colors = _resolve_colors(self._options)
        disabled = (
            self._options.disabled_opacity if mode == QIcon.Mode.Disabled else 1.0
        )
        opacity = self._options.opacity * disabled
        spin_angle = (
            round((monotonic() / self._options.spin_period * 360.0) / 5.0) * 5.0
            if self._options.spin
            else 0.0
        )
        rotate = (self._options.rotate + spin_angle) % 360.0
        key = _cache_key(
            render_name,
            version,
            width,
            height,
            scale,
            color,
            colors,
            opacity,
            self._options,
            rotate,
        )
        try:
            return render_pixmap(
                cache_key=key,
                data=data,
                width=width,
                height=height,
                device_pixel_ratio=scale,
                color=color,
                colors=colors,
                opacity=opacity,
                rotate=rotate,
                h_flip=self._options.h_flip,
                v_flip=self._options.v_flip,
                stable_scale=self._options.spin,
            )
        except UnsupportedSvgError:
            return create_placeholder(width, height, scale)


def create_icon(name: IconName, options: IconOptions) -> QIcon:
    """用自定义引擎创建标准 QIcon。"""
    require_main_thread()
    return QIcon(IconEngine(name, options))


def _resolve_colors(
    options: IconOptions,
) -> tuple[RGBA | None, Mapping[object, RGBA] | None]:
    selected = _select_theme_color(options)
    if selected is None:
        palette = QApplication.palette()
        from pyside_iconify.rendering.qt_adapter import normalize_color

        selected = normalize_color(palette.color(QPalette.ColorRole.WindowText))
    if isinstance(selected, Mapping):
        return None, selected
    return selected, None


def _select_theme_color(options: IconOptions) -> ColorValue | None:
    palette = QApplication.palette()
    window = palette.color(QPalette.ColorRole.Window)
    dark = window.lightness() < 128
    if dark and options.dark_color is not None:
        return options.dark_color
    if not dark and options.light_color is not None:
        return options.light_color
    return options.color


def _cache_key(
    name: IconName,
    version: int,
    width: int,
    height: int,
    scale: float,
    color: RGBA | None,
    colors: Mapping[object, RGBA] | None,
    opacity: float,
    options: IconOptions,
    rotate: float,
) -> str:
    text = repr(
        (
            str(name),
            version,
            width,
            height,
            scale,
            color,
            tuple(sorted((colors or {}).items(), key=repr)),
            opacity,
            rotate,
            options.h_flip,
            options.v_flip,
        )
    )
    return sha256(text.encode("utf-8")).hexdigest()
