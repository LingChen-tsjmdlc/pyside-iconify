"""共享旋转动画时钟"""

from __future__ import annotations

import weakref
from time import monotonic

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QWidget


class SpinClock(QObject):
    """用一个定时器驱动所有可见旋转图标。"""

    def __init__(self) -> None:
        super().__init__()
        self._widgets: weakref.WeakSet[QWidget] = weakref.WeakSet()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._started_at = monotonic()

    def add(self, widget: QWidget) -> None:
        """注册需要旋转的控件。"""
        self._widgets.add(widget)
        reference = weakref.ref(widget)
        widget.destroyed.connect(lambda *_: self._remove_destroyed(reference))
        self._sync()

    def remove(self, widget: QWidget) -> None:
        """移除不再旋转的控件。"""
        self._discard(widget)
        self._sync()

    def _remove_destroyed(self, reference: weakref.ReferenceType[QWidget]) -> None:
        widget = reference()
        if widget is not None:
            self._discard(widget)
        self._sync()

    def _discard(self, widget: QWidget) -> None:
        try:
            self._widgets.discard(widget)
        except RuntimeError:
            return

    def angle(self, period: float) -> float:
        """返回当前动画角度。"""
        if period <= 0:
            return 0.0
        return ((monotonic() - self._started_at) / period * 360.0) % 360.0

    def _tick(self) -> None:
        visible = False
        for widget in tuple(self._widgets):
            if self._is_active(widget):
                visible = True
                widget.update()
        if not visible:
            self._timer.stop()

    def _sync(self) -> None:
        if any(self._is_active(widget) for widget in tuple(self._widgets)):
            if not self._timer.isActive():
                self._timer.start()

    def _is_active(self, widget: QWidget) -> bool:
        try:
            return widget.isVisible() and not widget.window().isMinimized()
        except RuntimeError:
            self._discard(widget)
            return False

    def sync(self) -> None:
        """在可见性变化后同步定时器。"""
        self._sync()


spin_clock: SpinClock | None = None


def get_spin_clock() -> SpinClock:
    """延迟创建共享动画时钟。"""
    global spin_clock
    if spin_clock is None:
        spin_clock = SpinClock()
    return spin_clock
