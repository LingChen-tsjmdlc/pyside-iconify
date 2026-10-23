"""图标名解析"""

from __future__ import annotations

import re

from pyside_iconify._errors import InvalidIconNameError
from pyside_iconify.core.types import IconName

_NAME_PART = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def parse_icon_name(value: str | IconName) -> IconName:
    """解析 ``prefix:name`` 格式的图标名。

    prefix 与 name 都只能由小写字母、数字和连字符组成，且以字母或数字开头。

    Args:
        value: 图标名字符串或已解析的 IconName；字符串首尾空白会被去除。

    Returns:
        标准化后的 IconName。

    Raises:
        InvalidIconNameError: 不是字符串，或不符合 ``prefix:name`` 格式。
    """
    if isinstance(value, IconName):
        return value
    if not isinstance(value, str):
        raise InvalidIconNameError("icon name must be a 'prefix:name' string")
    prefix, separator, name = value.strip().partition(":")
    if (
        not separator
        or not _NAME_PART.fullmatch(prefix)
        or not _NAME_PART.fullmatch(name)
    ):
        raise InvalidIconNameError(f"invalid icon name: {value!r}")
    return IconName(prefix, name)
