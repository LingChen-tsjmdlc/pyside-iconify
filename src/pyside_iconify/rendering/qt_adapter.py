"""Qt 类型适配和线程检查。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

from PySide6.QtCore import QCoreApplication, QSize, QThread, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

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
    """返回 QApplication，缺失时抛异常。"""
    application = QApplication.instance()
    if application is None:
        raise NoApplicationError("QApplication must exist before using Qt icons")
    return application


def require_main_thread() -> None:
    """确保当前调用位于 Qt 主线程。"""
    application = QCoreApplication.instance()
    if application is not None and QThread.currentThread() != application.thread():
        raise WrongThreadError("Qt icon APIs must be called from the main thread")


def normalize_color(value: ColorScalar) -> RGBA:
    """把 Qt 或公开颜色写法转为 RGBA。"""
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
        color = QColor.fromString(value)
        if not color.isValid():
            raise
        return RGBA(color.red(), color.green(), color.blue(), color.alpha())


def normalize_mapping(value: ColorMapping) -> dict[RGBA | str, RGBA]:
    """把公开颜色映射表规范化。"""
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
    """在公开接口边界立即验证颜色或映射表。"""
    if value is None:
        return None
    if isinstance(value, Mapping):
        return normalize_mapping(value)
    return normalize_color(value)


def normalize_size(value: object) -> SizeSpec:
    """把 QSize 或其它公开尺寸写法转为 SizeSpec。"""
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
    """将内部 RGBA 转为 QColor。"""
    return QColor(color.red, color.green, color.blue, color.alpha)
