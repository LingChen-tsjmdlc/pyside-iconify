"""联网下载和缓存（Step 2）。"""

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
