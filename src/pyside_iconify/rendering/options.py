"""渲染选项构造。"""

from __future__ import annotations

import math

from pyside_iconify._config import get_default_config
from pyside_iconify._errors import (
    InvalidAnimationError,
    InvalidOpacityError,
    InvalidRotationError,
)
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.rendering.engine import IconOptions
from pyside_iconify.rendering.motion import ANIMATIONS, DEFAULT_DEPTHS, DEFAULT_PERIODS
from pyside_iconify.rendering.qt_adapter import (
    ColorValue,
    normalize_color_value,
    normalize_size,
)


def make_options(
    *,
    size: object | None = None,
    color: ColorValue | None = None,
    color_light_theme: ColorValue | None = None,
    color_dark_theme: ColorValue | None = None,
    hover_color: ColorValue | None = None,
    hover_color_light_theme: ColorValue | None = None,
    hover_color_dark_theme: ColorValue | None = None,
    selected_color: ColorValue | None = None,
    selected_color_light_theme: ColorValue | None = None,
    selected_color_dark_theme: ColorValue | None = None,
    opacity: float | None = None,
    disabled_opacity: float | None = None,
    spin: bool = False,
    spin_period: float | None = None,
    animation: str | None = None,
    animation_period: float | None = None,
    animation_depth: float | None = None,
    width: object | None = None,
    height: object | None = None,
    rotate: float = 0,
    rotate_overflow: bool = False,
    h_flip: bool = False,
    v_flip: bool = False,
) -> IconOptions:
    """把公开参数和默认配置转为渲染选项。

    值为 None 的参数使用默认配置；颜色与尺寸在此处立即校验并规范化。

    Args:
        size: 图标尺寸；可传 SizeSpec、QSize、数字、字符串、元组或列表，None 用默认配置
        color: 基础颜色；可传颜色值或颜色映射表，None 用默认配置
        color_light_theme: 浅色主题基础颜色；None 用默认配置
        color_dark_theme: 深色主题基础颜色；None 用默认配置
        hover_color: 悬停颜色；None 表示不变色
        hover_color_light_theme: 浅色主题悬停颜色；None 表示不指定
        hover_color_dark_theme: 深色主题悬停颜色；None 表示不指定
        selected_color: 选中颜色；None 表示不变色
        selected_color_light_theme: 浅色主题选中颜色；None 表示不指定
        selected_color_dark_theme: 深色主题选中颜色；None 表示不指定
        opacity: 整体不透明度；0 到 1，None 用默认配置
        disabled_opacity: 禁用时的不透明度；0 到 1，None 用默认配置
        spin: 是否持续旋转；等价于 animation="spin"，不能与其他动画同时给出
        spin_period: 旋转一周的秒数；有限正数，None 用默认配置
        animation: 内置动画；"spin"、"pulse"、"breathe"、"ping"、"bounce" 之一，
            None 表示不动画
        animation_period: 动画一个周期的秒数；有限正数，None 时 spin 用 spin_period，
            pulse、ping、bounce 为 1 秒，breathe 为 2 秒
        animation_depth: 动画变化幅度；0 到 1，None 用默认值。pulse 默认 0.25（缩到 75%），
            breathe 默认 0.7（淡到 30%），ping 默认 1（水波扩散到 2 倍），
            bounce 默认 0.25（跳起图标高度的 25%）。ping、bounce 会把图标缩小到
            1 / (1 + 幅度)，给水波和弹跳留出空间。spin 不能给出
        width: 单独覆盖宽度；可传与 size 相同的写法，只取其宽度
        height: 单独覆盖高度；可传与 size 相同的写法，只取其高度
        rotate: 固定旋转角度；有限数字，单位为度，会对 360 取模
        rotate_overflow: 旋转时是否保持原大小；False 按角度自动缩小以免被裁切，
            True 不缩小，铺满控件的图标旋转时四角可能被裁掉
        h_flip: 是否水平翻转
        v_flip: 是否垂直翻转

    Returns:
        规范化后的 IconOptions。
    """
    defaults = get_default_config()
    actual_size = defaults.size if size is None else size
    actual_color = defaults.color if color is None else color
    actual_light = defaults.color_light_theme if color_light_theme is None else color_light_theme
    actual_dark = defaults.color_dark_theme if color_dark_theme is None else color_dark_theme
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
    kind = _animation(animation, spin)
    validated_spin_period = _spin_period(actual_spin_period)
    if animation_period is not None:
        period = _period(animation_period, "animation_period")
    elif kind in DEFAULT_PERIODS:
        period = DEFAULT_PERIODS[kind]
    else:
        period = validated_spin_period
    depth = _depth(animation_depth, kind)
    return IconOptions(
        size=resolved_size,
        color=normalize_color_value(actual_color),
        color_light_theme=normalize_color_value(actual_light),
        color_dark_theme=normalize_color_value(actual_dark),
        hover_color=normalize_color_value(hover_color),
        hover_color_light_theme=normalize_color_value(hover_color_light_theme),
        hover_color_dark_theme=normalize_color_value(hover_color_dark_theme),
        selected_color=normalize_color_value(selected_color),
        selected_color_light_theme=normalize_color_value(selected_color_light_theme),
        selected_color_dark_theme=normalize_color_value(selected_color_dark_theme),
        opacity=_opacity(actual_opacity),
        disabled_opacity=_opacity(actual_disabled_opacity),
        animation=kind,
        animation_period=period,
        animation_depth=depth,
        spin_period=validated_spin_period,
        rotate=_rotation(rotate),
        rotate_overflow=bool(rotate_overflow),
        h_flip=bool(h_flip),
        v_flip=bool(v_flip),
    )


