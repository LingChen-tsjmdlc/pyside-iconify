"""图标名解析"""

from __future__ import annotations

import re

from pyside_iconify._errors import InvalidIconNameError
from pyside_iconify.core.types import IconName

_NAME_PART = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def parse_icon_name(value: str | IconName) -> IconName:
    """解析 ``prefix:name`` 格式的图标名。"""
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
