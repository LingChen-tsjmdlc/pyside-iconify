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
    """合成完整 SVG 文档。"""
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
    return f"{data.left:g} {data.top:g} {data.width:g} {data.height:g}"


def replace_colors(body: str, replacements: Mapping[object, RGBA]) -> str:
    """替换 SVG 内容里的固定绘制颜色。"""
    return rewrite_paints(body, None, replacements)


def rewrite_paints(
    body: str,
    tint: RGBA | None,
    replacements: Mapping[object, RGBA] | None,
) -> str:
    """将绘制颜色规范为 Qt 可渲染的值。"""

    def attribute(match: re.Match[str]) -> str:
        name, quote, value = match.group(1), match.group(2), match.group(3)
        resolved = _resolve_paint(value, tint, replacements)
        if resolved is None:
            return match.group(0)
        opacity = f" {name}-opacity={quote}{_alpha(resolved)}{quote}" if resolved.alpha != 255 else ""
        return f"{name}={quote}{_hex(resolved)}{quote}{opacity}"

    def style(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2).strip()
        resolved = _resolve_paint(value, tint, replacements)
        if resolved is None:
            return match.group(0)
        opacity = f";{name}-opacity:{_alpha(resolved)}" if resolved.alpha != 255 else ""
        return f"{name}:{_hex(resolved)}{opacity}"

    body = _PAINT_ATTRIBUTE.sub(attribute, body)
    return _PAINT_STYLE.sub(style, body)


def collect_paints(body: str) -> tuple[RGBA, ...]:
    """列出 SVG 内容使用的固定绘制颜色。"""
    found: dict[RGBA, None] = {}
    for match in _PAINT_ATTRIBUTE.finditer(body):
        _record(match.group(3), found)
    for match in _PAINT_STYLE.finditer(body):
        _record(match.group(2), found)
    return tuple(found)


def _record(value: str, found: dict[RGBA, None]) -> None:
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
    return f"#{color.red:02x}{color.green:02x}{color.blue:02x}"


def _alpha(color: RGBA) -> str:
    return f"{color.alpha_fraction:.6g}"


def _transform(data: IconData) -> str:
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
