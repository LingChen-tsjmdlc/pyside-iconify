"""本地图标注册表"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from hashlib import sha256
from threading import RLock

from pyside_iconify._errors import (
    DuplicateIconError,
    IconNotFoundError,
    InvalidIconDataError,
)
from pyside_iconify.core.icon_data import create_icon_data, parse_collection
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.types import IconData, IconName


class IconRegistry:
    """保存已注册 Iconify 数据的线程安全注册表。"""

    def __init__(self) -> None:
        """创建空的注册表。"""
        self._items: OrderedDict[IconName, IconData] = OrderedDict()
        self._versions: dict[IconName, int] = {}
        self._pending: set[IconName] = set()
        self._limit: int | None = None
        self._lock = RLock()

    def add_icon(
        self, name: str | IconName, data: IconData | str, *, replace: bool = False
    ) -> None:
        """注册一个图标。

        data 为字符串且 replace 为 True、同名图标已存在时，沿用旧图标的尺寸与翻转等元数据，只替换 body。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。
            data: 图标数据；可传 IconData 或 SVG body 字符串。
            replace: 同名图标已存在时是否覆盖。

        Raises:
            InvalidIconDataError: data 既不是 IconData 也不是字符串。
            DuplicateIconError: 同名图标已存在且 replace 为 False。
        """
        icon_name = parse_icon_name(name)
        if isinstance(data, str):
            with self._lock:
                existing = self._items.get(icon_name)
            if replace and existing is not None:
                icon_data = create_icon_data(
                    data,
                    width=existing.width,
                    height=existing.height,
                    left=existing.left,
                    top=existing.top,
                    rotate=existing.rotate,
                    h_flip=existing.h_flip,
                    v_flip=existing.v_flip,
                )
            else:
                icon_data = create_icon_data(data)
        elif isinstance(data, IconData):
            icon_data = create_icon_data(
                data.body,
                width=data.width,
                height=data.height,
                left=data.left,
                top=data.top,
                rotate=data.rotate,
                h_flip=data.h_flip,
                v_flip=data.v_flip,
            )
        else:
            raise InvalidIconDataError("icon data must be IconData or an SVG body string")
        with self._lock:
            if icon_name in self._items and not replace:
                raise DuplicateIconError(f"icon already exists: {icon_name}")
            self._items[icon_name] = icon_data
            self._pending.discard(icon_name)
            self._items.move_to_end(icon_name)
            self._versions[icon_name] = self._versions.get(icon_name, 0) + 1
            self._trim()

    def add_collection(
        self, collection: Mapping[str, object], *, replace: bool = False
    ) -> None:
        """注册一份 Iconify JSON 集合。

        Args:
            collection: Iconify JSON 集合（已解析为映射）。
            replace: 集合内存在已注册的同名图标时是否覆盖。

        Raises:
            DuplicateIconError: 存在已注册的同名图标且 replace 为 False。
        """
        parsed = parse_collection(collection)
        with self._lock:
            duplicates = [name for name in parsed if name in self._items]
            if duplicates and not replace:
                names = ", ".join(map(str, duplicates))
                raise DuplicateIconError(f"icons already exist: {names}")
            for name, data in parsed.items():
                self._items[name] = data
                self._pending.discard(name)
                self._items.move_to_end(name)
                self._versions[name] = self._versions.get(name, 0) + 1
            self._trim()

    def register_inline(self, data: IconData) -> IconName:
        """注册可复用的内联图标并返回内部名称。

        相同内容的 IconData 会得到同一个名称，不会重复注册。

        Args:
            data: 内联图标数据。

        Returns:
            ``inline:<内容摘要>`` 形式的 IconName。
        """
        digest = sha256(repr(data).encode("utf-8")).hexdigest()[:16]
        name = IconName("inline", digest)
        with self._lock:
            if name not in self._items:
                self._items[name] = data
                self._versions[name] = 1
                self._trim()
            self._items.move_to_end(name)
            return name

    def get(self, name: str | IconName) -> IconData:
        """返回已注册图标，并将其标记为最近使用。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。

        Returns:
            该图标的 IconData。

        Raises:
            IconNotFoundError: 图标未注册。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            try:
                self._items.move_to_end(icon_name)
                return self._items[icon_name]
            except KeyError as error:
                raise IconNotFoundError(f"icon not found: {icon_name}") from error

    def version(self, name: str | IconName) -> int:
        """返回图标数据版本。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。

        Returns:
            版本号；每次重新注册会递增。

        Raises:
            IconNotFoundError: 图标未注册。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            if icon_name not in self._items:
                raise IconNotFoundError(f"icon not found: {icon_name}")
            return self._versions[icon_name]

    def contains(self, name: str | IconName) -> bool:
        """判断图标是否已注册。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。

        Returns:
            已注册为 True。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            return icon_name in self._items

    def mark_pending(self, name: str | IconName) -> None:
        """标记图标数据正在加载。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            self._pending.add(icon_name)

    def is_pending(self, name: str | IconName) -> bool:
        """判断图标数据是否正在加载。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。

        Returns:
            已被标记为加载中为 True。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            return icon_name in self._pending

    def clear_pending(self, name: str | IconName) -> None:
        """解除图标的加载中标记。

        Args:
            name: 图标名；可传 ``prefix:name`` 字符串或 IconName。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            self._pending.discard(icon_name)

    def set_limit(self, entries: int | None) -> None:
        """设置数据缓存上限，超出时按最近最少使用淘汰。

        Args:
            entries: 最大条目数，须大于 0；None 表示不限制。
        """
        if entries is not None and entries <= 0:
            raise ValueError("data_entries must be greater than 0")
        with self._lock:
            self._limit = entries
            self._trim()

    def _trim(self) -> None:
        """淘汰最久未使用的图标，直到条目数不超过上限。"""
        while self._limit is not None and len(self._items) > self._limit:
            name, _ = self._items.popitem(last=False)
            self._versions.pop(name, None)

    def clear(self) -> None:
        """清空注册表。"""
        with self._lock:
            self._items.clear()
            self._versions.clear()
            self._pending.clear()


registry = IconRegistry()
