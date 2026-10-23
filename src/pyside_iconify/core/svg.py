"""SVG 合成和颜色替换。"""

from __future__ import annotations

import re
from collections.abc import Mapping

from pyside_iconify._errors import InvalidColorError
from pyside_iconify.core.colors import parse_color
from pyside_iconify.core.types import IconData, RGBA

_PAINT_ATTRIBUTE = re.compile(r"\b(fill|stroke)\s*=\s*([\"'])(.*?)\2", re.IGNORECASE)
_PAINT_STYLE = re.compile(r"\b(fill|stroke)\s*:\s*([^;\"']+)", re.IGNORECASE)
_NON_PAINT = {"none", "transparent", "inherit", "context-fill", "context-stroke"}


def build_svg(
    data: IconData,
    *,
    color: RGBA | None = None,
    colors: Mapping[object, RGBA] | None = None,
) -> str:
    """合成完整 SVG 文档。

    先改写绘制颜色，再按旋转与翻转包一层 `<g transform>`，最后以图标视口作为 viewBox。

    Args:
        data: 图标数据。
        color: 替换 `currentColor` 的颜色；可传 RGBA 或 None（不替换）。
        colors: 颜色替换表；键为被替换的 RGBA 颜色或 `"currentColor"`，值为目标颜色。`"currentColor"` 的映射优先于 `color`。

    Returns:
        完整的 SVG 文本。
    """
    tint = colors.get("currentColor") if colors else None
    if tint is None:
        tint = color
    body = rewrite_paints(data.body, tint, colors)
    transform = _transform(data)
    if transform:
        body = f'<g transform="{transform}">{body}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_view_box(data)}">{body}</svg>'
    )


def _view_box(data: IconData) -> str:
    """生成 viewBox 属性值，格式为“左 上 宽 高”。

    Args:
        data: 图标数据。

    Returns:
        viewBox 文本。
    """
    return f"{data.left:g} {data.top:g} {data.width:g} {data.height:g}"


def replace_colors(body: str, replacements: Mapping[object, RGBA]) -> str:
    """替换 SVG 内容里的固定绘制颜色。

    Args:
        body: SVG 内容片段。
        replacements: 颜色替换表；键为被替换的 RGBA 颜色，值为目标颜色。

    Returns:
        替换后的 SVG 内容片段。
    """
    return rewrite_paints(body, None, replacements)


def rewrite_paints(
    body: str,
    tint: RGBA | None,
    replacements: Mapping[object, RGBA] | None,
) -> str:
    """将绘制颜色规范为 Qt 可渲染的值。

    处理 `fill`/`stroke` 的属性和 style 写法，颜色统一输出为 `#rrggbb`，不透明度拆成 `*-opacity`。
    `none`、`url(...)` 等非纯色值以及无法解析的值保持不变。

    Args:
        body: SVG 内容片段。
        tint: 替换 `currentColor` 的颜色；可传 RGBA 或 None（保持 `currentColor` 不变）。
        replacements: 颜色替换表；键为被替换的 RGBA 颜色，值为目标颜色；可传 None。

    Returns:
        改写后的 SVG 内容片段。
    """

    def attribute(match: re.Match[str]) -> str:
        """改写一处 fill/stroke 属性写法的颜色。"""
        name, quote, value = match.group(1), match.group(2), match.group(3)
        resolved = _resolve_paint(value, tint, replacements)
        if resolved is None:
            return match.group(0)
        opacity = f" {name}-opacity={quote}{_alpha(resolved)}{quote}" if resolved.alpha != 255 else ""
        return f"{name}={quote}{_hex(resolved)}{quote}{opacity}"

    def style(match: re.Match[str]) -> str:
        """改写一处 style 内 fill/stroke 声明的颜色。"""
        name, value = match.group(1), match.group(2).strip()
        resolved = _resolve_paint(value, tint, replacements)
        if resolved is None:
            return match.group(0)
        opacity = f";{name}-opacity:{_alpha(resolved)}" if resolved.alpha != 255 else ""
        return f"{name}:{_hex(resolved)}{opacity}"

    body = _PAINT_ATTRIBUTE.sub(attribute, body)
    return _PAINT_STYLE.sub(style, body)


def collect_paints(body: str) -> tuple[RGBA, ...]:
    """列出 SVG 内容使用的固定绘制颜色。

    Args:
        body: SVG 内容片段。

    Returns:
        按首次出现顺序去重的颜色元组；不含 `currentColor`、`none`、`url(...)` 和无法解析的值。
    """
    found: dict[RGBA, None] = {}
    for match in _PAINT_ATTRIBUTE.finditer(body):
        _record(match.group(3), found)
    for match in _PAINT_STYLE.finditer(body):
        _record(match.group(2), found)
    return tuple(found)


def _record(value: str, found: dict[RGBA, None]) -> None:
    """把可解析的固定颜色记入有序集合。

    Args:
        value: fill 或 stroke 的原始取值；`currentColor`、`url(...)`、非纯色关键字和无法解析的值会被忽略。
        found: 以颜色为键的有序字典，原地更新。
    """
    text = value.strip()
    if not text or text == "currentColor" or text.startswith("url(") or text.lower() in _NON_PAINT:
        return
    try:
        found[parse_color(text)] = None
    except InvalidColorError:
        return


def _resolve_paint(
    value: str,
    tint: RGBA | None,
    replacements: Mapping[object, RGBA] | None,
) -> RGBA | None:
    """计算单个绘制值改写后的颜色。

    Args:
        value: fill 或 stroke 的原始取值。
        tint: 替换 `currentColor` 的颜色；可传 RGBA 或 None。
        replacements: 颜色替换表；键为源 RGBA 颜色，值为目标颜色；可传 None。

    Returns:
        改写后的颜色；值为空、`url(...)`、非纯色关键字、无法解析，或为 `currentColor` 且 `tint` 为 None 时返回 None，表示保持原样。
    """
    text = value.strip()
    if not text or text.startswith("url(") or text.lower() in _NON_PAINT:
        return None
    if text == "currentColor":
        return tint
    try:
        source = parse_color(text)
    except InvalidColorError:
        return None
    if replacements:
        target = replacements.get(source)
        if isinstance(target, RGBA):
            return target
    return source


def _hex(color: RGBA) -> str:
    """将颜色格式化为不含透明度的 `#rrggbb` 文本。"""
    return f"#{color.red:02x}{color.green:02x}{color.blue:02x}"


def _alpha(color: RGBA) -> str:
    """将颜色的透明度格式化为 0 到 1 的小数文本。"""
    return f"{color.alpha_fraction:.6g}"


def _transform(data: IconData) -> str:
    """生成旋转与翻转对应的 SVG transform 属性值。

    Args:
        data: 图标数据；`rotate` 为 90 度的倍数，`h_flip`/`v_flip` 为翻转标志。

    Returns:
        以空格连接的 transform 列表；无旋转和翻转时为空字符串。
    """
    transforms: list[str] = []
    source_center_x = data.left + (data.height if data.rotate % 2 else data.width) / 2
    source_center_y = data.top + (data.width if data.rotate % 2 else data.height) / 2
    if data.rotate:
        transforms.append(f"rotate({data.rotate * 90:g} {source_center_x:g} {source_center_y:g})")
    if data.h_flip:
        transforms.append(f"translate({2 * source_center_x:g} 0) scale(-1 1)")
    if data.v_flip:
        transforms.append(f"translate(0 {2 * source_center_y:g}) scale(1 -1)")
    return " ".join(transforms)
