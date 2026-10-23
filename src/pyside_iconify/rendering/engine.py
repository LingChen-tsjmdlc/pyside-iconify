"""标准 QIcon 使用的自定义绘制引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from collections.abc import Mapping

from PySide6.QtCore import QSize, Qt, QRectF
from PySide6.QtGui import QIcon, QIconEngine, QPalette, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from pyside_iconify._errors import (
    IconNotFoundError,
    InvalidIconNameError,
    UnsupportedSvgError,
)
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.registry import registry
from pyside_iconify.core.types import IconName, RGBA, SizeSpec
from pyside_iconify.rendering.placeholder import create_placeholder
from pyside_iconify.rendering.qt_adapter import (
    NormalizedColorValue,
    require_main_thread,
)
from pyside_iconify.rendering.renderer import render_pixmap


@dataclass(frozen=True, slots=True)
class IconOptions:
    """图标渲染选项。

    Attributes:
        size: 图标尺寸；em 尺寸时跟随请求尺寸，否则为固定宽高
        color: 基础颜色；None 时使用调色板文本色
        color_light_theme: 浅色主题下的基础颜色；None 时回退到 color
        color_dark_theme: 深色主题下的基础颜色；None 时回退到 color
        hover_color: 悬停（Active 模式）颜色；None 表示不变色
        hover_color_light_theme: 浅色主题下的悬停颜色；None 时回退到 hover_color
        hover_color_dark_theme: 深色主题下的悬停颜色；None 时回退到 hover_color
        selected_color: 选中（Selected 模式）颜色；None 表示不变色
        selected_color_light_theme: 浅色主题下的选中颜色；None 时回退到 selected_color
        selected_color_dark_theme: 深色主题下的选中颜色；None 时回退到 selected_color
        opacity: 整体不透明度；0 到 1
        disabled_opacity: 禁用模式下额外乘上的不透明度；0 到 1
        spin: 是否持续旋转
        spin_period: 旋转一周的秒数；正数
        rotate: 固定旋转角度；单位为度
        h_flip: 是否水平翻转
        v_flip: 是否垂直翻转
    """

    size: SizeSpec
    color: NormalizedColorValue | None
    color_light_theme: NormalizedColorValue | None
    color_dark_theme: NormalizedColorValue | None
    hover_color: NormalizedColorValue | None
    hover_color_light_theme: NormalizedColorValue | None
    hover_color_dark_theme: NormalizedColorValue | None
    selected_color: NormalizedColorValue | None
    selected_color_light_theme: NormalizedColorValue | None
    selected_color_dark_theme: NormalizedColorValue | None
    opacity: float
    disabled_opacity: float
    spin: bool
    spin_period: float
    rotate: float
    h_flip: bool
    v_flip: bool


class IconEngine(QIconEngine):
    """按当前注册表数据绘制图标的 QIconEngine。"""

    def __init__(
        self,
        name: IconName,
        options: IconOptions,
        *,
        state_mode: str | None = None,
    ) -> None:
        """创建图标引擎。

        Args:
            name: 图标名称
            options: 渲染选项
            state_mode: 固定状态模式；可传 "normal"（始终用常态色）、"hover"（始终用悬停/选中强调色）或 None（按 QIcon 模式）
        """
        super().__init__()
        self._name = name
        self._options = options
        # 事件驱动悬停用：按钮样式对图标永远请求 Active，
        # 无法靠 QIcon mode 表达悬停，改为外部切换两个固定状态的图标。
        # "normal" 永远用常态色，"hover" 永远用悬停/选中强调色。
        self._state_mode = state_mode

    def clone(self) -> QIconEngine:
        """返回使用相同名称、选项和状态模式的新引擎。

        Returns:
            新的 IconEngine 实例。
        """
        return IconEngine(self._name, self._options, state_mode=self._state_mode)

    def key(self) -> str:
        """返回供 QIcon 缓存使用的引擎键。

        键包含图标名称、数据版本和悬停/选中配置。

        Returns:
            形如 "pyside_iconify/名称/版本/状态" 的字符串。
        """
        # 版本参与 key，数据更新后 QIcon 内部缓存才会失效。
        try:
            version = registry.version(self._name)
        except IconNotFoundError:
            version = "pending"
        # 状态色参与 key：QIcon 的 pixmap 缓存按 key 索引，
        # hover/selected 配置不同就必须是不同的 key。
        options = self._options
        state_key = repr(
            (
                options.hover_color,
                options.hover_color_light_theme,
                options.hover_color_dark_theme,
                options.selected_color,
                options.selected_color_light_theme,
                options.selected_color_dark_theme,
                self._state_mode,
            )
        )
        return f"pyside_iconify/{self._name}/{version}/{state_key}"

    def actualSize(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QSize:
        """返回图标实际尺寸。

        Args:
            size: 请求的尺寸
            mode: 图标模式（此处未使用）
            state: 图标状态（此处未使用）

        Returns:
            em 尺寸时返回请求尺寸，否则返回选项里的固定尺寸（四舍五入取整）。
        """
        if self._options.size.is_em:
            return size
        return QSize(round(self._options.size.width), round(self._options.size.height))

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        """按缩放比 1.0 渲染位图。

        Args:
            size: 目标逻辑尺寸
            mode: 图标模式，决定颜色与禁用不透明度
            state: 图标状态（此处未使用）

        Returns:
            渲染得到的 QPixmap。
        """
        return self.scaledPixmap(size, mode, state, 1.0)

    def paint(self, painter: QPainter, rect: QRectF, mode: QIcon.Mode, state: QIcon.State) -> None:
        """在目标矩形内绘制图标，item view 等通过 QIcon.paint() 绘制时走这里。

        Args:
            painter: 目标画笔；其设备的像素比决定渲染缩放比
            rect: 绘制的目标矩形
            mode: 图标模式，决定颜色与禁用不透明度
            state: 图标状态（此处未使用）
        """
        device = painter.device()
        ratio = device.devicePixelRatioF() if device is not None else 1.0
        size = QSize(max(1, round(rect.width())), max(1, round(rect.height())))
        pixmap = self.scaledPixmap(size, mode, state, ratio)
        painter.drawPixmap(QRectF(rect), pixmap, QRectF(pixmap.rect()))

    def scaledPixmap(
        self, size: QSize, mode: QIcon.Mode, state: QIcon.State, scale: float
    ) -> QPixmap:
        """按设备像素比渲染位图。

        图标仍在加载时返回空白位图；加载失败时使用配置的 fallback 图标，
        fallback 也不可用或 SVG 不受支持时返回问号占位图。

        Args:
            size: 目标逻辑尺寸
            mode: 图标模式，决定颜色与禁用不透明度
            state: 图标状态（此处未使用）
            scale: 设备像素比

        Returns:
            渲染得到的 QPixmap。
        """
        require_main_thread()
        width = max(1, size.width())
        height = max(1, size.height())
        render_name = self._name
        if registry.is_pending(render_name):
            from pyside_iconify.rendering.placeholder import create_blank

            return create_blank(width, height, scale)
        try:
            data = registry.get(render_name)
            version = registry.version(render_name)
        except IconNotFoundError:
            from pyside_iconify.network import client as _network

            client = _network.default_client()
            client.ensure_loaded(render_name)
            if registry.is_pending(render_name):
                from pyside_iconify.rendering.placeholder import create_blank

                return create_blank(width, height, scale)
            from pyside_iconify._config import get_default_config

            fallback = get_default_config().fallback
            if fallback is None:
                return create_placeholder(width, height, scale)
            try:
                render_name = parse_icon_name(fallback)
                data = registry.get(render_name)
                version = registry.version(render_name)
            except (IconNotFoundError, InvalidIconNameError):
                return create_placeholder(width, height, scale)
        if self._state_mode == "normal" and mode in (
            QIcon.Mode.Active,
            QIcon.Mode.Selected,
        ):
            mode = QIcon.Mode.Normal
        elif self._state_mode == "hover" and mode != QIcon.Mode.Disabled:
            mode = QIcon.Mode.Active
        color, colors = _resolve_colors(self._options, mode)
        disabled = (
            self._options.disabled_opacity if mode == QIcon.Mode.Disabled else 1.0
        )
        opacity = self._options.opacity * disabled
        spin_angle = (
            round((monotonic() / self._options.spin_period * 360.0) / 5.0) * 5.0
            if self._options.spin
            else 0.0
        )
        rotate = (self._options.rotate + spin_angle) % 360.0
        key = _cache_key(
            render_name,
            version,
            width,
            height,
            scale,
            color,
            colors,
            opacity,
            self._options,
            rotate,
        )
        try:
            return render_pixmap(
                cache_key=key,
                data=data,
                width=width,
                height=height,
                device_pixel_ratio=scale,
                color=color,
                colors=colors,
                opacity=opacity,
                rotate=rotate,
                h_flip=self._options.h_flip,
                v_flip=self._options.v_flip,
                stable_scale=self._options.spin,
            )
        except UnsupportedSvgError:
            return create_placeholder(width, height, scale)


def create_icon(name: IconName, options: IconOptions) -> QIcon:
    """用自定义引擎创建标准 QIcon。

    Args:
        name: 图标名称；尚未加载时会预触发加载
        options: 渲染选项

    Returns:
        由 IconEngine 驱动的 QIcon。
    """
    require_main_thread()
    # 构造即预触发加载：目标（树节点、菜单项）可能迟迟不绘制，
    # 等首次绘制才请求会拖慢图标出现。
    if not registry.contains(name) and not registry.is_pending(name):
        from pyside_iconify.network.client import default_client

        default_client().ensure_loaded(name)
    return QIcon(IconEngine(name, options))


def _resolve_colors(
    options: IconOptions,
    mode: QIcon.Mode = QIcon.Mode.Normal,
) -> tuple[RGBA | None, Mapping[object, RGBA] | None]:
    """按主题和图标模式解析最终颜色。

    Args:
        options: 渲染选项
        mode: 图标模式；Active 取悬停色，Selected 取选中色，其余用基础色

    Returns:
        (单色, 颜色映射表)，两者至多一个非 None。
    """
    selected = _select_theme_color(options)
    if selected is None:
        palette = QApplication.palette()
        from pyside_iconify.rendering.qt_adapter import normalize_color

        selected = normalize_color(palette.color(QPalette.ColorRole.WindowText))
    if mode in (QIcon.Mode.Active, QIcon.Mode.Selected):
        override = _select_state_color(options, mode)
        if override is not None:
            selected = override
        # 不写 hover/selected 参数时不做任何变化：
        # 悬停/选中变色是显式启用的功能。
    if isinstance(selected, Mapping):
        return None, selected
    return selected, None


def _select_state_color(
    options: IconOptions, mode: QIcon.Mode
) -> NormalizedColorValue | None:
    """按图标模式选择悬停色或选中色。

    Args:
        options: 渲染选项
        mode: 图标模式；Active 取悬停色，其余取选中色

    Returns:
        对应的颜色值，未配置时为 None。
    """
    dark = _is_dark_theme()
    if mode == QIcon.Mode.Active:
        return _select_hover_color(options, dark)
    return _select_selected_color(options, dark)


def _select_hover_color(
    options: IconOptions, dark: bool
) -> NormalizedColorValue | None:
    """按主题选择悬停色。

    Args:
        options: 渲染选项
        dark: 当前是否为深色主题

    Returns:
        主题专属悬停色，缺省时为通用悬停色，均未配置则为 None。
    """
    if dark and options.hover_color_dark_theme is not None:
        return options.hover_color_dark_theme
    if not dark and options.hover_color_light_theme is not None:
        return options.hover_color_light_theme
    return options.hover_color


def _select_selected_color(
    options: IconOptions, dark: bool
) -> NormalizedColorValue | None:
    """按主题选择选中色。

    Args:
        options: 渲染选项
        dark: 当前是否为深色主题

    Returns:
        主题专属选中色，缺省时为通用选中色，均未配置则为 None。
    """
    if dark and options.selected_color_dark_theme is not None:
        return options.selected_color_dark_theme
    if not dark and options.selected_color_light_theme is not None:
        return options.selected_color_light_theme
    return options.selected_color


def _is_dark_theme() -> bool:
    """判断当前调色板是否为深色主题。

    Returns:
        窗口背景亮度低于 128 时为 True。
    """
    palette = QApplication.palette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


def _select_theme_color(options: IconOptions) -> ColorValue | None:
    """按主题选择基础颜色。

    Args:
        options: 渲染选项

    Returns:
        主题专属基础色，缺省时为通用基础色，均未配置则为 None。
    """
    palette = QApplication.palette()
    window = palette.color(QPalette.ColorRole.Window)
    dark = window.lightness() < 128
    if dark and options.color_dark_theme is not None:
        return options.color_dark_theme
    if not dark and options.color_light_theme is not None:
        return options.color_light_theme
    return options.color


def _cache_key(
    name: IconName,
    version: int,
    width: int,
    height: int,
    scale: float,
    color: RGBA | None,
    colors: Mapping[object, RGBA] | None,
    opacity: float,
    options: IconOptions,
    rotate: float,
) -> str:
    """生成位图缓存键。

    Args:
        name: 图标名称
        version: 图标数据版本
        width: 逻辑宽度
        height: 逻辑高度
        scale: 设备像素比
        color: 单色；映射表模式下为 None
        colors: 颜色映射表；单色模式下为 None
        opacity: 最终不透明度
        options: 渲染选项，取其中的水平/垂直翻转
        rotate: 最终旋转角度，单位为度

    Returns:
        参数摘要的 SHA-256 十六进制字符串。
    """
    text = repr(
        (
            str(name),
            version,
            width,
            height,
            scale,
            color,
            tuple(sorted((colors or {}).items(), key=repr)),
            opacity,
            rotate,
            options.h_flip,
            options.v_flip,
        )
    )
    return sha256(text.encode("utf-8")).hexdigest()
