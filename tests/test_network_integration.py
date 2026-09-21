"""网络层真实联网测试：直接请求 api.iconify.design。

设 PYSIDE_ICONIFY_NO_NETWORK=1 可跳过（无网环境 / CI 离线跑）。
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    bool(os.environ.get("PYSIDE_ICONIFY_NO_NETWORK")),
    reason="PYSIDE_ICONIFY_NO_NETWORK is set",
)

from PySide6.QtCore import QObject, Signal

from pyside_iconify import get_pixmap, get_icon_data
from pyside_iconify._errors import IconNotFoundError
from pyside_iconify.core.registry import registry
from pyside_iconify.network.client import IconifyClient, default_client
from pyside_iconify.network.disk_cache import DiskCache
from pyside_iconify.network.downloader import DownloadResult, IconDownloader


def wait_until(predicate: object, timeout_s: float = 15.0) -> bool:
    """处理事件循环直到条件成立或超时。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    deadline = timeout_s
    import time

    while deadline > 0:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
        deadline -= 0.02
    return predicate()


def test_real_downloader_fetches_mdi_home(qtbot: object) -> None:
    downloader = IconDownloader()
    results: list[DownloadResult] = []
    downloader.resultReady.connect(results.append)
    downloader.fetch("mdi", ["home"])
    assert wait_until(lambda: bool(results)), "real download did not finish"
    result = results[0]
    assert result.error is None
    assert "home" in result.icons
    assert result.width == 24 and result.height == 24


def test_real_download_registers_at_full_viewbox(qtbot: object, tmp_path: object) -> None:
    """集合级 width/height 必须生效，否则 24 格的 mdi 会被裁成 16 格。"""
    client = IconifyClient(cache=DiskCache(directory=str(tmp_path) + "/cache"))
    client.ensure_loaded("mdi:weather-night")
    assert wait_until(lambda: registry.contains("mdi:weather-night"))
    data = get_icon_data("mdi:weather-night")
    assert (data.width, data.height) == (24.0, 24.0)
    # 墨迹不得顶到画布边缘（weather-night 的图形在 24 格里自带留白）。
    pixmap = get_pixmap("mdi:weather-night", size=40)
    image = pixmap.toImage()
    width, height = image.width(), image.height()
    edge_pixels = [
        (x, y)
        for y in range(height)
        for x in (0, width - 1)
        if image.pixelColor(x, y).alpha() > 0
    ] + [
        (x, y)
        for x in range(width)
        for y in (0, height - 1)
        if image.pixelColor(x, y).alpha() > 0
    ]
    assert edge_pixels == [], "icon ink touches the canvas edge: viewbox clipped"


def test_real_widget_shows_downloaded_icon(qtbot: object) -> None:
    from pyside_iconify import IconWidget

    default_client().set_offline(False)
    default_client().reset_failures()
    widget = IconWidget("mdi:cog", size=40)
    qtbot.addWidget(widget)
    widget.resize(40, 40)
    widget.show()
    assert wait_until(lambda: registry.contains("mdi:cog"))
    pixmap = get_pixmap("mdi:cog", size=40)
    assert not pixmap.isNull()


def test_real_missing_icon_is_not_network_error(qtbot: object) -> None:
    from pyside_iconify.network.client import default_client

    client = default_client()
    client.set_offline(False)
    client.reset_failures()
    client.ensure_loaded("mdi:this-icon-definitely-does-not-exist-xyz")
    assert wait_until(lambda: client.get_failure("mdi:this-icon-definitely-does-not-exist-xyz") is not None)
    failure = client.get_failure("mdi:this-icon-definitely-does-not-exist-xyz")
    assert isinstance(failure, IconNotFoundError)


def test_real_batch_merges_into_one_response(qtbot: object) -> None:
    downloader = IconDownloader()
    results: list[DownloadResult] = []
    downloader.resultReady.connect(results.append)
    downloader.fetch("mdi", ["heart"])
    downloader.fetch("mdi", ["star"])
    assert wait_until(lambda: bool(results))
    assert len(results) == 1
    merged = results[0]
    assert {"heart", "star"} <= set(merged.icons)