def _animation(animation: str | None, spin: bool) -> str | None:
    """合并 animation 与 spin 两个参数，得到最终的动画名称。

    Args:
        animation: 动画名称；"spin"、"pulse"、"breathe"、"ping"、"bounce" 之一或 None
        spin: 旧写法，True 等价于 animation="spin"

    Returns:
        动画名称，不动画时为 None。

    Raises:
        InvalidAnimationError: 名称不在支持列表里，或 spin=True 与其他动画同时给出。
    """
    if animation is not None and (
        not isinstance(animation, str) or animation not in ANIMATIONS
    ):
        raise InvalidAnimationError(
            f"animation must be one of {', '.join(ANIMATIONS)} or None"
        )
    if spin and animation not in (None, "spin"):
        raise InvalidAnimationError(
            f"spin=True conflicts with animation={animation!r}; use only one of them"
        )
    if animation is not None:
        return animation
    return "spin" if spin else None


def _opacity(value: float) -> float:
    """校验不透明度。

    Args:
        value: 不透明度；0 到 1 的数字，不接受 bool

    Returns:
        转为 float 的不透明度。

    Raises:
        InvalidOpacityError: 值不是数字、是 bool 或不在 0 到 1 之间。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
    ):
        raise InvalidOpacityError("opacity must be between 0 and 1")
    return float(value)


def _spin_period(value: float) -> float:
    """校验旋转周期。

    Args:
        value: 旋转一周的秒数；有限正数，不接受 bool

    Returns:
        转为 float 的旋转周期。

    Raises:
        InvalidRotationError: 值不是数字、是 bool、非有限数或不大于 0。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise InvalidRotationError("spin_period must be a finite positive number")
    return float(value)


def _depth(value: float | None, kind: str | None) -> float | None:
    """校验动画变化幅度。

    Args:
        value: 变化幅度；0 到 1 的数字，不接受 bool；None 表示用默认值
        kind: 最终的动画名称

    Returns:
        pulse、breathe、ping、bounce 返回有效幅度（未给出时为各自默认值）；
        spin 和不动画时为 None。

    Raises:
        InvalidAnimationError: 值不合法，或动画是 spin、None 却给了幅度。
    """
    if kind not in DEFAULT_DEPTHS:
        if value is not None:
            names = ", ".join(repr(name) for name in DEFAULT_DEPTHS)
            raise InvalidAnimationError(
                f"animation_depth only applies to animation in {names}"
            )
        return None
    if value is None:
        return DEFAULT_DEPTHS[kind]
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
    ):
        raise InvalidAnimationError("animation_depth must be between 0 and 1")
    return float(value)


def _period(value: float, name: str) -> float:
    """校验动画周期。

    Args:
        value: 一个周期的秒数；有限正数，不接受 bool
        name: 参数名，用于错误信息

    Returns:
        转为 float 的周期。

    Raises:
        InvalidAnimationError: 值不是数字、是 bool、非有限数或不大于 0。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise InvalidAnimationError(f"{name} must be a finite positive number")
    return float(value)


def _rotation(value: float) -> float:
    """校验旋转角度并归一化到 [0, 360)。

    Args:
        value: 旋转角度，单位为度；有限数字，不接受 bool

    Returns:
        对 360 取模后的角度。

    Raises:
        InvalidRotationError: 值不是数字、是 bool 或非有限数。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise InvalidRotationError("rotate must be a finite number")
    return float(value) % 360.0
