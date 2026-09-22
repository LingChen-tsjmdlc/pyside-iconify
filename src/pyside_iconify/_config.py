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
    """默认值。"""

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
    """返回当前默认值。"""
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
    """更新新图标的默认值。"""
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
    """设置禁用透明度。"""
    set_default_config(disabled_opacity=value)


def _value_or_builtin(name: str, value: object) -> object:
    if value is _UNSET:
        return getattr(_config, name)
    if value is None:
        return getattr(_BUILTIN, name)
    return value


def _opacity(value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
    ):
        raise InvalidOpacityError("opacity must be between 0 and 1")


def _validate(values: dict[str, object]) -> None:
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
