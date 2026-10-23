"""尺寸解析"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from pyside_iconify._errors import InvalidSizeError
from pyside_iconify.core.types import SizeSpec

_SIZE_TEXT = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(px|em)$", re.IGNORECASE)


def parse_size(value: int | float | str | Sequence[int | float]) -> SizeSpec:
    """把公开尺寸写法解析为 SizeSpec。

    Args:
        value: 尺寸写法；可传正数（宽高相同，px）、``"16px"``/``"1.5em"`` 字符串，或 (宽, 高) 序列（px）。

    Returns:
        解析后的 SizeSpec。

    Raises:
        InvalidSizeError: 取值为布尔值、字符串无法解析、序列长度不是 2、数值不是有限正数，或类型不受支持。
    """
    if isinstance(value, bool):
        raise InvalidSizeError("size cannot be a boolean")
    if isinstance(value, (int, float)):
        number = _positive_number(value)
        return SizeSpec(number, number)
    if isinstance(value, str):
        match = _SIZE_TEXT.fullmatch(value.strip())
        if match is None:
            raise InvalidSizeError(f"cannot parse size: {value!r}")
        number = _positive_number(float(match.group(1)))
        unit = match.group(2).lower()
        return SizeSpec(number, number, unit)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) != 2:
            raise InvalidSizeError("size tuple must contain width and height")
        width = _positive_number(value[0])
        height = _positive_number(value[1])
        return SizeSpec(width, height)
    raise InvalidSizeError(f"cannot parse size: {value!r}")


def resolve_size(
    spec: SizeSpec, font_pixels: float | None = None
) -> tuple[float, float]:
    """将尺寸描述解析为逻辑像素宽高。

    Args:
        spec: 待解析的尺寸描述。
        font_pixels: 字体像素高度；spec 为 em 单位时必须提供，px 单位时忽略。

    Returns:
        (宽, 高) 逻辑像素元组。

    Raises:
        InvalidSizeError: spec 为 em 单位但未提供 font_pixels。
    """
    if not spec.is_em:
        return spec.width, spec.height
    if font_pixels is None:
        raise InvalidSizeError("em size requires a font context")
    font_size = _positive_number(font_pixels)
    return spec.width * font_size, spec.height * font_size


def _positive_number(value: object) -> float:
    """校验并返回有限正数。

    Args:
        value: 待校验的值；布尔值不被接受。

    Returns:
        转换为 float 的数值。

    Raises:
        InvalidSizeError: 不是数字，或不是有限正数。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidSizeError("size must be numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise InvalidSizeError("size must be a finite positive number")
    return number
