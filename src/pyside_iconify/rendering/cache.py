"""位图缓存。"""

from __future__ import annotations

from collections import OrderedDict

from pyside_iconify._qt import QPixmap

from pyside_iconify._logging import logger


class PixmapCache:
    """按实际像素内存限制的 LRU 缓存。"""

    def __init__(self, limit_mib: int = 32) -> None:
        """创建位图缓存。

        Args:
            limit_mib: 缓存内存上限，单位 MiB；可传正整数，默认 32
        """
        self._items: OrderedDict[str, QPixmap] = OrderedDict()
        self._bytes = 0
        self._limit = limit_mib * 1024 * 1024

    def get(self, key: str) -> QPixmap | None:
        """返回缓存位图并更新使用顺序。

        Args:
            key: 缓存键字符串

        Returns:
            命中时返回缓存的 QPixmap，未命中返回 None。
        """
        pixmap = self._items.get(key)
        if pixmap is None:
            logger.debug("pixmap cache miss: %s", key)
            return None
        logger.debug("pixmap cache hit: %s", key)
        self._items.move_to_end(key)
        return pixmap

    def put(self, key: str, pixmap: QPixmap) -> None:
        """写入位图并按内存上限淘汰最久未用项。

        Args:
            key: 缓存键字符串；已存在时覆盖旧值
            pixmap: 要缓存的位图
        """
        previous = self._items.pop(key, None)
        if previous is not None:
            self._bytes -= _pixmap_bytes(previous)
        self._items[key] = pixmap
        self._bytes += _pixmap_bytes(pixmap)
        while self._items and self._bytes > self._limit:
            _, removed = self._items.popitem(last=False)
            self._bytes -= _pixmap_bytes(removed)

    def clear(self) -> None:
        """清空缓存。"""
        self._items.clear()
        self._bytes = 0

    def set_limit_mib(self, value: int) -> None:
        """调整缓存内存上限，超限时立即淘汰最久未用项。

        Args:
            value: 新的内存上限，单位 MiB
        """
        self._limit = value * 1024 * 1024
        while self._items and self._bytes > self._limit:
            _, removed = self._items.popitem(last=False)
            self._bytes -= _pixmap_bytes(removed)


def _pixmap_bytes(pixmap: QPixmap) -> int:
    """返回位图转为 QImage 后占用的字节数。

    Args:
        pixmap: 要统计的位图

    Returns:
        位图像素数据的字节数。
    """
    return pixmap.toImage().sizeInBytes()


class SvgCache:
    """按条数限制的 SVG 文本 LRU 缓存。"""

    def __init__(self, limit: int = 500) -> None:
        """创建 SVG 文本缓存。

        Args:
            limit: 最大缓存条数；可传正整数，默认 500
        """
        self._items: OrderedDict[str, str] = OrderedDict()
        self._limit = limit

    def get(self, key: str) -> str | None:
        """返回缓存 SVG 并更新使用顺序。

        Args:
            key: 缓存键字符串

        Returns:
            命中时返回 SVG 文本，未命中返回 None。
        """
        svg = self._items.get(key)
        if svg is not None:
            self._items.move_to_end(key)
        return svg

    def put(self, key: str, svg: str) -> None:
        """写入 SVG 并淘汰最久未用项。

        Args:
            key: 缓存键字符串；已存在时覆盖旧值
            svg: 要缓存的 SVG 文本
        """
        self._items[key] = svg
        self._items.move_to_end(key)
        while len(self._items) > self._limit:
            self._items.popitem(last=False)

    def clear(self) -> None:
        """清空缓存。"""
        self._items.clear()


pixmap_cache = PixmapCache()
svg_cache = SvgCache()
