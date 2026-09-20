"""颜色解析"""

from __future__ import annotations

import colorsys
import math
import re
from collections.abc import Sequence

from pyside_iconify._errors import InvalidColorError
from pyside_iconify.core.types import RGBA

_HEX = re.compile(r"^#?([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB = re.compile(r"^rgba?\((.*)\)$", re.IGNORECASE)
_HSL = re.compile(r"^hsla?\((.*)\)$", re.IGNORECASE)


def hex_rgba(value: str) -> RGBA:
    """按 CSS 的 #RRGGBBAA 顺序解析十六进制颜色。"""
    return _parse_hex(value, alpha_last=True)


def hex_argb(value: str) -> RGBA:
    """按 Qt 的 #AARRGGBB 顺序解析十六进制颜色。"""
    return _parse_hex(value, alpha_last=False)


def parse_color(value: str | Sequence[int | float] | RGBA) -> RGBA:
    """解析 CSS 函数、默认 RGBA HEX、元组或 RGBA。"""
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.lower() == "transparent":
            return RGBA(0, 0, 0, 0)
        if _HEX.fullmatch(text):
            return hex_rgba(text)
        if _RGB.fullmatch(text):
            return _parse_rgb(text)
        if _HSL.fullmatch(text):
            return _parse_hsl(text)
        raise InvalidColorError(f"cannot parse color: {value!r}")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return _parse_tuple(value)
    raise InvalidColorError(f"cannot parse color: {value!r}")


def _parse_hex(value: str, *, alpha_last: bool) -> RGBA:
    match = _HEX.fullmatch(value.strip())
    if match is None:
        raise InvalidColorError(f"invalid HEX color: {value!r}")
    digits = match.group(1)
    if len(digits) in (3, 4):
        digits = "".join(character * 2 for character in digits)
    if len(digits) == 6:
        return RGBA(int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    if alpha_last:
        return RGBA(
            int(digits[0:2], 16),
            int(digits[2:4], 16),
            int(digits[4:6], 16),
            int(digits[6:8], 16),
        )
    return RGBA(
        int(digits[2:4], 16),
        int(digits[4:6], 16),
        int(digits[6:8], 16),
        int(digits[0:2], 16),
    )


def _parse_rgb(value: str) -> RGBA:
    match = _RGB.fullmatch(value.strip())
    if match is None:
        raise InvalidColorError(f"invalid RGB color: {value!r}")
    values = [part.strip() for part in match.group(1).split(",")]
    if len(values) not in (3, 4):
        raise InvalidColorError("rgb() and rgba() require three or four values")
    red, green, blue = (_parse_channel(part) for part in values[:3])
    alpha = _parse_alpha(values[3]) if len(values) == 4 else 255
    return RGBA(red, green, blue, alpha)


def _parse_hsl(value: str) -> RGBA:
    match = _HSL.fullmatch(value.strip())
    if match is None:
        raise InvalidColorError(f"invalid HSL color: {value!r}")
    values = [part.strip() for part in match.group(1).split(",")]
    if len(values) not in (3, 4):
        raise InvalidColorError("hsl() and hsla() require three or four values")
    hue = _finite_number(values[0]) % 360.0
    saturation = _parse_percent(values[1])
    lightness = _parse_percent(values[2])
    red, green, blue = colorsys.hls_to_rgb(hue / 360.0, lightness, saturation)
    alpha = _parse_alpha(values[3]) if len(values) == 4 else 255
    return RGBA(round(red * 255), round(green * 255), round(blue * 255), alpha)


def _parse_tuple(value: Sequence[int | float]) -> RGBA:
    if len(value) not in (3, 4):
        raise InvalidColorError("color tuple requires three or four integers")
    channels = [_parse_channel(channel) for channel in value[:3]]
    alpha = _parse_channel(value[3]) if len(value) == 4 else 255
    return RGBA(*channels, alpha)


def _parse_channel(value: str | int | float) -> int:
    if isinstance(value, str) and value.endswith("%"):
        return round(_parse_percent(value) * 255)
    number = _finite_number(value)
    if not 0 <= number <= 255 or number != int(number):
        raise InvalidColorError("color channels must be integers between 0 and 255")
    return int(number)


def _parse_alpha(value: str | int | float) -> int:
    if isinstance(value, str) and value.endswith("%"):
        return round(_parse_percent(value) * 255)
    number = _finite_number(value)
    if not 0 <= number <= 1:
        raise InvalidColorError("alpha must be between 0 and 1")
    return round(number * 255)


def _parse_percent(value: str | int | float) -> float:
    if not isinstance(value, str) or not value.endswith("%"):
        raise InvalidColorError("a percentage is required")
    number = _finite_number(value[:-1])
    if not 0 <= number <= 100:
        raise InvalidColorError("percentage must be between 0 and 100")
    return number / 100.0


def _finite_number(value: str | int | float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise InvalidColorError(f"invalid numeric value: {value!r}") from error
    if not math.isfinite(number):
        raise InvalidColorError("color values must be finite")
    return number
