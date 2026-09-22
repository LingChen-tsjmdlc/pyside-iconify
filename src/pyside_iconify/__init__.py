"""给 QIcon 换一个数据来源。"""

from __future__ import annotations

from collections.abc import Mapping
import re

from pyside_iconify._errors import (
    ClientClosedError,
    DuplicateIconError,
    IconNotFoundError,
    IconNotLoadedError,
    IconifyError,
    InvalidColorError,
    InvalidIconDataError,
    InvalidIconNameError,
    InvalidOpacityError,
    InvalidResponseError,
    InvalidRotationError,
    InvalidSizeError,
    NetworkError,
    NoApplicationError,
    OfflineError,
    RateLimitError,
    RequestCancelledError,
    ResponseTooLargeError,
    ServerError,
    UnsupportedSvgError,
    UnsupportedTargetError,
    UnsafeIconDataError,
    WrongThreadError,
)
from pyside_iconify.core.colors import hex_argb, hex_rgba, parse_color
from pyside_iconify.core.registry import registry
from pyside_iconify.core.svg import collect_paints
from pyside_iconify.core.types import IconData

__version__ = "0.1.0.dev0"


def add_icon(name: str, data: IconData | str, *, replace: bool = False) -> None:
    """注册一个本地图标。"""
    registry.add_icon(name, data, replace=replace)


def add_collection(collection: Mapping[str, object], *, replace: bool = False) -> None:
    """注册一份 Iconify JSON 图标集合。"""
    registry.add_collection(collection, replace=replace)


def get_icon_data(icon: str) -> IconData:
    """返回已注册的图标数据。"""
    return registry.get(icon)


def mark_pending(icon: str) -> None:
    """标记图标数据正在加载。"""
    registry.mark_pending(icon)


def is_monotone(icon: str) -> bool:
    """判断图标是否只使用 currentColor。"""
    return not collect_paints(registry.get(icon).body)


def get_icon_colors(icon: str) -> tuple[str, ...]:
    """列出图标固定颜色。"""
    return tuple(
        f"#{color.red:02x}{color.green:02x}{color.blue:02x}"
        for color in collect_paints(registry.get(icon).body)
    )


def __getattr__(name: str) -> object:
    """延迟导入依赖 Qt 的公开接口。"""
    if name == "IconWidget":
        from pyside_iconify.widgets import IconWidget

        return IconWidget
    qt_api_names = {
        "get_default_config",
        "get_icon",
        "get_pixmap",
        "set_cache_limits",
        "set_default_config",
        "set_disabled_opacity",
    }
    if name in qt_api_names:
        from pyside_iconify import _api

        return getattr(_api, name)
    network_names = {
        "IconifyClient",
        "LoadRequest",
        "default_client",
        "is_offline",
        "load_icons",
        "set_offline",
    }
    if name in network_names:
        from pyside_iconify import network

        return getattr(network, name)
    if name in {"register_icon_target", "set_icon"}:
        from pyside_iconify import integrations

        return getattr(integrations, name)
    if name in {"pack_icons", "pack_project"}:
        from pyside_iconify import pack

        return getattr(pack, name)
    if name == "load_bundle":
        from pyside_iconify import pack

        return getattr(pack, "load_bundle")
    raise AttributeError(name)


__all__ = [
    "ClientClosedError",
    "DuplicateIconError",
    "IconNotFoundError",
    "IconNotLoadedError",
    "IconWidget",
    "IconifyClient",
    "IconifyError",
    "InvalidColorError",
    "InvalidIconDataError",
    "InvalidIconNameError",
    "InvalidOpacityError",
    "InvalidResponseError",
    "InvalidRotationError",
    "InvalidSizeError",
    "LoadRequest",
    "NetworkError",
    "NoApplicationError",
    "OfflineError",
    "RateLimitError",
    "RequestCancelledError",
    "ResponseTooLargeError",
    "ServerError",
    "UnsupportedSvgError",
    "UnsupportedTargetError",
    "UnsafeIconDataError",
    "WrongThreadError",
    "add_collection",
    "add_icon",
    "default_client",
    "get_default_config",
    "get_icon",
    "get_icon_colors",
    "get_icon_data",
    "get_pixmap",
    "hex_argb",
    "hex_rgba",
    "is_monotone",
    "is_offline",
    "load_bundle",
    "load_icons",
    "mark_pending",
    "pack_icons",
    "pack_project",
    "register_icon_target",
    "set_cache_limits",
    "set_default_config",
    "set_disabled_opacity",
    "set_icon",
    "set_offline",
]
