"""公开函数实现。"""

from __future__ import annotations

from collections.abc import Mapping

from pyside_iconify._qt import QFontMetrics, QIcon, QPixmap, QSize

from pyside_iconify._config import (
    get_default_config,
    set_default_config,
    set_disabled_opacity,
)
from pyside_iconify.core.colors import hex_argb, hex_rgba
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.registry import registry
from pyside_iconify.core.sizes import resolve_size
from pyside_iconify.core.svg import collect_paints
from pyside_iconify.core.types import IconData
from pyside_iconify.rendering.cache import pixmap_cache
from pyside_iconify.rendering.engine import create_icon
from pyside_iconify.rendering.options import make_options
from pyside_iconify.rendering.qt_adapter import require_application, require_main_thread


def add_icon(name: str, data: IconData | str, *, replace: bool = False) -> None:
    """注册一个本地图标。

    Args:
        name: 图标名；格式为 ``prefix:name``。
        data: 图标数据；可传 IconData 或 SVG body 字符串。
        replace: 同名图标已存在时是否覆盖；False 时抛出重复注册异常。
    """
    registry.add_icon(name, data, replace=replace)


def add_collection(collection: Mapping[str, object], *, replace: bool = False) -> None:
    """注册一份 Iconify JSON 图标集合。

    Args:
        collection: Iconify JSON 集合（已解析为映射）。
        replace: 集合内存在已注册的同名图标时是否覆盖；False 时抛出重复注册异常。
    """
    registry.add_collection(collection, replace=replace)


def get_icon(
    icon: str | IconData,
    *,
    size: object | None = None,
    color: object | None = None,
    color_light_theme: object | None = None,
    color_dark_theme: object | None = None,
    selected_color: object | None = None,
    selected_color_light_theme: object | None = None,
    selected_color_dark_theme: object | None = None,
    opacity: float | None = None,
    width: object | None = None,
    height: object | None = None,
    rotate: float = 0,
    rotate_overflow: bool = False,
    spin: bool = False,
    h_flip: bool = False,
    v_flip: bool = False,
) -> QIcon:
    """返回可用于任意 Qt 控件的标准 QIcon。

    悬停变色不在这里：裸 QIcon 表达不了悬停（样式对图标
    的 mode 请求不可靠）。按钮悬停用 set_icon(hover_color=...)，
    控件悬停用 IconWidget(hover_color=...)。

    Args:
        icon: 图标名（``prefix:name``）或 IconData；IconData 会按内容注册为内联图标。
        size: 图标尺寸；None 使用默认配置，可传数字、``"16px"``/``"1.5em"`` 字符串或 (宽, 高) 序列。
        color: 通用颜色；None 使用默认配置。
        color_light_theme: 浅色主题下的颜色；None 使用默认配置。
        color_dark_theme: 深色主题下的颜色；None 使用默认配置。
        selected_color: 选中状态的颜色；None 表示不单独指定。
        selected_color_light_theme: 浅色主题下选中状态的颜色；None 表示不单独指定。
        selected_color_dark_theme: 深色主题下选中状态的颜色；None 表示不单独指定。
        opacity: 不透明度；0 到 1，None 使用默认配置。
        width: 单独覆盖宽度；None 沿用 size 的宽度。
        height: 单独覆盖高度；None 沿用 size 的高度。
        rotate: 旋转角度；单位为度，会对 360 取模。
        rotate_overflow: 旋转时是否保持原大小；False 按角度自动缩小以免被裁切，
            True 不缩小，铺满的图标旋转时四角可能被裁掉。
        spin: 是否持续旋转。
        h_flip: 是否水平翻转。
        v_flip: 是否垂直翻转。

    Returns:
        可直接用于 Qt 控件的 QIcon。
    """
    require_application()
    require_main_thread()
    options = make_options(
        size=size,
        color=color,
        color_light_theme=color_light_theme,
        color_dark_theme=color_dark_theme,
        selected_color=selected_color,
        selected_color_light_theme=selected_color_light_theme,
        selected_color_dark_theme=selected_color_dark_theme,
        opacity=opacity,
        width=width,
        height=height,
        spin=spin,
        rotate=rotate,
        rotate_overflow=rotate_overflow,
        h_flip=h_flip,
        v_flip=v_flip,
    )
    name = (
        registry.register_inline(icon)
        if isinstance(icon, IconData)
        else parse_icon_name(icon)
    )
    return create_icon(name, options)


def get_pixmap(
    icon: str | IconData, *, size: object | None = None, **options: object
) -> QPixmap:
    """返回静态 QPixmap。

    Args:
        icon: 图标名（``prefix:name``）或 IconData。
        size: 图标尺寸；None 使用默认配置，em 单位按应用默认字体高度换算。
        **options: 其余渲染选项；取值同 get_icon 的同名参数（如 color、opacity、rotate、h_flip）。

    Returns:
        按解析后的尺寸渲染出的 QPixmap。
    """
    require_application()
    require_main_thread()
    render_options = make_options(size=size, **options)
    font_pixels = QFontMetrics(require_application().font()).height()
    width, height = resolve_size(render_options.size, font_pixels)
    name = (
        registry.register_inline(icon)
        if isinstance(icon, IconData)
        else parse_icon_name(icon)
    )
    qicon = create_icon(name, render_options)
    return qicon.pixmap(QSize(round(width), round(height)))


def get_icon_data(icon: str) -> IconData:
    """返回已注册的图标数据。

    Args:
        icon: 图标名；格式为 ``prefix:name``。

    Returns:
        该图标对应的 IconData。
    """
    return registry.get(icon)


def is_monotone(icon: str) -> bool:
    """判断图标是否只使用 currentColor。

    Args:
        icon: 已注册的图标名。

    Returns:
        图标没有固定颜色时为 True。
    """
    return not collect_paints(registry.get(icon).body)


def get_icon_colors(icon: str) -> tuple[str, ...]:
    """列出图标固定颜色。

    Args:
        icon: 已注册的图标名。

    Returns:
        ``#rrggbb`` 形式的颜色字符串元组；不含 alpha。
    """
    return tuple(
        f"#{color.red:02x}{color.green:02x}{color.blue:02x}"
        for color in collect_paints(registry.get(icon).body)
    )


def set_cache_limits(
    *, pixmap_mib: int | None = None, data_entries: int | None = None
) -> None:
    """调整缓存上限。

    Args:
        pixmap_mib: 像素图缓存上限；单位 MiB，须大于 0，None 表示不修改。
        data_entries: 图标数据缓存的最大条目数，须大于 0，None 表示不修改。
    """
    if data_entries is not None:
        registry.set_limit(data_entries)
    if pixmap_mib is not None:
        if pixmap_mib <= 0:
            raise ValueError("pixmap_mib must be greater than 0")
        pixmap_cache.set_limit_mib(pixmap_mib)


__all__ = [
    "add_collection",
    "add_icon",
    "get_default_config",
    "get_icon",
    "get_icon_colors",
    "get_icon_data",
    "get_pixmap",
    "hex_argb",
    "hex_rgba",
    "is_monotone",
    "set_cache_limits",
    "set_default_config",
    "set_disabled_opacity",
]
