"""pytest 和 Qt 测试的共用配置。"""

from __future__ import annotations

import gc
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QApplication

from pyside_iconify import set_default_config
from pyside_iconify.core.registry import registry
from pyside_iconify.network import client as network_client
from pyside_iconify.rendering.cache import pixmap_cache, svg_cache
from pyside_iconify.widgets import animation


def _reset_default_client() -> None:
    """默认客户端回到离线、无失败记录的状态，避免测试真联网。"""
    client = network_client.default_client()
    client.set_offline(True)
    client.reset_failures()


def _drain_events(iterations: int = 10) -> None:
    """处理普通事件与延迟删除事件，清空 Qt 队列。"""
    app = QApplication.instance()
    if app is None:
        return
    for _ in range(iterations):
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()


def _stop_active_qt_objects() -> None:
    """停止控件树内残留的定时器和属性动画。"""
    app = QApplication.instance()
    if app is not None:
        for widget in list(app.topLevelWidgets()):
            try:
                for timer in widget.findChildren(QTimer):
                    timer.stop()
                for transition in widget.findChildren(QPropertyAnimation):
                    transition.stop()
            except RuntimeError:
                continue
    if animation.spin_clock is not None:
        animation.spin_clock._timer.stop()


@pytest.fixture(autouse=True)
def reset_library_state(qtbot: object) -> None:
    """每条测试前后恢复库状态并清理 Qt 生命周期残留。"""
    _drain_events()
    _reset_default_client()
    registry.clear()
    pixmap_cache.clear()
    svg_cache.clear()
    set_default_config(
        size=None,
        color=None,
        light_color=None,
        dark_color=None,
        opacity=None,
        fallback=None,
        disabled_opacity=None,
        spin_period=None,
    )
    yield
    _stop_active_qt_objects()
    _drain_events()
    _reset_default_client()
    registry.clear()
    pixmap_cache.clear()
    svg_cache.clear()
    gc.collect()
    _drain_events()
