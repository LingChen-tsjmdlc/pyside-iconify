"""共享旋转动画时钟。"""

from __future__ import annotations

import weakref
from time import monotonic

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QWidget


class SpinClock(QObject):
    """用一个定时器驱动所有可见旋转图标。

    控件以弱引用保存；定时器仅在存在可见控件时运行。
    """

    def __init__(self) -> None:
        """创建时钟，定时器间隔 16 毫秒，启动时刻作为角度计算起点。"""
        super().__init__()
        self._widgets: weakref.WeakSet[QWidget] = weakref.WeakSet()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._started_at = monotonic()

    def add(self, widget: QWidget) -> None:
        """注册需要旋转的控件，控件销毁时自动移除。

        Args:
            widget: 要旋转的控件；以弱引用保存。
        """
        self._widgets.add(widget)
        reference = weakref.ref(widget)
        widget.destroyed.connect(lambda *_: self._remove_destroyed(reference))
        self._sync()

    def remove(self, widget: QWidget) -> None:
        """移除不再旋转的控件。

        Args:
            widget: 要移除的控件。
        """
        self._discard(widget)
        self._sync()

    def _remove_destroyed(self, reference: weakref.ReferenceType[QWidget]) -> None:
        """控件销毁后将其移出集合并同步定时器。

        Args:
            reference: 指向已销毁控件的弱引用。
        """
        widget = reference()
        if widget is not None:
            self._discard(widget)
        self._sync()

    def _discard(self, widget: QWidget) -> None:
        """从集合中移除控件，忽略底层对象已被删除的错误。

        Args:
            widget: 要移除的控件。
        """
        try:
            self._widgets.discard(widget)
        except RuntimeError:
            return

    def angle(self, period: float) -> float:
        """返回当前动画角度。

        Args:
            period: 旋转一圈的秒数；小于等于 0 时角度恒为 0。

        Returns:
            当前角度（度），范围 [0, 360)。
        """
        if period <= 0:
            return 0.0
        return ((monotonic() - self._started_at) / period * 360.0) % 360.0

    def _tick(self) -> None:
        """刷新所有活跃控件，没有活跃控件时停止定时器。"""
        visible = False
        for widget in tuple(self._widgets):
            if self._is_active(widget):
                visible = True
                widget.update()
        if not visible:
            self._timer.stop()

    def _sync(self) -> None:
        """存在活跃控件且定时器未运行时启动定时器。"""
        if any(self._is_active(widget) for widget in tuple(self._widgets)):
            if not self._timer.isActive():
                self._timer.start()

    def _is_active(self, widget: QWidget) -> bool:
        """判断控件是否可见且所在窗口未最小化。

        Args:
            widget: 要检查的控件；底层对象已被删除时会被移除并视为不活跃。

        Returns:
            活跃返回 True，否则返回 False。
        """
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
    """延迟创建并返回全局共享的动画时钟。

    Returns:
        进程内唯一的 SpinClock 实例。
    """
    global spin_clock
    if spin_clock is None:
        spin_clock = SpinClock()
    return spin_clock
