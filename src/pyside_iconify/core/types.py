"""核心不可变数据类型"""

from __future__ import annotations

from dataclasses import dataclass
import math

from pyside_iconify._errors import InvalidIconDataError


@dataclass(frozen=True, slots=True)
class IconName:
    """由集合前缀和图标名组成的标准名称。

    Attributes:
        prefix: 图标集合前缀。
        name: 集合内的图标名。
    """

    prefix: str
    name: str

    def __str__(self) -> str:
        """返回 ``prefix:name`` 形式的字符串。"""
        return f"{self.prefix}:{self.name}"


@dataclass(frozen=True, slots=True)
class RGBA:
    """8 位 RGBA 颜色。

    Attributes:
        red: 红色通道；0 到 255。
        green: 绿色通道；0 到 255。
        blue: 蓝色通道；0 到 255。
        alpha: 透明度通道；0 到 255，255 为不透明。
    """

    red: int
    green: int
    blue: int
    alpha: int = 255

    def __post_init__(self) -> None:
        """校验各通道取值范围。"""
        for value in (self.red, self.green, self.blue, self.alpha):
            if not 0 <= value <= 255:
                raise ValueError("RGBA channel must be between 0 and 255")

    @property
    def alpha_fraction(self) -> float:
        """返回 0 到 1 的 alpha。"""
        return self.alpha / 255.0

    def with_alpha_multiplier(self, multiplier: float) -> RGBA:
        """返回乘上透明度后的颜色。

        Args:
            multiplier: 透明度系数；与当前 alpha 相乘，结果限制在 0 到 1。

        Returns:
            alpha 调整后的新 RGBA。
        """
        alpha = round(max(0.0, min(1.0, self.alpha_fraction * multiplier)) * 255)
        return RGBA(self.red, self.green, self.blue, alpha)

    def to_svg(self) -> str:
        """返回 SVG 可用的颜色字符串。

        Returns:
            alpha 为 255 时为 ``#rrggbb``，否则为 ``rgba(r, g, b, a)``。
        """
        if self.alpha == 255:
            return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"
        return f"rgba({self.red}, {self.green}, {self.blue}, {self.alpha_fraction:.6g})"


@dataclass(frozen=True, slots=True)
class SizeSpec:
    """尚未解析为最终逻辑像素的尺寸。

    Attributes:
        width: 宽度数值；单位由 unit 决定。
        height: 高度数值；单位由 unit 决定。
        unit: 尺寸单位；``"px"`` 或 ``"em"``。
    """

    width: float
    height: float
    unit: str = "px"

    @property
    def is_em(self) -> bool:
        """是否依赖字体尺寸。"""
        return self.unit == "em"


@dataclass(frozen=True, slots=True)
class IconData:
    """已规范化的单个图标数据。

    Attributes:
        body: SVG 内容（不含外层 svg 标签），须为非空字符串。
        width: 图标宽度；须为有限正数。
        height: 图标高度；须为有限正数。
        left: viewBox 左边界；须为有限数。
        top: viewBox 上边界；须为有限数。
        rotate: 预设旋转，以 90 度为单位的圈数。
        h_flip: 是否预设水平翻转。
        v_flip: 是否预设垂直翻转。
    """

    body: str
    width: float
    height: float
    left: float = 0.0
    top: float = 0.0
    rotate: int = 0
    h_flip: bool = False
    v_flip: bool = False

    def __post_init__(self) -> None:
        """校验 body 与尺寸字段。

        Raises:
            InvalidIconDataError: body 为空，或尺寸/偏移不是有限数，或宽高不大于 0。
        """
        if not isinstance(self.body, str) or not self.body.strip():
            raise InvalidIconDataError("icon body must be a non-empty string")
        if not all(math.isfinite(value) for value in (self.width, self.height, self.left, self.top)):
            raise InvalidIconDataError("icon dimensions must be finite")
        if self.width <= 0 or self.height <= 0:
            raise InvalidIconDataError("icon width and height must be greater than 0")

    def replace_colors(self, replacements: dict[str, str]) -> IconData:
        """返回替换 SVG 固定颜色后的新图标数据。

        Args:
            replacements: 颜色映射；键为原颜色，值为新颜色，均为可解析的颜色写法。

        Returns:
            body 颜色已替换、其余字段不变的新 IconData。
        """
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
    """一次渲染请求的标准化参数。

    Attributes:
        name: 图标名。
        size: 渲染尺寸。
        rotate: 旋转量。
        h_flip: 是否水平翻转。
        v_flip: 是否垂直翻转。
        opacity: 不透明度；0 到 1。
    """

    name: IconName
    size: SizeSpec
    rotate: float
    h_flip: bool
    v_flip: bool
    opacity: float
