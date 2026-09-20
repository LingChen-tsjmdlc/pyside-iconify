"""公开函数实现。"""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import QSize
from PySide6.QtGui import QFontMetrics, QIcon, QPixmap

from pyside_iconify._config import (
    get_default_config,
    set_default_config,
    set_disabled_opacity,
)
from pyside_iconify.core.colors import hex_argb, hex_rgba
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.registry import registry
from pyside_iconify.core.sizes import resolve_size
from pyside_iconify.core.svg import collect_paints
from pyside_iconify.core.types import IconData
from pyside_iconify.rendering.cache import pixmap_cache
from pyside_iconify.rendering.engine import create_icon
from pyside_iconify.rendering.options import make_options
from pyside_iconify.rendering.qt_adapter import require_application, require_main_thread


def add_icon(name: str, data: IconData | str, *, replace: bool = False) -> None:
    """注册一个本地图标。"""
    registry.add_icon(name, data, replace=replace)


def add_collection(collection: Mapping[str, object], *, replace: bool = False) -> None:
    """注册一份 Iconify JSON 图标集合。"""
    registry.add_collection(collection, replace=replace)


def get_icon(
    icon: str | IconData,
    *,
    size: object | None = None,
    color: object | None = None,
    light_color: object | None = None,
    dark_color: object | None = None,
    opacity: float | None = None,
    width: object | None = None,
    height: object | None = None,
    rotate: float = 0,
    spin: bool = False,
    h_flip: bool = False,
    v_flip: bool = False,
) -> QIcon:
    """返回可用于任意 Qt 控件的标准 QIcon。"""
    require_application()
    require_main_thread()
    options = make_options(
        size=size,
        color=color,
        light_color=light_color,
        dark_color=dark_color,
        opacity=opacity,
        width=width,
        height=height,
        spin=spin,
        rotate=rotate,
        h_flip=h_flip,
        v_flip=v_flip,
    )
    name = (
        registry.register_inline(icon)
        if isinstance(icon, IconData)
        else parse_icon_name(icon)
    )
    return create_icon(name, options)


def get_pixmap(
    icon: str | IconData, *, size: object | None = None, **options: object
) -> QPixmap:
    """返回静态 QPixmap。"""
    require_application()
    require_main_thread()
    render_options = make_options(size=size, **options)
    font_pixels = QFontMetrics(require_application().font()).height()
    width, height = resolve_size(render_options.size, font_pixels)
    name = (
        registry.register_inline(icon)
        if isinstance(icon, IconData)
        else parse_icon_name(icon)
    )
    qicon = create_icon(name, render_options)
    return qicon.pixmap(QSize(round(width), round(height)))


def get_icon_data(icon: str) -> IconData:
    """返回已注册的图标数据。"""
    return registry.get(icon)


def is_monotone(icon: str) -> bool:
    """判断图标是否只使用 currentColor。"""
    return not collect_paints(registry.get(icon).body)


def get_icon_colors(icon: str) -> tuple[str, ...]:
    """列出图标固定颜色。"""
    return tuple(
        f"#{color.red:02x}{color.green:02x}{color.blue:02x}"
        for color in collect_paints(registry.get(icon).body)
    )


def set_cache_limits(
    *, pixmap_mib: int | None = None, data_entries: int | None = None
) -> None:
    """调整缓存上限。"""
    if data_entries is not None:
        registry.set_limit(data_entries)
    if pixmap_mib is not None:
        if pixmap_mib <= 0:
            raise ValueError("pixmap_mib must be greater than 0")
        pixmap_cache.set_limit_mib(pixmap_mib)


__all__ = [
    "add_collection",
    "add_icon",
    "get_default_config",
    "get_icon",
    "get_icon_colors",
    "get_icon_data",
    "get_pixmap",
    "hex_argb",
    "hex_rgba",
    "is_monotone",
    "set_cache_limits",
    "set_default_config",
    "set_disabled_opacity",
]
