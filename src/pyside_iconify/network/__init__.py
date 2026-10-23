"""联网下载与磁盘缓存：导出下载客户端、下载器、磁盘缓存及模块级便捷函数。"""

from __future__ import annotations

from pyside_iconify.network.client import (
    IconifyClient,
    LoadRequest,
    default_client,
    is_offline,
    load_icons,
    set_offline,
)
from pyside_iconify.network.disk_cache import DiskCache
from pyside_iconify.network.downloader import (
    DEFAULT_API_ROOT,
    DEFAULT_BATCH_DELAY_MS,
    DownloadResult,
    IconDownloader,
)

__all__ = [
    "DEFAULT_API_ROOT",
    "DEFAULT_BATCH_DELAY_MS",
    "DiskCache",
    "DownloadResult",
    "IconDownloader",
    "IconifyClient",
    "LoadRequest",
    "default_client",
    "is_offline",
    "load_icons",
    "set_offline",
]
