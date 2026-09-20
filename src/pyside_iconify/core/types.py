"""核心不可变数据类型"""

from __future__ import annotations

from dataclasses import dataclass
import math

from pyside_iconify._errors import InvalidIconDataError


@dataclass(frozen=True, slots=True)
class IconName:
    """由集合前缀和图标名组成的标准名称。"""

    prefix: str
    name: str

    def __str__(self) -> str:
        return f"{self.prefix}:{self.name}"


@dataclass(frozen=True, slots=True)
class RGBA:
    """8 位 RGBA 颜色。"""

    red: int
    green: int
    blue: int
    alpha: int = 255

    def __post_init__(self) -> None:
        for value in (self.red, self.green, self.blue, self.alpha):
            if not 0 <= value <= 255:
                raise ValueError("RGBA channel must be between 0 and 255")

    @property
    def alpha_fraction(self) -> float:
        """返回 0 到 1 的 alpha。"""
        return self.alpha / 255.0

    def with_alpha_multiplier(self, multiplier: float) -> RGBA:
        """返回乘上透明度后的颜色。"""
        alpha = round(max(0.0, min(1.0, self.alpha_fraction * multiplier)) * 255)
        return RGBA(self.red, self.green, self.blue, alpha)

    def to_svg(self) -> str:
        """返回 CSS RGBA 字符串。"""
        if self.alpha == 255:
            return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"
        return f"rgba({self.red}, {self.green}, {self.blue}, {self.alpha_fraction:.6g})"


@dataclass(frozen=True, slots=True)
class SizeSpec:
    """尚未解析为最终逻辑像素的尺寸。"""

    width: float
    height: float
    unit: str = "px"

    @property
    def is_em(self) -> bool:
        """是否依赖字体尺寸。"""
        return self.unit == "em"


@dataclass(frozen=True, slots=True)
class IconData:
    """已规范化的单个图标数据。"""

    body: str
    width: float
    height: float
    left: float = 0.0
    top: float = 0.0
    rotate: int = 0
    h_flip: bool = False
    v_flip: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.body, str) or not self.body.strip():
            raise InvalidIconDataError("icon body must be a non-empty string")
        if not all(math.isfinite(value) for value in (self.width, self.height, self.left, self.top)):
            raise InvalidIconDataError("icon dimensions must be finite")
        if self.width <= 0 or self.height <= 0:
            raise InvalidIconDataError("icon width and height must be greater than 0")

    def replace_colors(self, replacements: dict[str, str]) -> IconData:
        """返回替换 SVG 固定颜色后的新图标数据。"""
        from pyside_iconify.core.colors import parse_color
        from pyside_iconify.core.svg import replace_colors

        normalized = {
            parse_color(source): parse_color(target)
            for source, target in replacements.items()
        }
        return IconData(
            body=replace_colors(self.body, normalized),
            width=self.width,
            height=self.height,
            left=self.left,
            top=self.top,
            rotate=self.rotate,
            h_flip=self.h_flip,
            v_flip=self.v_flip,
        )


@dataclass(frozen=True, slots=True)
class IconRequest:
    """一次渲染请求的标准化参数。"""

    name: IconName
    size: SizeSpec
    rotate: float
    h_flip: bool
    v_flip: bool
    opacity: float
