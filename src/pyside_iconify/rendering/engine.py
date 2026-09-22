"""标准 QIcon 使用的自定义绘制引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from collections.abc import Mapping

from PySide6.QtCore import QSize, Qt, QRectF
from PySide6.QtGui import QIcon, QIconEngine, QPalette, QPainter, QPixmap
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
    color_light_theme: NormalizedColorValue | None
    color_dark_theme: NormalizedColorValue | None
    hover_color: NormalizedColorValue | None
    hover_color_light_theme: NormalizedColorValue | None
    hover_color_dark_theme: NormalizedColorValue | None
    selected_color: NormalizedColorValue | None
    selected_color_light_theme: NormalizedColorValue | None
    selected_color_dark_theme: NormalizedColorValue | None
    opacity: float
    disabled_opacity: float
    spin: bool
    spin_period: float
    rotate: float
    h_flip: bool
    v_flip: bool


class IconEngine(QIconEngine):
    """按当前注册表数据绘制图标的 QIconEngine。"""

    def __init__(
        self,
        name: IconName,
        options: IconOptions,
        *,
        state_mode: str | None = None,
    ) -> None:
        super().__init__()
        self._name = name
        self._options = options
        # 事件驱动悬停用：按钮样式对图标永远请求 Active，
        # 无法靠 QIcon mode 表达悬停，改为外部切换两个固定状态的图标。
        # "normal" 永远用常态色，"hover" 永远用悬停/选中强调色。
        self._state_mode = state_mode

    def clone(self) -> QIconEngine:
        return IconEngine(self._name, self._options, state_mode=self._state_mode)

    def key(self) -> str:
        # 版本参与 key，数据更新后 QIcon 内部缓存才会失效。
        try:
            version = registry.version(self._name)
        except IconNotFoundError:
            version = "pending"
        # 状态色参与 key：QIcon 的 pixmap 缓存按 key 索引，
        # hover/selected 配置不同就必须是不同的 key。
        options = self._options
        state_key = repr(
            (
                options.hover_color,
                options.hover_color_light_theme,
                options.hover_color_dark_theme,
                options.selected_color,
                options.selected_color_light_theme,
                options.selected_color_dark_theme,
                self._state_mode,
            )
        )
        return f"pyside_iconify/{self._name}/{version}/{state_key}"

    def actualSize(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QSize:
        if self._options.size.is_em:
            return size
        return QSize(round(self._options.size.width), round(self._options.size.height))

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return self.scaledPixmap(size, mode, state, 1.0)

    def paint(self, painter: QPainter, rect: QRectF, mode: QIcon.Mode, state: QIcon.State) -> None:
        """item view 等通过 QIcon.paint() 绘制时走这里。"""
        device = painter.device()
        ratio = device.devicePixelRatioF() if device is not None else 1.0
        size = QSize(max(1, round(rect.width())), max(1, round(rect.height())))
        pixmap = self.scaledPixmap(size, mode, state, ratio)
        painter.drawPixmap(QRectF(rect), pixmap, QRectF(pixmap.rect()))

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
            from pyside_iconify.network import client as _network

            client = _network.default_client()
            client.ensure_loaded(render_name)
            if registry.is_pending(render_name):
                from pyside_iconify.rendering.placeholder import create_blank

                return create_blank(width, height, scale)
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
        if self._state_mode == "normal" and mode in (
            QIcon.Mode.Active,
            QIcon.Mode.Selected,
        ):
            mode = QIcon.Mode.Normal
        elif self._state_mode == "hover" and mode != QIcon.Mode.Disabled:
            mode = QIcon.Mode.Active
        color, colors = _resolve_colors(self._options, mode)
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
    # 构造即预触发加载：目标（树节点、菜单项）可能迟迟不绘制，
    # 等首次绘制才请求会拖慢图标出现。
    if not registry.contains(name) and not registry.is_pending(name):
        from pyside_iconify.network.client import default_client

        default_client().ensure_loaded(name)
    return QIcon(IconEngine(name, options))


def _resolve_colors(
    options: IconOptions,
    mode: QIcon.Mode = QIcon.Mode.Normal,
) -> tuple[RGBA | None, Mapping[object, RGBA] | None]:
    selected = _select_theme_color(options)
    if selected is None:
        palette = QApplication.palette()
        from pyside_iconify.rendering.qt_adapter import normalize_color

        selected = normalize_color(palette.color(QPalette.ColorRole.WindowText))
    if mode in (QIcon.Mode.Active, QIcon.Mode.Selected):
        override = _select_state_color(options, mode)
        if override is not None:
            selected = override
        # 不写 hover/selected 参数时不做任何变化：
        # 悬停/选中变色是显式启用的功能。
    if isinstance(selected, Mapping):
        return None, selected
    return selected, None


def _select_state_color(
    options: IconOptions, mode: QIcon.Mode
) -> NormalizedColorValue | None:
    dark = _is_dark_theme()
    if mode == QIcon.Mode.Active:
        return _select_hover_color(options, dark)
    return _select_selected_color(options, dark)


def _select_hover_color(
    options: IconOptions, dark: bool
) -> NormalizedColorValue | None:
    if dark and options.hover_color_dark_theme is not None:
        return options.hover_color_dark_theme
    if not dark and options.hover_color_light_theme is not None:
        return options.hover_color_light_theme
    return options.hover_color


def _select_selected_color(
    options: IconOptions, dark: bool
) -> NormalizedColorValue | None:
    if dark and options.selected_color_dark_theme is not None:
        return options.selected_color_dark_theme
    if not dark and options.selected_color_light_theme is not None:
        return options.selected_color_light_theme
    return options.selected_color


def _is_dark_theme() -> bool:
    palette = QApplication.palette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


def _select_theme_color(options: IconOptions) -> ColorValue | None:
    palette = QApplication.palette()
    window = palette.color(QPalette.ColorRole.Window)
    dark = window.lightness() < 128
    if dark and options.color_dark_theme is not None:
        return options.color_dark_theme
    if not dark and options.color_light_theme is not None:
        return options.color_light_theme
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
