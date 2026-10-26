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
    InvalidAnimationError,
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
from pyside_iconify.core.smil import is_supported_animation
from pyside_iconify.core.svg import collect_paints
from pyside_iconify.core.types import IconData

__version__ = "1.1.0"


def add_icon(name: str, data: IconData | str, *, replace: bool = False) -> None:
    """注册一个本地图标。

    Args:
        name: 图标名；格式为 ``prefix:name``。
        data: 图标数据；可传 IconData 或 SVG body 字符串。
        replace: 同名图标已存在时是否覆盖；False 时抛出重复注册异常。
    """
    registry.add_icon(name, data, replace=replace)


def add_collection(collection: Mapping[str, object], *, replace: bool = False) -> None:
    """注册一份 Iconify JSON 图标集合。

    Args:
        collection: Iconify JSON 集合（已解析为映射）。
        replace: 集合内存在已注册的同名图标时是否覆盖；False 时抛出重复注册异常。
    """
    registry.add_collection(collection, replace=replace)


def get_icon_data(icon: str) -> IconData:
    """返回已注册的图标数据。

    Args:
        icon: 图标名；格式为 ``prefix:name``。

    Returns:
        该图标对应的 IconData。
    """
    return registry.get(icon)


def mark_pending(icon: str) -> None:
    """标记图标数据正在加载。

    Args:
        icon: 图标名；格式为 ``prefix:name``。
    """
    registry.mark_pending(icon)


def is_monotone(icon: str) -> bool:
    """判断图标是否只使用 currentColor。

    Args:
        icon: 已注册的图标名。

    Returns:
        图标没有固定颜色时为 True。
    """
    return not collect_paints(registry.get(icon).body)


def is_animated(icon: str) -> bool:
    """判断图标是否带有可播放的 SMIL 动画。

    只认 SMIL（SVG 内置的 animate、set、animateTransform、animateMotion）。
    CSS 动画、脚本动画等其他形式不属于播放范围，这类图标和普通静态图一样显示。

    Args:
        icon: 已注册的图标名。

    Returns:
        图标含有本库能播放的 SMIL 动画时为 True。
    """
    return is_supported_animation(registry.get(icon).body)


def get_icon_colors(icon: str) -> tuple[str, ...]:
    """列出图标固定颜色。

    Args:
        icon: 已注册的图标名。

    Returns:
        ``#rrggbb`` 形式的颜色字符串元组；不含 alpha。
    """
    return tuple(
        f"#{color.red:02x}{color.green:02x}{color.blue:02x}"
        for color in collect_paints(registry.get(icon).body)
    )


def __getattr__(name: str) -> object:
    """按需延迟导入依赖 Qt、网络、集成与打包的公开接口。

    Args:
        name: 公开属性名；未知名称会抛出 AttributeError。

    Returns:
        对应子模块中的同名对象。
    """
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
    "InvalidAnimationError",
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
    "is_animated",
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
