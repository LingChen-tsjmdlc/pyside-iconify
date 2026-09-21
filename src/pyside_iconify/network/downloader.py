"""基于 QtNetwork 的图标下载器。"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from pyside_iconify._errors import (
    ClientClosedError,
    InvalidResponseError,
    NetworkError,
    RateLimitError,
    RequestCancelledError,
    ResponseTooLargeError,
    ServerError,
)
from pyside_iconify._logging import logger
from pyside_iconify.rendering.qt_adapter import require_main_thread

DEFAULT_API_ROOT = "https://api.iconify.design"
DEFAULT_BATCH_DELAY_MS = 50
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """一次批量下载的结果。"""

    prefix: str
    names: frozenset[str]
    icons: dict[str, dict[str, object]] = field(default_factory=dict)
    aliases: dict[str, dict[str, object]] = field(default_factory=dict)
    not_found: frozenset[str] = frozenset()
    error: Exception | None = None
    width: float | None = None
    height: float | None = None
    set_missing: bool = False


def _error_from_reply(reply: QNetworkReply) -> Exception:
    """把 Qt 网络错误映射为库错误。"""
    status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
    if status is not None:
        code = int(status)
        if code == 404:
            return InvalidResponseError(f"icon set not found: {reply.url().toString()}")
        if code == 429:
            return RateLimitError("rate limited by icon server")
        if code >= 500:
            return ServerError(f"server error: HTTP {code}")
    error = reply.error()
    if error == QNetworkReply.NetworkError.OperationCanceledError:
        return RequestCancelledError("request cancelled")
    return NetworkError(reply.errorString() or "network request failed")


class IconDownloader(QObject):
    """按前缀凑批下载图标 JSON，同一时刻每个图标只请求一次。"""

    resultReady = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        api_root: str = DEFAULT_API_ROOT,
        batch_delay_ms: int = DEFAULT_BATCH_DELAY_MS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._api_root = api_root.rstrip("/")
        self._batch_delay_ms = max(0, batch_delay_ms)
        self._max_response_bytes = max_response_bytes
        self._queued: dict[str, set[str]] = {}
        self._inflight: dict[str, set[str]] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._batch_delay_ms)
        self._timer.timeout.connect(self._flush)
        self._replies: dict[QNetworkReply, tuple[str, frozenset[str]]] = {}
        self._retired: deque[QNetworkReply] = deque(maxlen=128)
        self._closed = False

    def fetch(self, prefix: str, names: Iterable[str]) -> None:
        """请求一批图标，进入凑批队列。"""
        require_main_thread()
        if self._closed:
            raise ClientClosedError("downloader is closed")
        requested = {name for name in names if name}
        if not requested:
            return
        pending = requested - self._inflight.get(prefix, set())
        if not pending:
            return
        batch = self._queued.setdefault(prefix, set())
        new_names = pending - batch
        if not new_names:
            return
        batch.update(new_names)
        if not self._timer.isActive():
            self._timer.start()

    def close(self) -> None:
        """取消所有进行中的请求并停止接收新请求。"""
        require_main_thread()
        if self._closed:
            return
        self._closed = True
        self._timer.stop()
        for reply, (prefix, names) in list(self._replies.items()):
            del self._replies[reply]
            self._inflight.get(prefix, set()).difference_update(names)
            if not self._inflight.get(prefix):
                self._inflight.pop(prefix, None)
            reply.abort()
            self._retire(reply)
            self.resultReady.emit(
                DownloadResult(
                    prefix=prefix,
                    names=names,
                    error=RequestCancelledError("downloader closed"),
                )
            )
        self._queued.clear()

    def _retire(self, reply: QNetworkReply) -> None:
        """回收已完成的 reply，销毁动作同步完成，不留悬空的 DeferredDelete。

        若只 deleteLater，事件未被处理时本对象可能连带销毁 reply 的 C++
        对象，之后事件循环处理这条失效事件会直接崩溃。
        """
        try:
            reply.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        reply.close()
        self._retired.append(reply)
        if len(self._retired) == self._retired.maxlen:
            self._destroy(self._retired.popleft())

    @staticmethod
    def _destroy(reply: QNetworkReply) -> None:
        reply.deleteLater()
        QCoreApplication.sendPostedEvents(reply, QEvent.Type.DeferredDelete)

    def _flush(self) -> None:
        for prefix, names in self._queued.items():
            frozen = frozenset(names)
            self._inflight.setdefault(prefix, set()).update(frozen)
            url = QUrl(f"{self._api_root}/{prefix}.json")
            query = url.query()
            joined = ",".join(sorted(frozen))
            url.setQuery(f"icons={joined}" if not query else f"{query}&icons={joined}")
            request = QNetworkRequest(url)
            request.setAttribute(
                QNetworkRequest.Attribute.RedirectPolicyAttribute,
                QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
            )
            reply = self._manager.get(request)
            self._replies[reply] = (prefix, frozen)
            reply.finished.connect(lambda reply=reply: self._on_finished(reply))
        self._queued.clear()

    def _on_finished(self, reply: QNetworkReply) -> None:
        entry = self._replies.pop(reply, None)
        if entry is None:
            self._retire(reply)
            return
        prefix, names = entry
        inflight = self._inflight.get(prefix)
        if inflight is not None:
            inflight.difference_update(names)
            if not inflight:
                self._inflight.pop(prefix, None)
        try:
            result = self._parse_reply(reply, prefix, names)
        finally:
            self._retire(reply)
        self.resultReady.emit(result)

    def _parse_reply(
        self, reply: QNetworkReply, prefix: str, names: frozenset[str]
    ) -> DownloadResult:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if status is not None and int(status) == 404:
                # 集合不存在：所有请求的图标都确认不存在。
                return DownloadResult(
                    prefix=prefix,
                    names=names,
                    not_found=names,
                    set_missing=True,
                )
            return DownloadResult(
                prefix=prefix, names=names, error=_error_from_reply(reply)
            )
        payload = bytes(reply.readAll())
        if len(payload) > self._max_response_bytes:
            return DownloadResult(
                prefix=prefix,
                names=names,
                error=ResponseTooLargeError(
                    f"response exceeds {self._max_response_bytes} bytes"
                ),
            )
        try:
            document = json.loads(payload)
        except (ValueError, UnicodeDecodeError) as error:
            return DownloadResult(
                prefix=prefix, names=names, error=InvalidResponseError(str(error))
            )
        if not isinstance(document, dict):
            # API 对不存在的集合返回 HTTP 200 + 正文 "404"。
            if document == 404 or payload.strip() == b"404":
                return DownloadResult(
                    prefix=prefix,
                    names=names,
                    not_found=names,
                    set_missing=True,
                )
            return DownloadResult(
                prefix=prefix,
                names=names,
                error=InvalidResponseError("response must be a JSON object"),
            )
        response_prefix = document.get("prefix", prefix)
        if response_prefix != prefix:
            return DownloadResult(
                prefix=prefix,
                names=names,
                error=InvalidResponseError(
                    f"response prefix mismatch: {response_prefix!r}"
                ),
            )
        icons_raw = document.get("icons") or {}
        aliases_raw = document.get("aliases") or {}
        not_found_raw = document.get("not_found") or []
        if not isinstance(icons_raw, dict) or not isinstance(aliases_raw, dict):
            return DownloadResult(
                prefix=prefix,
                names=names,
                error=InvalidResponseError("icons must be an object"),
            )
        if not isinstance(not_found_raw, list):
            return DownloadResult(
                prefix=prefix,
                names=names,
                error=InvalidResponseError("not_found must be an array"),
            )
        icons = {
            name: value
            for name, value in icons_raw.items()
            if isinstance(name, str) and isinstance(value, dict)
        }
        aliases = {
            name: value
            for name, value in aliases_raw.items()
            if isinstance(name, str) and isinstance(value, dict)
        }
        not_found = frozenset(name for name in not_found_raw if isinstance(name, str))
        logger.debug("downloaded %s icons from %s", len(icons) + len(aliases), prefix)
        return DownloadResult(
            prefix=prefix,
            names=names,
            icons=icons,
            aliases=aliases,
            not_found=not_found,
            width=_optional_number(document.get("width")),
            height=_optional_number(document.get("height")),
        )


def _optional_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
