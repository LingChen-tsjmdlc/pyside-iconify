"""Iconify JSON 解析和别名归一化。"""

from __future__ import annotations

from collections.abc import Mapping

from pyside_iconify._errors import InvalidIconDataError, UnsafeIconDataError
from pyside_iconify.core.types import IconData, IconName


def parse_collection(value: Mapping[str, object]) -> dict[IconName, IconData]:
    """解析一份 Iconify JSON 集合。

    图标缺省的尺寸、偏移、旋转和翻转取集合顶层的值；别名会沿 `parent` 链解析并叠加变换。

    Args:
        value: Iconify JSON 集合；须含非空字符串 `prefix` 和对象 `icons`，可含对象 `aliases`。

    Returns:
        以图标名为键、图标数据为值的字典，包含图标和别名。

    Raises:
        InvalidIconDataError: 别名循环、别名目标不存在，或图标/别名名称不是字符串。
    """
    prefix = _text(value.get("prefix"), "prefix")
    defaults = _defaults(value)
    icons_raw = _mapping(value.get("icons"), "icons")
    aliases_raw = _optional_mapping(value.get("aliases"))
    resolved: dict[str, IconData] = {}
    resolving: set[str] = set()

    def resolve(name: str) -> IconData:
        """解析指定名称的图标或别名，并缓存结果。"""
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
    """创建一份本地图标数据。

    Args:
        body: SVG 内容片段；须为非空字符串，且不得含脚本或外部资源引用。
        width: 图标宽度；须为大于 0 的数字。
        height: 图标高度；须为大于 0 的数字。
        left: 视口左边界偏移；可传任意数字。
        top: 视口上边界偏移；可传任意数字。
        rotate: 顺时针旋转的 90 度倍数；整数，按 4 取模。
        h_flip: 是否水平翻转；须为布尔值。
        v_flip: 是否垂直翻转；须为布尔值。

    Returns:
        新建的图标数据。

    Raises:
        InvalidIconDataError: `body` 不是非空字符串。
    """
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
    """读取集合顶层的图标默认值。

    Args:
        value: Iconify JSON 集合；缺省的 `width`/`height` 取 16，`left`/`top`/`rotate` 取 0，`hFlip`/`vFlip` 取 False。

    Returns:
        以 Iconify 字段名为键的默认值字典，不做类型校验。
    """
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
    """用默认值补全并解析单个图标。

    Args:
        value: 单个图标的原始对象；字段优先于默认值，`body` 必填。
        defaults: 集合级默认值，来自 `_defaults`。

    Returns:
        校验后的图标数据。
    """
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
    """在父图标上叠加别名声明的变换。

    旋转量累加后按 4 取模，翻转与父图标异或；别名旋转为奇数时交换宽高与左上偏移。

    Args:
        parent: 父图标数据。
        alias: 别名原始对象；可含 `rotate`、`hFlip`、`vFlip`、`width`、`height`、`left`、`top`，缺省沿用父图标。

    Returns:
        叠加变换后的新图标数据，内容沿用父图标。
    """
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
    """校验图标内容不含脚本和外部资源引用。

    Args:
        body: SVG 内容片段；检查时忽略大小写。

    Raises:
        UnsafeIconDataError: 内容含 `<script`、`javascript:`，或以 http 开头的 href 与 `url(http`。
    """
    lowered = body.lower()
    if "<script" in lowered or "javascript:" in lowered:
        raise UnsafeIconDataError("icon data must not contain scripts")
    if 'href="http' in lowered or "href='http" in lowered or "url(http" in lowered:
        raise UnsafeIconDataError("icon data must not load external resources")


def _mapping(value: object, field: str) -> Mapping[str, object]:
    """要求值为映射对象。

    Args:
        value: 待检查的值。
        field: 字段名，用于错误信息。

    Returns:
        原值。

    Raises:
        InvalidIconDataError: 值不是映射。
    """
    if not isinstance(value, Mapping):
        raise InvalidIconDataError(f"{field} must be an object")
    return value


def _optional_mapping(value: object) -> Mapping[str, object]:
    """读取可选的 `aliases` 映射。

    Args:
        value: `aliases` 字段值；None 表示未提供。

    Returns:
        原映射；未提供时为空字典。
    """
    if value is None:
        return {}
    return _mapping(value, "aliases")


def _text(value: object, field: str) -> str:
    """要求值为非空字符串。

    Args:
        value: 待检查的值。
        field: 字段名，用于错误信息。

    Returns:
        原字符串。

    Raises:
        InvalidIconDataError: 值不是非空字符串。
    """
    if not isinstance(value, str) or not value:
        raise InvalidIconDataError(f"{field} must be a non-empty string")
    return value


def _number(value: object, field: str) -> float:
    """要求值为数字并转为浮点数。

    Args:
        value: 待检查的值；布尔值不被接受。
        field: 字段名，用于错误信息；为 `width` 或 `height` 时要求大于 0。

    Returns:
        浮点数值。

    Raises:
        InvalidIconDataError: 值不是数字，或宽高不大于 0。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidIconDataError(f"{field} must be numeric")
    number = float(value)
    if field in {"width", "height"} and number <= 0:
        raise InvalidIconDataError(f"{field} must be greater than 0")
    return number


def _rotation(value: object) -> int:
    """要求值为整数旋转量并按 4 取模。

    Args:
        value: 顺时针旋转的 90 度倍数；可传整数或整数值的浮点数，布尔值不被接受。

    Returns:
        0 到 3 的旋转量。

    Raises:
        InvalidIconDataError: 值不是整数。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or int(value) != value
    ):
        raise InvalidIconDataError("rotate must be an integer")
    return int(value) % 4


def _boolean(value: object, field: str) -> bool:
    """要求值为布尔值。

    Args:
        value: 待检查的值。
        field: 字段名，用于错误信息。

    Returns:
        原布尔值。

    Raises:
        InvalidIconDataError: 值不是布尔值。
    """
    if not isinstance(value, bool):
        raise InvalidIconDataError(f"{field} must be a boolean")
    return value
