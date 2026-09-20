"""渲染选项构造"""

from __future__ import annotations

import math

from pyside_iconify._config import get_default_config
from pyside_iconify._errors import InvalidOpacityError, InvalidRotationError
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.rendering.engine import IconOptions
from pyside_iconify.rendering.qt_adapter import (
    ColorValue,
    normalize_color_value,
    normalize_size,
)


def make_options(
    *,
    size: object | None = None,
    color: ColorValue | None = None,
    light_color: ColorValue | None = None,
    dark_color: ColorValue | None = None,
    opacity: float | None = None,
    disabled_opacity: float | None = None,
    spin: bool = False,
    spin_period: float | None = None,
    width: object | None = None,
    height: object | None = None,
    rotate: float = 0,
    h_flip: bool = False,
    v_flip: bool = False,
) -> IconOptions:
    """把公开参数和默认配置转为渲染选项。"""
    defaults = get_default_config()
    actual_size = defaults.size if size is None else size
    actual_color = defaults.color if color is None else color
    actual_light = defaults.light_color if light_color is None else light_color
    actual_dark = defaults.dark_color if dark_color is None else dark_color
    actual_opacity = defaults.opacity if opacity is None else opacity
    actual_disabled_opacity = (
        defaults.disabled_opacity if disabled_opacity is None else disabled_opacity
    )
    actual_spin_period = defaults.spin_period if spin_period is None else spin_period
    resolved_size = normalize_size(actual_size)
    if width is not None or height is not None:
        resolved_width = (
            normalize_size(width).width if width is not None else resolved_size.width
        )
        resolved_height = (
            normalize_size(height).height
            if height is not None
            else resolved_size.height
        )
        resolved_size = type(resolved_size)(resolved_width, resolved_height)
    return IconOptions(
        size=resolved_size,
        color=normalize_color_value(actual_color),
        light_color=normalize_color_value(actual_light),
        dark_color=normalize_color_value(actual_dark),
        opacity=_opacity(actual_opacity),
        disabled_opacity=_opacity(actual_disabled_opacity),
        spin=bool(spin),
        spin_period=_spin_period(actual_spin_period),
        rotate=_rotation(rotate),
        h_flip=bool(h_flip),
        v_flip=bool(v_flip),
    )


def _opacity(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
    ):
        raise InvalidOpacityError("opacity must be between 0 and 1")
    return float(value)


def _spin_period(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise InvalidRotationError("spin_period must be a finite positive number")
    return float(value)


def _rotation(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise InvalidRotationError("rotate must be a finite number")
    return float(value) % 360.0
