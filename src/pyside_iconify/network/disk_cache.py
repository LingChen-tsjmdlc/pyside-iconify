"""图标 JSON 的磁盘缓存。"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from threading import RLock
from time import time

from PySide6.QtCore import QStandardPaths

from pyside_iconify._logging import logger

DEFAULT_TTL_SECONDS = 7 * 24 * 3600
DEFAULT_MAX_ENTRIES = 4096
_CACHE_VERSION = 1


class DiskCache:
    """按前缀合并存放图标数据，读失败静默降级为未命中。"""

    def __init__(
        self,
        *,
        directory: str | Path | None = None,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._directory = Path(directory) if directory is not None else None
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._lock = RLock()

    def directory(self) -> Path | None:
        """返回缓存目录，不可用时为 None。"""
        if self._directory is not None:
            return self._directory
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.CacheLocation
        )
        if not base:
            return None
        self._directory = Path(base) / "pyside-iconify"
        return self._directory

    def lookup(
        self, prefix: str, names: frozenset[str]
    ) -> tuple[
        dict[str, dict[str, object]],
        dict[str, dict[str, object]],
        frozenset[str],
        tuple[float | None, float | None],
    ]:
        """返回 (icons, aliases, not_found, (width, height)) 中未过期的部分。"""
        icons: dict[str, dict[str, object]] = {}
        aliases: dict[str, dict[str, object]] = {}
        not_found: set[str] = set()
        with self._lock:
            document = self._read(prefix)
            if document is None:
                return {}, {}, frozenset(), (None, None)
            dims = (
                _optional_number(document.get("width")),
                _optional_number(document.get("height")),
            )
            now = time()
            for name in names:
                entry = document["icons"].get(name)
                if entry is not None and now - entry["saved"] <= self._ttl_seconds:
                    if entry["kind"] == "not_found":
                        not_found.add(name)
                    else:
                        icons[name] = entry["data"]
                entry = document["aliases"].get(name)
                if entry is not None and now - entry["saved"] <= self._ttl_seconds:
                    if name not in icons and name not in not_found:
                        aliases[name] = entry["data"]
        return icons, aliases, frozenset(not_found), dims

    def store(
        self,
        prefix: str,
        icons: Mapping[str, Mapping[str, object]],
        aliases: Mapping[str, Mapping[str, object]],
        not_found: frozenset[str],
        width: float | None,
        height: float | None,
    ) -> None:
        """把下载结果合并进前缀对应的缓存文件。"""
        now = time()
        with self._lock:
            document = self._read(prefix)
            if document is None:
                document = {
                    "version": _CACHE_VERSION,
                    "width": width,
                    "height": height,
                    "icons": {},
                    "aliases": {},
                }
            else:
                if width is not None:
                    document["width"] = width
                if height is not None:
                    document["height"] = height
                for section in ("icons", "aliases"):
                    stale = [
                        name
                        for name, entry in document[section].items()
                        if now - entry["saved"] > self._ttl_seconds
                    ]
                    for name in stale:
                        del document[section][name]
            for name, value in icons.items():
                document["icons"][name] = {
                    "saved": now,
                    "kind": "icon",
                    "data": dict(value),
                }
            for name, value in aliases.items():
                document["aliases"][name] = {
                    "saved": now,
                    "kind": "alias",
                    "data": dict(value),
                }
            for name in not_found:
                document["icons"][name] = {
                    "saved": now,
                    "kind": "not_found",
                    "data": {},
                }
            self._prune(document)
            self._write(prefix, document)

    def clear(self) -> None:
        """删除全部缓存文件。"""
        with self._lock:
            directory = self.directory()
            if directory is None:
                return
            try:
                for path in directory.glob("*.json"):
                    path.unlink(missing_ok=True)
            except OSError as error:
                logger.warning("cannot clear disk cache: %s", error)

    def _read(self, prefix: str) -> dict[str, object] | None:
        path = self._path(prefix)
        if path is None:
            return None
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            if path.exists():
                logger.warning("corrupt cache entry dropped: %s", path)
                try:
                    path.unlink()
                except OSError:
                    pass
            return None
        if not isinstance(document, dict) or document.get("version") != _CACHE_VERSION:
            return None
        if not isinstance(document.get("icons"), dict) or not isinstance(
            document.get("aliases"), dict
        ):
            return None
        return document

    def _write(self, prefix: str, document: dict[str, object]) -> None:
        path = self._path(prefix, create=True)
        if path is None:
            return
        try:
            fd, temp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(document, handle, ensure_ascii=False)
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        except OSError as error:
            logger.warning("cannot write disk cache: %s", error)

    def _prune(self, document: dict[str, object]) -> None:
        entries: list[tuple[float, str, str]] = []
        for section in ("icons", "aliases"):
            for name, entry in document[section].items():
                entries.append((entry["saved"], section, name))
        overflow = len(entries) - self._max_entries
        if overflow <= 0:
            return
        entries.sort()
        for _, section, name in entries[:overflow]:
            del document[section][name]

    def _path(self, prefix: str, *, create: bool = False) -> Path | None:
        directory = self.directory()
        if directory is None:
            return None
        if create:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                logger.warning("cannot create cache directory: %s", error)
                return None
        return directory / f"{prefix}.json"


def _optional_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
