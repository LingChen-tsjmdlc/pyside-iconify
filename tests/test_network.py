"""网络层测试：不真联网，用假下载器驱动。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from pyside_iconify._errors import (
    IconNotFoundError,
    NetworkError,
    OfflineError,
    RequestCancelledError,
)
from pyside_iconify.core.registry import registry
from pyside_iconify.network.client import IconifyClient
from pyside_iconify.network.disk_cache import DiskCache
from pyside_iconify.network.downloader import DownloadResult
from pyside_iconify.widgets import IconWidget

BODY = '<path d="M2 2h12v12H2z"/>'


class FakeDownloader(QObject):
    """记录调用并按队列返回结果的假下载器。"""

    resultReady = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.calls: list[tuple[str, frozenset[str]]] = []
        self.responses: list[DownloadResult | None] = []
        self.closed = False

    def fetch(self, prefix: str, names: object) -> None:
        assert not self.closed
        self.calls.append((prefix, frozenset(names)))  # type: ignore[arg-type]
        if self.responses:
            result = self.responses.pop(0)
            if result is not None:
                self.resultReady.emit(result)

    def close(self) -> None:
        self.closed = True


def make_client(tmp_path: object, **kwargs: object) -> tuple[IconifyClient, FakeDownloader, DiskCache]:
    fake = FakeDownloader()
    cache = DiskCache(directory=str(tmp_path) + "/cache")
    client = IconifyClient(downloader=fake, cache=cache, **kwargs)
    return client, fake, cache


def ok_result(prefix: str, names: object, **kwargs: object) -> DownloadResult:
    return DownloadResult(
        prefix=prefix,
        names=frozenset(names),  # type: ignore[arg-type]
        width=24,
        height=24,
        **kwargs,
    )


def drain() -> None:
    for _ in range(10):
        QApplication.processEvents()


def test_batch_merges_same_prefix(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    client.ensure_loaded("mdi:home")
    client.ensure_loaded("mdi:account")
    drain()
    assert fake.calls == [("mdi", frozenset({"home", "account"}))]


def test_ensure_is_noop_when_registered(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    registry.add_collection(
        {"prefix": "mdi", "icons": {"home": {"body": BODY}}}
    )
    client.ensure_loaded("mdi:home")
    drain()
    assert fake.calls == []


def test_ensure_dedupes_inflight(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    client.ensure_loaded("mdi:home")
    drain()
    # 下载未返回前再次触发，不应重复请求。
    client.ensure_loaded("mdi:home")
    client.ensure_loaded("mdi:home")
    drain()
    assert fake.calls == [("mdi", frozenset({"home"}))]


def test_success_registers_and_clears_pending(
    qtbot: object, tmp_path: object
) -> None:
    client, fake, _ = make_client(tmp_path)
    fake.responses.append(
        ok_result("mdi", ["home"], icons={"home": {"body": BODY}})
    )
    client.ensure_loaded("mdi:home")
    drain()
    assert registry.contains("mdi:home")
    assert not registry.is_pending("mdi:home")
    assert client.get_failure("mdi:home") is None


def test_not_found_records_missing(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    fake.responses.append(ok_result("mdi", ["gone"], not_found=frozenset({"gone"})))
    client.ensure_loaded("mdi:gone")
    drain()
    failure = client.get_failure("mdi:gone")
    assert isinstance(failure, IconNotFoundError)
    assert not registry.is_pending("mdi:gone")


def test_network_error_is_not_missing(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    fake.responses.append(
        ok_result("mdi", ["home"], error=NetworkError("timeout"))
    )
    client.ensure_loaded("mdi:home")
    drain()
    assert isinstance(client.get_failure("mdi:home"), NetworkError)
    assert not isinstance(client.get_failure("mdi:home"), IconNotFoundError)


def test_no_retry_after_failure(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    fake.responses.append(
        ok_result("mdi", ["home"], error=NetworkError("timeout"))
    )
    client.ensure_loaded("mdi:home")
    drain()
    assert len(fake.calls) == 1
    client.reset_failures()
    client.ensure_loaded("mdi:home")
    drain()
    # 失败记录清除后允许重试。
    assert len(fake.calls) == 2


def test_offline_makes_no_requests(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path, offline=True)
    client.ensure_loaded("mdi:home")
    drain()
    assert fake.calls == []
    assert not registry.is_pending("mdi:home")


def test_offline_load_raises(qtbot: object, tmp_path: object) -> None:
    client, _, _ = make_client(tmp_path, offline=True)
    request = client.load(["mdi:home"])
    results = request.wait(timeout_ms=100)
    assert isinstance(results["mdi:home"], OfflineError)


def test_back_online_retries_after_offline_failure(
    qtbot: object, tmp_path: object
) -> None:
    client, fake, _ = make_client(tmp_path, offline=True)
    request = client.load(["mdi:home"])
    assert isinstance(request.wait(timeout_ms=100)["mdi:home"], OfflineError)
    # 切回在线后必须可以重新加载，不能沿用离线失败记忆。
    client.set_offline(False)
    client.load(["mdi:home"])
    drain()
    assert fake.calls == [("mdi", frozenset({"home"}))]


def test_going_offline_fails_pending_loads(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    client.ensure_loaded("mdi:home")
    drain()  # 请求已发出，尚未返回
    client.set_offline(True)
    # 不能永远卡在 loading：转成 OfflineError 失败。
    assert isinstance(client.get_failure("mdi:home"), OfflineError)
    assert not registry.is_pending("mdi:home")
    # 回到在线后可重新加载。
    client.set_offline(False)
    client.ensure_loaded("mdi:home")
    drain()
    assert len(fake.calls) == 2


def test_load_request_reports_results(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    fake.responses.append(
        ok_result("mdi", ["home", "gone"], icons={"home": {"body": BODY}}, not_found=frozenset({"gone"}))
    )
    request = client.load(["mdi:home", "mdi:gone"])
    results = request.wait(timeout_ms=1000)
    assert results["mdi:home"] is None
    assert isinstance(results["mdi:gone"], IconNotFoundError)


def test_load_request_cancel(qtbot: object, tmp_path: object) -> None:
    client, fake, _ = make_client(tmp_path)
    request = client.load(["mdi:home"])
    request.cancel()
    results = request.wait(timeout_ms=100)
    assert isinstance(results["mdi:home"], RequestCancelledError)


def test_disk_cache_hit_skips_network(qtbot: object, tmp_path: object) -> None:
    first, first_fake, cache = make_client(tmp_path)
    first_fake.responses.append(
        ok_result("mdi", ["home"], icons={"home": {"body": BODY}})
    )
    first.ensure_loaded("mdi:home")
    drain()
    registry.clear()

    client = IconifyClient(downloader=FakeDownloader(), cache=cache)
    client.ensure_loaded("mdi:home")
    drain()
    assert registry.contains("mdi:home")


def test_disk_cache_alias_missing_parent_refetched(
    qtbot: object, tmp_path: object
) -> None:
    _, _, cache = make_client(tmp_path)
    cache.store("mdi", {}, {"alias": {"parent": "real"}}, frozenset(), 24, 24)
    fake = FakeDownloader()
    client = IconifyClient(downloader=fake, cache=cache)
    client.ensure_loaded("mdi:alias")
    drain()
    # 别名的父级不在缓存里，必须回源网络。
    assert fake.calls == [("mdi", frozenset({"alias"}))]


def test_widget_triggers_load_and_refreshes(
    qtbot: object, tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, fake, _ = make_client(tmp_path)
    monkeypatch.setattr(
        "pyside_iconify.network.client.default_client", lambda: client
    )
    fake.responses.append(
        ok_result("mdi", ["home"], icons={"home": {"body": BODY}})
    )
    widget = IconWidget("mdi:home")
    statuses: list[str] = []
    widget.statusChanged.connect(statuses.append)
    qtbot.addWidget(widget)
    widget.resize(24, 24)
    widget.show()
    qtbot.waitUntil(lambda: "ready" in statuses, timeout=2000)
    assert fake.calls == [("mdi", frozenset({"home"}))]
    assert registry.contains("mdi:home")
