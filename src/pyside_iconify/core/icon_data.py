"""Iconify JSON 解析和别名归一化。"""

from __future__ import annotations

from collections.abc import Mapping

from pyside_iconify._errors import InvalidIconDataError, UnsafeIconDataError
from pyside_iconify.core.types import IconData, IconName


def parse_collection(value: Mapping[str, object]) -> dict[IconName, IconData]:
    """解析一份 Iconify JSON 集合。"""
    prefix = _text(value.get("prefix"), "prefix")
    defaults = _defaults(value)
    icons_raw = _mapping(value.get("icons"), "icons")
    aliases_raw = _optional_mapping(value.get("aliases"))
    resolved: dict[str, IconData] = {}
    resolving: set[str] = set()

    def resolve(name: str) -> IconData:
        if name in resolved:
            return resolved[name]
        if name in resolving:
            raise InvalidIconDataError(f"alias cycle detected: {name}")
        resolving.add(name)
        try:
            raw_icon = icons_raw.get(name)
            if raw_icon is not None:
                icon = _parse_icon(_mapping(raw_icon, f"icons.{name}"), defaults)
            else:
                raw_alias = aliases_raw.get(name)
                if raw_alias is None:
                    raise InvalidIconDataError(f"alias target not found: {name}")
                alias = _mapping(raw_alias, f"aliases.{name}")
                parent = _text(alias.get("parent"), f"aliases.{name}.parent")
                icon = _apply_transform(resolve(parent), alias)
            resolved[name] = icon
            return icon
        finally:
            resolving.remove(name)

    for icon_name in icons_raw:
        if not isinstance(icon_name, str):
            raise InvalidIconDataError("icon name must be a string")
        resolve(icon_name)
    for alias_name in aliases_raw:
        if not isinstance(alias_name, str):
            raise InvalidIconDataError("alias name must be a string")
        resolve(alias_name)
    return {IconName(prefix, name): icon for name, icon in resolved.items()}


def create_icon_data(
    body: str,
    *,
    width: float = 16,
    height: float = 16,
    left: float = 0,
    top: float = 0,
    rotate: int = 0,
    h_flip: bool = False,
    v_flip: bool = False,
) -> IconData:
    """创建一份本地图标数据。"""
    if not isinstance(body, str) or not body.strip():
        raise InvalidIconDataError("icon body must be a non-empty string")
    _validate_body(body)
    return IconData(
        body=body,
        width=_number(width, "width"),
        height=_number(height, "height"),
        left=_number(left, "left"),
        top=_number(top, "top"),
        rotate=_rotation(rotate),
        h_flip=_boolean(h_flip, "h_flip"),
        v_flip=_boolean(v_flip, "v_flip"),
    )


def _defaults(value: Mapping[str, object]) -> dict[str, object]:
    return {
        "width": value.get("width", 16),
        "height": value.get("height", 16),
        "left": value.get("left", 0),
        "top": value.get("top", 0),
        "rotate": value.get("rotate", 0),
        "hFlip": value.get("hFlip", False),
        "vFlip": value.get("vFlip", False),
    }


def _parse_icon(
    value: Mapping[str, object], defaults: Mapping[str, object]
) -> IconData:
    merged = {**defaults, **value}
    body = _text(merged.get("body"), "body")
    _validate_body(body)
    return IconData(
        body=body,
        width=_number(merged.get("width"), "width"),
        height=_number(merged.get("height"), "height"),
        left=_number(merged.get("left"), "left"),
        top=_number(merged.get("top"), "top"),
        rotate=_rotation(merged.get("rotate")),
        h_flip=_boolean(merged.get("hFlip"), "hFlip"),
        v_flip=_boolean(merged.get("vFlip"), "vFlip"),
    )


def _apply_transform(parent: IconData, alias: Mapping[str, object]) -> IconData:
    extra_rotate = _rotation(alias.get("rotate", 0))
    h_flip = parent.h_flip ^ _boolean(alias.get("hFlip", False), "hFlip")
    v_flip = parent.v_flip ^ _boolean(alias.get("vFlip", False), "vFlip")
    rotate = (parent.rotate + extra_rotate) % 4
    width = _number(alias.get("width", parent.width), "width")
    height = _number(alias.get("height", parent.height), "height")
    left = _number(alias.get("left", parent.left), "left")
    top = _number(alias.get("top", parent.top), "top")
    if extra_rotate % 2:
        width, height = height, width
        left, top = top, left
    return IconData(
        body=parent.body,
        width=width,
        height=height,
        left=left,
        top=top,
        rotate=rotate,
        h_flip=h_flip,
        v_flip=v_flip,
    )


def _validate_body(body: str) -> None:
    lowered = body.lower()
    if "<script" in lowered or "javascript:" in lowered:
        raise UnsafeIconDataError("icon data must not contain scripts")
    if 'href="http' in lowered or "href='http" in lowered or "url(http" in lowered:
        raise UnsafeIconDataError("icon data must not load external resources")


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise InvalidIconDataError(f"{field} must be an object")
    return value


def _optional_mapping(value: object) -> Mapping[str, object]:
    if value is None:
        return {}
    return _mapping(value, "aliases")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidIconDataError(f"{field} must be a non-empty string")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidIconDataError(f"{field} must be numeric")
    number = float(value)
    if field in {"width", "height"} and number <= 0:
        raise InvalidIconDataError(f"{field} must be greater than 0")
    return number


def _rotation(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or int(value) != value
    ):
        raise InvalidIconDataError("rotate must be an integer")
    return int(value) % 4


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidIconDataError(f"{field} must be a boolean")
    return value
