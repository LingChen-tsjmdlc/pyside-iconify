"""下载客户端：串起内存注册表、磁盘缓存和网络下载。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from threading import RLock

from PySide6.QtCore import QEventLoop, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from pyside_iconify._errors import (
    ClientClosedError,
    IconNotFoundError,
    OfflineError,
)
from pyside_iconify._logging import logger
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.registry import IconRegistry, registry as shared_registry
from pyside_iconify.core.types import IconName
from pyside_iconify.network.disk_cache import DiskCache
from pyside_iconify.network.downloader import IconDownloader
from pyside_iconify.rendering.qt_adapter import require_main_thread


class LoadRequest(QObject):
    """一批预加载请求的完成通知句柄。"""

    finished = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._results: dict[str, Exception | None] = {}
        self._remaining: set[str] = set()
        self._loop: QEventLoop | None = None

    def names(self) -> tuple[str, ...]:
        """返回本批图标名。"""
        return tuple(self._results)

    def wait(self, timeout_ms: int | None = None) -> dict[str, Exception | None]:
        """阻塞事件循环等待完成，返回每个图标的结果。"""
        require_main_thread()
        if self._remaining:
            self._loop = QEventLoop(self)
            self.finished.connect(self._loop.quit)
            if timeout_ms is not None:
                QTimer.singleShot(timeout_ms, self._loop.quit)
            self._loop.exec()
        return dict(self._results)

    def cancel(self) -> None:
        """取消尚未完成的图标，剩余项记为 RequestCancelledError。"""
        from pyside_iconify._errors import RequestCancelledError

        self._resolve(dict.fromkeys(self._remaining, RequestCancelledError("cancelled")))

    def _start(self, results: dict[str, Exception | None], remaining: Iterable[str]) -> None:
        self._results = dict(results)
        self._remaining = set(remaining)
        if not self._remaining:
            self.finished.emit(dict(self._results))

    def _resolve(self, updates: dict[str, Exception | None]) -> None:
        for name, error in updates.items():
            self._results[name] = error
            self._remaining.discard(name)
        if not self._remaining:
            self.finished.emit(dict(self._results))


class IconifyClient(QObject):
    """按需下载图标数据并注册进内存注册表。"""

    loaded = Signal(str)
    failed = Signal(str, object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        offline: bool = False,
        downloader: IconDownloader | None = None,
        cache: DiskCache | None = None,
        target_registry: IconRegistry | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = target_registry if target_registry is not None else shared_registry
        self._downloader = downloader if downloader is not None else IconDownloader(self)
        self._downloader.resultReady.connect(self._on_result)
        self._cache = cache if cache is not None else DiskCache()
        self._offline = offline
        self._closed = False
        self._lock = RLock()
        self._failures: dict[IconName, Exception] = {}
        self._scheduled: dict[str, set[str]] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._flush_scheduled)
        self._requests: list[LoadRequest] = []
        self._pending_names: set[IconName] = set()

    def set_offline(self, value: bool) -> None:
        """切换严格离线模式。"""
        self._offline = bool(value)
        if value:
            self._fail_pending_icons()
        else:
            # 回到在线时，离线造成的失败记录全部作废，允许重新加载。
            with self._lock:
                for name in [
                    name
                    for name, error in self._failures.items()
                    if isinstance(error, OfflineError)
                ]:
                    del self._failures[name]

    def _fail_pending_icons(self) -> None:
        """切离线时，未完成的加载一律记为 OfflineError，不让控件永远转圈。"""
        with self._lock:
            pending = [
                name for name in self._pending_names
                if not self._registry.contains(name)
                and name not in self._failures
            ]
            self._pending_names.clear()
        updates: dict[str, Exception | None] = {}
        for icon_name in pending:
            error = OfflineError(f"offline and no local data: {icon_name}")
            self._record_failure(icon_name, error)
            updates[str(icon_name)] = error
        if updates:
            self._update_requests(updates)

    def is_offline(self) -> bool:
        """是否处于严格离线模式。"""
        return self._offline

    def get_failure(self, name: str | IconName) -> Exception | None:
        """返回已记录的加载失败原因。"""
        icon_name = parse_icon_name(name)
        with self._lock:
            return self._failures.get(icon_name)

    def reset_failures(self) -> None:
        """清除失败记录，允许重新加载。"""
        with self._lock:
            self._failures.clear()

    def ensure_loaded(self, name: str | IconName) -> None:
        """数据缺失时轻量触发一次加载，可在绘制路径调用。"""
        require_main_thread()
        icon_name = parse_icon_name(name)
        if self._closed or self._offline:
            return
        with self._lock:
            if (
                icon_name in self._failures
                or self._registry.contains(icon_name)
                or self._registry.is_pending(icon_name)
            ):
                return
            self._registry.mark_pending(icon_name)
            self._pending_names.add(icon_name)
            self._scheduled.setdefault(icon_name.prefix, set()).add(icon_name.name)
        if not self._timer.isActive():
            self._timer.start()

    def load(
        self, icons: Iterable[str], *, on_finished: Callable[[dict[str, Exception | None]], None] | None = None
    ) -> LoadRequest:
        """显式预加载一批图标，返回 LoadRequest。"""
        require_main_thread()
        if self._closed:
            raise ClientClosedError("client is closed")
        results: dict[str, Exception | None] = {}
        remaining: set[str] = set()
        for icon in icons:
            icon_name = parse_icon_name(icon)
            name = str(icon_name)
            if self._registry.contains(icon_name):
                results[name] = None
                continue
            failure = self.get_failure(icon_name)
            if failure is not None:
                results[name] = failure
                continue
            if self._offline:
                self._record_failure(icon_name, OfflineError(f"offline and no local data: {name}"))
                results[name] = OfflineError(f"offline and no local data: {name}")
                continue
            remaining.add(name)
            self.ensure_loaded(icon_name)
        request = LoadRequest(self)
        if on_finished is not None:
            request.finished.connect(on_finished)
        request._start(results, remaining)
        if remaining:
            self._requests.append(request)
        return request

    def close(self) -> None:
        """取消所有请求并关闭客户端。"""
        require_main_thread()
        self._closed = True
        self._timer.stop()
        self._downloader.close()
        with self._lock:
            pending = list(self._pending_names)
            self._pending_names.clear()
        for icon_name in pending:
            self._record_failure(
                icon_name, ClientClosedError(f"client closed: {icon_name}")
            )

    # -- 内部 --

    def _flush_scheduled(self) -> None:
        scheduled, self._scheduled = self._scheduled, {}
        if self._offline:
            return
        for prefix, names in scheduled.items():
            icons, aliases, not_found, dims = self._cache.lookup(
                prefix, frozenset(names)
            )
            handled = self._register(
                prefix, icons, aliases, not_found, dims[0], dims[1]
            )
            rest = names - handled
            if rest:
                self._downloader.fetch(prefix, rest)

    def _on_result(self, result: object) -> None:
        from pyside_iconify.network.downloader import DownloadResult

        assert isinstance(result, DownloadResult)
        prefix = result.prefix
        if result.error is not None:
            for name in sorted(result.names):
                self._record_failure(IconName(prefix, name), result.error)
        else:
            if result.icons or result.aliases or result.not_found:
                try:
                    self._cache.store(
                        prefix,
                        result.icons,
                        result.aliases,
                        result.not_found,
                        result.width,
                        result.height,
                    )
                except OSError as error:
                    logger.warning("cannot write disk cache: %s", error)
            self._register(
                prefix,
                result.icons,
                result.aliases,
                result.not_found,
                result.width,
                result.height,
                result.set_missing,
            )
            missing = (
                result.names
                - set(result.icons)
                - set(result.aliases)
                - set(result.not_found)
            )
            for name in sorted(missing):
                self._record_failure(
                    IconName(prefix, name),
                    IconNotFoundError(f"icon not found: {prefix}:{name}"),
                )
        updates = self._collect_updates(prefix, result.names)
        self._update_requests(updates)
        self._repaint_all()

    def _register(
        self,
        prefix: str,
        icons: dict[str, dict[str, object]],
        aliases: dict[str, dict[str, object]],
        not_found: frozenset[str],
        width: float | None = None,
        height: float | None = None,
        set_missing: bool = False,
    ) -> set[str]:
        """把图标数据注册进注册表，返回成功处理的图标名。"""
        handled: set[str] = set()
        if icons or aliases:
            safe_aliases = {
                name: value
                for name, value in aliases.items()
                if _alias_resolvable(value, icons)
            }
            collection: dict[str, object] = {
                "prefix": prefix,
                "icons": icons,
                "aliases": safe_aliases,
            }
            if width is not None:
                collection["width"] = width
            if height is not None:
                collection["height"] = height
            try:
                self._registry.add_collection(collection, replace=True)
                handled.update(icons)
                handled.update(safe_aliases)
            except Exception as error:  # 数据不合法：逐个记为失败
                logger.error("cannot register downloaded icons for %s: %s", prefix, error)
                for name in list(icons) + list(safe_aliases):
                    self._record_failure(IconName(prefix, name), error)
                    handled.add(name)
        for name in not_found:
            if set_missing:
                detail = f"icon set not found: {prefix}"
            else:
                detail = f"icon not found: {prefix}:{name}"
            self._record_failure(IconName(prefix, name), IconNotFoundError(detail))
            handled.add(name)
        with self._lock:
            for name in handled:
                self._pending_names.discard(IconName(prefix, name))
        return handled

    def _collect_updates(self, prefix: str, names: frozenset[str]) -> dict[str, Exception | None]:
        updates: dict[str, Exception | None] = {}
        for name in names:
            icon_name = IconName(prefix, name)
            failure = self.get_failure(icon_name)
            if failure is not None:
                updates[str(icon_name)] = failure
            elif self._registry.contains(icon_name):
                updates[str(icon_name)] = None
        return updates

    def _record_failure(self, icon_name: IconName, error: Exception) -> None:
        self._registry.clear_pending(icon_name)
        with self._lock:
            self._failures[icon_name] = error
            self._pending_names.discard(icon_name)
        logger.debug("icon load failed: %s (%s)", icon_name, error)
        self.failed.emit(str(icon_name), error)

    def _update_requests(self, updates: dict[str, Exception | None]) -> None:
        if not self._requests:
            return
        for request in self._requests[:]:
            resolved = {name: error for name, error in updates.items() if name in request._results or name in request._remaining}
            if resolved:
                request._resolve(resolved)
            if not request._remaining:
                self._requests.remove(request)

    def _repaint_all(self) -> None:
        application = QApplication.instance()
        if application is None:
            return
        for widget in QApplication.allWidgets():
            widget.update()


def _alias_resolvable(alias: dict[str, object], icons: dict[str, dict[str, object]]) -> bool:
    parent = alias.get("parent")
    return isinstance(parent, str) and parent in icons


_default_client: IconifyClient | None = None


def default_client() -> IconifyClient:
    """返回进程级共享客户端。"""
    global _default_client
    if _default_client is None:
        _default_client = IconifyClient()
    return _default_client


def set_offline(value: bool) -> None:
    """切换默认客户端的离线模式。"""
    default_client().set_offline(value)


def is_offline() -> bool:
    """返回默认客户端是否处于离线模式。"""
    return default_client().is_offline()


def load_icons(
    icons: Iterable[str],
    *,
    on_finished: Callable[[dict[str, Exception | None]], None] | None = None,
) -> LoadRequest:
    """用默认客户端预加载一批图标。"""
    return default_client().load(icons, on_finished=on_finished)
