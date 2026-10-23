"""默认配置。"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from threading import RLock
from typing import Final

from pyside_iconify._errors import InvalidOpacityError, InvalidRotationError
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.sizes import parse_size

_UNSET: Final = object()


@dataclass(frozen=True, slots=True)
class DefaultConfig:
    """新建图标时使用的全局默认配置。

    Attributes:
        size: 默认图标尺寸；可传数字、``"16px"``/``"1.5em"`` 字符串或 (宽, 高) 序列。
        color: 默认颜色；None 表示不指定。
        color_light_theme: 浅色主题下的默认颜色；None 表示不指定。
        color_dark_theme: 深色主题下的默认颜色；None 表示不指定。
        opacity: 默认不透明度；0 到 1。
        fallback: 图标加载失败时显示的后备图标名；None 表示不使用后备图标。
        disabled_opacity: 禁用状态的不透明度；0 到 1。
        spin_period: 旋转一圈所需的秒数；须为有限正数。
    """

    size: object = 24
    color: object | None = None
    color_light_theme: object | None = None
    color_dark_theme: object | None = None
    opacity: float = 1.0
    fallback: str | None = None
    disabled_opacity: float = 0.4
    spin_period: float = 1.0


_BUILTIN = DefaultConfig()
_lock = RLock()
_config = _BUILTIN


def get_default_config() -> DefaultConfig:
    """返回当前默认配置。

    Returns:
        当前生效的 DefaultConfig。
    """
    with _lock:
        return _config


def set_default_config(
    *,
    size: object = _UNSET,
    color: object = _UNSET,
    color_light_theme: object = _UNSET,
    color_dark_theme: object = _UNSET,
    opacity: object = _UNSET,
    fallback: object = _UNSET,
    disabled_opacity: object = _UNSET,
    spin_period: object = _UNSET,
) -> DefaultConfig:
    """更新新图标的默认配置。

    未传入的参数保持当前值；传入 None 则恢复为内置默认值。

    Args:
        size: 默认尺寸；可传数字、``"16px"``/``"1.5em"`` 字符串或 (宽, 高) 序列。
        color: 默认颜色。
        color_light_theme: 浅色主题下的默认颜色。
        color_dark_theme: 深色主题下的默认颜色。
        opacity: 默认不透明度；0 到 1。
        fallback: 后备图标名；格式为 ``prefix:name``。
        disabled_opacity: 禁用状态的不透明度；0 到 1。
        spin_period: 旋转一圈所需的秒数；须为有限正数。

    Returns:
        更新后的 DefaultConfig。
    """
    values = {
        "size": _value_or_builtin("size", size),
        "color": _value_or_builtin("color", color),
        "color_light_theme": _value_or_builtin("color_light_theme", color_light_theme),
        "color_dark_theme": _value_or_builtin("color_dark_theme", color_dark_theme),
        "opacity": _value_or_builtin("opacity", opacity),
        "fallback": _value_or_builtin("fallback", fallback),
        "disabled_opacity": _value_or_builtin("disabled_opacity", disabled_opacity),
        "spin_period": _value_or_builtin("spin_period", spin_period),
    }
    _validate(values)
    global _config
    with _lock:
        _config = replace(_config, **values)
        return _config


def set_disabled_opacity(value: float) -> None:
    """设置禁用状态的默认不透明度。

    Args:
        value: 不透明度；0 到 1。
    """
    set_default_config(disabled_opacity=value)


def _value_or_builtin(name: str, value: object) -> object:
    """按字段名解析最终值：未设置取当前值，None 取内置默认值，否则原样返回。

    Args:
        name: 配置字段名。
        value: 调用方传入的值；_UNSET 表示未传，None 表示恢复内置默认值。

    Returns:
        解析后的最终值。
    """
    if value is _UNSET:
        return getattr(_config, name)
    if value is None:
        return getattr(_BUILTIN, name)
    return value


def _opacity(value: object) -> None:
    """校验不透明度是 0 到 1 之间的数字。

    Args:
        value: 待校验的值。

    Raises:
        InvalidOpacityError: 不是数字（含布尔值）或超出 0 到 1。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
    ):
        raise InvalidOpacityError("opacity must be between 0 and 1")


def _validate(values: dict[str, object]) -> None:
    """校验一组配置字段的取值。

    Args:
        values: 字段名到取值的映射；须包含 size、opacity、disabled_opacity、spin_period、fallback。

    Raises:
        InvalidRotationError: spin_period 不是有限正数。
    """
    parse_size(values["size"])
    _opacity(values["opacity"])
    _opacity(values["disabled_opacity"])
    period = values["spin_period"]
    if (
        isinstance(period, bool)
        or not isinstance(period, (int, float))
        or not math.isfinite(period)
        or period <= 0
    ):
        raise InvalidRotationError("spin_period must be a finite positive number")
    fallback = values["fallback"]
    if fallback is not None:
        if not isinstance(fallback, str):
            raise TypeError("fallback must be a string or None")
        parse_icon_name(fallback)
