"""共享旋转动画时钟。"""

from __future__ import annotations

import weakref
from time import monotonic

from pyside_iconify._qt import QObject, QTimer, QWidget


class SpinClock(QObject):
    """用一个定时器驱动所有可见旋转图标。

    控件以弱引用保存；定时器仅在存在可见控件时运行。
    """

    def __init__(self) -> None:
        """创建时钟，定时器间隔 16 毫秒，启动时刻作为角度计算起点。"""
        super().__init__()
        self._widgets: weakref.WeakSet[QWidget] = weakref.WeakSet()
        # 已经补画过"最后一帧"、正在等待重新被需要的控件
        self._settling: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._started_at = monotonic()

    def add(self, widget: QWidget) -> None:
        """注册需要旋转的控件，控件销毁时自动移除。

        Args:
            widget: 要旋转的控件；以弱引用保存。
        """
        if widget in self._widgets:
            self._sync()
            return
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
        self._settling.discard(id(widget))
        try:
            self._widgets.discard(widget)
        except RuntimeError:
            return

    def elapsed(self) -> float:
        """返回时钟启动以来的秒数，所有动画共用同一时间轴。

        Returns:
            自时钟创建起经过的秒数。
        """
        return monotonic() - self._started_at

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
        """刷新所有活跃控件，没有活跃控件时停止定时器。

        控件刚好从"需要刷新"变成"不需要"的那一次（动画播完、被暂停）还要再画最后一帧，
        否则画面会停在倒数第二帧；这次刷新之后才把它交还。
        """
        visible = False
        for widget in tuple(self._widgets):
            if not self._is_visible(widget):
                continue
            if self._wants_frames(widget):
                visible = True
                self._settling.discard(id(widget))
                widget.update()
            elif id(widget) not in self._settling:
                self._settling.add(id(widget))
                widget.update()
        if not visible:
            self._timer.stop()

    def _sync(self) -> None:
        """存在活跃控件且定时器未运行时启动定时器。"""
        if any(self._is_active(widget) for widget in tuple(self._widgets)):
            if not self._timer.isActive():
                self._timer.start()

    def _is_visible(self, widget: QWidget) -> bool:
        """判断控件是否可见且所在窗口未最小化。

        Args:
            widget: 要检查的控件；底层对象已被删除时会被移除并视为不可见。

        Returns:
            可见返回 True，否则返回 False。
        """
        try:
            return widget.isVisible() and not widget.window().isMinimized()
        except RuntimeError:
            self._discard(widget)
            return False

    @staticmethod
    def _wants_frames(widget: QWidget) -> bool:
        """控件此刻是否还需要继续刷新。

        控件可以声明"我现在没东西在动"（如 SMIL 动画已播完或已暂停），
        这样播完的图标不会让定时器一直转。

        Args:
            widget: 要询问的控件

        Returns:
            没有 _needs_frames 方法的控件一律视为需要。
        """
        needs_frames = getattr(widget, "_needs_frames", None)
        return True if needs_frames is None else bool(needs_frames())

    def _is_active(self, widget: QWidget) -> bool:
        """判断控件是否可见、未最小化且仍需要刷新。

        Args:
            widget: 要检查的控件

        Returns:
            活跃返回 True，否则返回 False。
        """
        return self._is_visible(widget) and self._wants_frames(widget)

    def sync(self) -> None:
        """在可见性变化后同步定时器。"""
        self._sync()


class Playhead:
    """一个控件自己的播放进度，支持暂停、倍速和重播。

    SMIL 图标的时间轴是"从这个控件开始播放那一刻"算起的，所以每个控件各有一个播放头；
    它只记录三件事：从哪个时刻开始计时、倍速、暂停在了哪里，因此暂停、继续、重播都几乎没有成本。
    时间来自调用方传入的"现在"，便于测试，也让所有控件共用共享时钟的同一时间轴。
    """

    def __init__(self, speed: float = 1.0) -> None:
        """创建播放头，初始为尚未开始。

        Args:
            speed: 播放速度倍率；须大于 0
        """
        self._speed = speed
        self._origin: float | None = None
        self._paused_at: float | None = None
        self._frozen = 0.0

    @property
    def speed(self) -> float:
        """当前的播放速度倍率。"""
        return self._speed

    @property
    def started(self) -> bool:
        """是否已经开始过计时。"""
        return self._origin is not None

    @property
    def paused(self) -> bool:
        """当前是否处于暂停。"""
        return self._paused_at is not None

    def start(self, now: float) -> None:
        """从头开始计时；已开始过则不变。

        Args:
            now: 共享时钟当前秒数
        """
        if self._origin is None:
            self._origin = now
            self._frozen = 0.0

    def restart(self, now: float) -> None:
        """从头重新计时，并取消暂停。

        Args:
            now: 共享时钟当前秒数
        """
        self._origin = now
        self._paused_at = None
        self._frozen = 0.0

    def elapsed(self, now: float) -> float:
        """已经播放的秒数（已乘倍速）。

        Args:
            now: 共享时钟当前秒数

        Returns:
            播放秒数；尚未开始为 0，暂停时保持暂停瞬间的值。
        """
        if self._origin is None:
            return 0.0
        reference = self._paused_at if self._paused_at is not None else now
        return max(0.0, (reference - self._origin) * self._speed) + self._frozen

    def pause(self, now: float) -> None:
        """暂停在当前画面。

        Args:
            now: 共享时钟当前秒数
        """
        if self._origin is not None and self._paused_at is None:
            self._paused_at = now

    def resume(self, now: float) -> None:
        """从暂停处继续；未暂停则不变。

        Args:
            now: 共享时钟当前秒数
        """
        if self._origin is None:
            self.start(now)
            return
        if self._paused_at is not None:
            self._origin += now - self._paused_at
            self._paused_at = None

    def set_speed(self, speed: float, now: float) -> None:
        """改变倍速，已经播放的部分保持不变。

        Args:
            speed: 新的倍速，须大于 0
            now: 共享时钟当前秒数
        """
        self._frozen = self.elapsed(now)
        if self._origin is not None:
            self._origin = now if self._paused_at is None else self._paused_at
        self._speed = speed


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
