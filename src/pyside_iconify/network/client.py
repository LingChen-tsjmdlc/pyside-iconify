"""下载客户端：串起内存注册表、磁盘缓存和网络下载。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from threading import RLock

from pyside_iconify._qt import (
    QApplication,
    QEventLoop,
    QObject,
    QTimer,
    Signal,
    run_event_loop,
)

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
    """一批预加载请求的完成通知句柄。

    信号 finished(object)：整批图标都有结果时发射，参数为 ``{图标名: 异常或 None}`` 字典。
    """

    finished = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        """初始化空的请求句柄。

        Args:
            parent: 父 QObject；可传 None。
        """
        super().__init__(parent)
        self._results: dict[str, Exception | None] = {}
        self._remaining: set[str] = set()
        self._loop: QEventLoop | None = None

    def names(self) -> tuple[str, ...]:
        """返回已有结果的图标名。"""
        return tuple(self._results)

    def wait(self, timeout_ms: int | None = None) -> dict[str, Exception | None]:
        """阻塞事件循环等待本批完成，必须在主线程调用。

        Args:
            timeout_ms: 最长等待毫秒数；None 表示一直等到全部完成。

        Returns:
            图标名到结果的映射，成功为 None，失败为对应异常；超时时只含已完成的图标。
        """
        require_main_thread()
        if self._remaining:
            self._loop = QEventLoop(self)
            self.finished.connect(self._loop.quit)
            if timeout_ms is not None:
                QTimer.singleShot(timeout_ms, self._loop.quit)
            run_event_loop(self._loop)
        return dict(self._results)

    def cancel(self) -> None:
        """取消尚未完成的图标，剩余项记为 RequestCancelledError。"""
        from pyside_iconify._errors import RequestCancelledError

        self._resolve(dict.fromkeys(self._remaining, RequestCancelledError("cancelled")))

    def _start(self, results: dict[str, Exception | None], remaining: Iterable[str]) -> None:
        """写入初始结果与待完成集合；没有待完成项时立即发射 finished。

        Args:
            results: 已确定结果的图标名到异常（成功为 None）的映射。
            remaining: 仍在等待加载的图标名。
        """
        self._results = dict(results)
        self._remaining = set(remaining)
        if not self._remaining:
            self.finished.emit(dict(self._results))

    def _resolve(self, updates: dict[str, Exception | None]) -> None:
        """记录一批图标的结果，全部完成后发射 finished。

        Args:
            updates: 图标名到异常（成功为 None）的映射。
        """
        for name, error in updates.items():
            self._results[name] = error
            self._remaining.discard(name)
        if not self._remaining:
            self.finished.emit(dict(self._results))


class IconifyClient(QObject):
    """按需下载图标数据并注册进内存注册表。

    加载顺序为：内存注册表、磁盘缓存、网络下载。

    信号 loaded(str)：参数为图标名；本类当前不会发射该信号。
    信号 failed(str, object)：某个图标加载失败时发射，参数为图标名和异常对象。
    """

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
        """初始化客户端。

        Args:
            parent: 父 QObject；可传 None。
            offline: 是否启动即处于严格离线模式；默认 False。
            downloader: 下载器；None 时新建默认 IconDownloader。
            cache: 磁盘缓存；None 时使用默认目录的 DiskCache。
            target_registry: 接收图标数据的注册表；None 时使用共享注册表。
        """
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
        """切换严格离线模式。

        切到离线时，未完成的加载记为 OfflineError；切回在线时，清除此前由离线造成的失败记录。

        Args:
            value: True 进入离线模式，False 回到在线模式。
        """
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
        """把未完成的加载一律记为 OfflineError，并通知相关请求。"""
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
        """返回已记录的加载失败原因。

        Args:
            name: 图标名；可传 "prefix:name" 字符串或 IconName。

        Returns:
            失败异常；没有失败记录时为 None。
        """
        icon_name = parse_icon_name(name)
        with self._lock:
            return self._failures.get(icon_name)

    def reset_failures(self) -> None:
        """清除失败记录，允许重新加载。"""
        with self._lock:
            self._failures.clear()

    def ensure_loaded(self, name: str | IconName) -> None:
        """数据缺失时轻量触发一次加载，可在绘制路径调用。

        客户端已关闭、处于离线、已有失败记录、数据已在注册表或正在加载时直接返回。

        Args:
            name: 图标名；可传 "prefix:name" 字符串或 IconName。
        """
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
        """显式预加载一批图标。

        已在注册表的图标直接记为成功；已有失败记录的沿用该失败；离线时记为 OfflineError。

        Args:
            icons: 图标名可迭代对象；每项为 "prefix:name" 字符串。
            on_finished: 整批完成时的回调，参数为结果映射；None 表示不回调。

        Returns:
            本批请求的 LoadRequest 句柄。

        Raises:
            ClientClosedError: 客户端已关闭。
        """
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
        """关闭客户端并关闭下载器，未完成的图标记为 ClientClosedError。"""
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
        """按前缀先查磁盘缓存并注册，缓存未覆盖的图标交给下载器。"""
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
        """处理下载结果：写磁盘缓存、注册图标、记录失败、通知请求并重绘。

        Args:
            result: 下载器发出的 DownloadResult。
        """
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
        """把图标数据注册进注册表，未找到的图标记为失败。

        Args:
            prefix: 图标集前缀。
            icons: 图标名到图标数据的映射。
            aliases: 别名到别名数据的映射；父图标不在 icons 中的别名会被忽略。
            not_found: 确认不存在的图标名集合。
            width: 图标集默认宽度；None 表示未提供。
            height: 图标集默认高度；None 表示未提供。
            set_missing: True 表示整个图标集不存在，失败信息改为图标集不存在。

        Returns:
            已处理的图标名集合，包含注册成功和已记为失败的。
        """
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
        """收集一批图标当前的结果。

        Args:
            prefix: 图标集前缀。
            names: 图标名集合（不含前缀）。

        Returns:
            完整图标名到结果的映射，失败为异常、已注册为 None；两者都不是的图标不包含在内。
        """
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
        """记录失败原因、清除待加载标记，并发射 failed 信号。

        Args:
            icon_name: 失败的图标名。
            error: 失败原因。
        """
        self._registry.clear_pending(icon_name)
        with self._lock:
            self._failures[icon_name] = error
            self._pending_names.discard(icon_name)
        logger.debug("icon load failed: %s (%s)", icon_name, error)
        self.failed.emit(str(icon_name), error)

    def _update_requests(self, updates: dict[str, Exception | None]) -> None:
        """把结果分发给相关的 LoadRequest，已完成的请求从列表移除。

        Args:
            updates: 完整图标名到异常（成功为 None）的映射。
        """
        if not self._requests:
            return
        for request in self._requests[:]:
            resolved = {name: error for name, error in updates.items() if name in request._results or name in request._remaining}
            if resolved:
                request._resolve(resolved)
            if not request._remaining:
                self._requests.remove(request)

    def _repaint_all(self) -> None:
        """刷新所有控件，使新到达的图标得以绘制。"""
        application = QApplication.instance()
        if application is None:
            return
        for widget in QApplication.allWidgets():
            widget.update()


def _alias_resolvable(alias: dict[str, object], icons: dict[str, dict[str, object]]) -> bool:
    """判断别名的父图标是否存在于给定图标中。

    Args:
        alias: 别名数据；其 "parent" 字段应为父图标名。
        icons: 图标名到图标数据的映射。

    Returns:
        父图标名是字符串且在 icons 中时为 True。
    """
    parent = alias.get("parent")
    return isinstance(parent, str) and parent in icons


_default_client: IconifyClient | None = None


def default_client() -> IconifyClient:
    """返回进程级共享客户端，首次调用时创建。

    Returns:
        共享的 IconifyClient。
    """
    global _default_client
    if _default_client is None:
        _default_client = IconifyClient()
    return _default_client


def set_offline(value: bool) -> None:
    """切换默认客户端的离线模式。

    Args:
        value: True 进入离线模式，False 回到在线模式。
    """
    default_client().set_offline(value)


def is_offline() -> bool:
    """返回默认客户端是否处于离线模式。"""
    return default_client().is_offline()


def load_icons(
    icons: Iterable[str],
    *,
    on_finished: Callable[[dict[str, Exception | None]], None] | None = None,
) -> LoadRequest:
    """用默认客户端预加载一批图标。

    Args:
        icons: 图标名可迭代对象；每项为 "prefix:name" 字符串。
        on_finished: 整批完成时的回调，参数为结果映射；None 表示不回调。

    Returns:
        本批请求的 LoadRequest 句柄。
    """
    return default_client().load(icons, on_finished=on_finished)
