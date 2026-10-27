"""Qt 类型适配和线程检查。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

from pyside_iconify._qt import (
    QApplication,
    QColor,
    QCoreApplication,
    QSize,
    Qt,
    QThread,
)

from pyside_iconify._errors import (
    InvalidColorError,
    InvalidSizeError,
    NoApplicationError,
    WrongThreadError,
)
from pyside_iconify.core.colors import parse_color
from pyside_iconify.core.sizes import parse_size
from pyside_iconify.core.types import RGBA, SizeSpec

ColorScalar: TypeAlias = str | Sequence[int | float] | RGBA | QColor | Qt.GlobalColor
ColorMapping: TypeAlias = Mapping[ColorScalar, ColorScalar]
NormalizedColorMapping: TypeAlias = Mapping[RGBA | str, RGBA]
NormalizedColorValue: TypeAlias = RGBA | NormalizedColorMapping
ColorValue: TypeAlias = ColorScalar | ColorMapping


def require_application() -> QApplication:
    """返回当前 QApplication 实例。

    Returns:
        当前的 QApplication。

    Raises:
        NoApplicationError: 尚未创建 QApplication。
    """
    application = QApplication.instance()
    if application is None:
        raise NoApplicationError("QApplication must exist before using Qt icons")
    return application


def require_main_thread() -> None:
    """确保当前调用位于 Qt 主线程。

    没有应用实例时不做检查。

    Raises:
        WrongThreadError: 当前线程不是应用所在的主线程。
    """
    application = QCoreApplication.instance()
    if application is not None and QThread.currentThread() != application.thread():
        raise WrongThreadError("Qt icon APIs must be called from the main thread")


def normalize_color(value: ColorScalar) -> RGBA:
    """把 Qt 或公开颜色写法转为 RGBA。

    先按公开写法解析，字符串解析失败时再尝试 QColor 的命名颜色。

    Args:
        value: 颜色；可传 QColor、Qt.GlobalColor、RGBA、颜色字符串或数值序列

    Returns:
        对应的 RGBA。

    Raises:
        InvalidColorError: QColor 无效，或颜色写法无法解析。
    """
    if isinstance(value, QColor):
        if not value.isValid():
            raise InvalidColorError("QColor is invalid")
        return RGBA(value.red(), value.green(), value.blue(), value.alpha())
    if isinstance(value, Qt.GlobalColor):
        return normalize_color(QColor(value))
    try:
        return parse_color(value)
    except InvalidColorError:
        if not isinstance(value, str):
            raise
        color = _named_color(value)
        if not color.isValid():
            raise
        return RGBA(color.red(), color.green(), color.blue(), color.alpha())


def _named_color(name: str) -> QColor:
    """按 Qt 的命名颜色表解析颜色名（如 "red"、"rebeccapurple"）。

    Qt 6.4 起有 ``QColor.fromString``；更旧的 Qt 只能用构造函数，而无效名字会让
    构造函数向控制台打警告，所以先用 ``isValidColor`` 判断。

    Args:
        name: 颜色名

    Returns:
        对应的 QColor；名字无效时返回无效的 QColor。
    """
    from_string = getattr(QColor, "fromString", None)
    if from_string is not None:
        return from_string(name)
    if QColor.isValidColor(name):
        return QColor(name)
    return QColor()


def normalize_mapping(value: ColorMapping) -> dict[RGBA | str, RGBA]:
    """把公开颜色映射表规范化。

    Args:
        value: 颜色映射表；键为被替换的颜色或 "currentColor"，值为目标颜色

    Returns:
        键为 RGBA 或 "currentColor"、值为 RGBA 的字典。
    """
    result: dict[RGBA | str, RGBA] = {}
    for source, target in value.items():
        key: RGBA | str
        if isinstance(source, str) and source == "currentColor":
            key = "currentColor"
        else:
            key = normalize_color(source)
        result[key] = normalize_color(target)
    return result


def normalize_color_value(value: ColorValue | None) -> NormalizedColorValue | None:
    """在公开接口边界立即验证颜色或映射表。

    Args:
        value: 单个颜色、颜色映射表或 None

    Returns:
        RGBA、规范化后的映射表；传入 None 时返回 None。
    """
    if value is None:
        return None
    if isinstance(value, Mapping):
        return normalize_mapping(value)
    return normalize_color(value)


def normalize_size(value: object) -> SizeSpec:
    """把 QSize 或其它公开尺寸写法转为 SizeSpec。

    Args:
        value: 尺寸；可传 SizeSpec、QSize（宽高须为正）、数字、字符串、元组或列表

    Returns:
        对应的 SizeSpec。

    Raises:
        InvalidSizeError: QSize 宽高不为正，或类型不受支持。
    """
    if isinstance(value, SizeSpec):
        return value
    if isinstance(value, QSize):
        if value.width() <= 0 or value.height() <= 0:
            raise InvalidSizeError("QSize dimensions must be positive")
        return parse_size((value.width(), value.height()))
    if isinstance(value, (int, float, str, tuple, list)):
        return parse_size(value)
    raise InvalidSizeError(f"cannot parse size: {value!r}")


def to_qcolor(color: RGBA) -> QColor:
    """将内部 RGBA 转为 QColor。

    Args:
        color: 内部 RGBA 颜色

    Returns:
        对应的 QColor。
    """
    return QColor(color.red, color.green, color.blue, color.alpha)
