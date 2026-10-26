"""内置动画的取值计算，不依赖 Qt。"""

from __future__ import annotations

import math
from dataclasses import dataclass

ANIMATIONS: tuple[str, ...] = ("spin", "pulse", "breathe", "ping", "bounce")

# 未指定周期时各动画的默认秒数；spin 的默认值来自全局配置的 spin_period。
DEFAULT_PERIODS: dict[str, float] = {
    "pulse": 1.0,
    "breathe": 2.0,
    "ping": 1.0,
    "bounce": 1.0,
}

# 量化帧率与每周期最少帧数。帧数随周期增长（周期秒数 x 帧率），
# 这样周期很长时画面仍和屏幕刷新同步，不会一格一格地跳；
# 同尺寸同颜色的图标最多渲染这么多张位图，其余命中缓存。
FRAME_RATE = 60
MIN_STEPS = 48

# 各动画默认的变化幅度：
# pulse 缩小的比例，breathe 淡出的比例，
# ping 水波扩散到原大小的 (1 + 幅度) 倍，bounce 跳起的高度占图标高度的比例。
DEFAULT_DEPTHS: dict[str, float] = {
    "pulse": 0.25,
    "breathe": 0.7,
    "ping": 1.0,
    "bounce": 0.25,
}
MIN_SCALE = 0.01

# 与 Tailwind 的 animate-ping、animate-bounce 一致：水波在一个周期的前 75% 扩散，
# 其余时间不可见；弹跳下落用加速曲线、上升用减速曲线。
PING_ACTIVE = 0.75
EASE_OUT = (0.0, 0.0, 0.2, 1.0)
EASE_IN = (0.8, 0.0, 1.0, 1.0)


@dataclass(frozen=True, slots=True)
class AnimationFrame:
    """某一时刻的动画取值。

    Attributes:
        rotate: 额外旋转角度，单位为度
        scale: 图标本体的缩放系数；1 表示铺满，ping、bounce 为给水波和弹跳留出空间会小于 1
        opacity: 额外不透明度系数；与其他不透明度相乘
        offset_y: 图标本体向下的位移，单位为画布高度的比例；负值向上
        ghost_scale: 水波残影的缩放系数，与 scale 同一基准；0 表示没有残影
        ghost_opacity: 水波残影的不透明度系数；0 表示没有残影
    """

    rotate: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0
    offset_y: float = 0.0
    ghost_scale: float = 0.0
    ghost_opacity: float = 0.0

    @property
    def shape(self) -> tuple[float, float, float, float]:
        """影响位图形状的四个取值，用于组成缓存键。"""
        return (self.scale, self.offset_y, self.ghost_scale, self.ghost_opacity)


STATIC_FRAME = AnimationFrame()


def _bezier(x1: float, y1: float, x2: float, y2: float, progress: float) -> float:
    """按 CSS cubic-bezier(x1, y1, x2, y2) 计算缓动后的进度。

    Args:
        x1: 第一个控制点的横坐标；0 到 1
        y1: 第一个控制点的纵坐标
        x2: 第二个控制点的横坐标；0 到 1
        y2: 第二个控制点的纵坐标
        progress: 时间进度；0 到 1，超出时按端点处理

    Returns:
        缓动后的取值；端点处分别为 0 和 1。
    """
    if progress <= 0.0:
        return 0.0
    if progress >= 1.0:
        return 1.0

    def coordinate(first: float, second: float, t: float) -> float:
        """三次贝塞尔曲线在参数 t 处的一个坐标分量。

        Args:
            first: 第一个控制点的该分量
            second: 第二个控制点的该分量
            t: 曲线参数，0 到 1

        Returns:
            该分量的取值（两端点固定为 0 和 1）。
        """
        inverse = 1.0 - t
        return 3.0 * inverse * inverse * t * first + 3.0 * inverse * t * t * second + t**3

    # 横坐标关于 t 单调，二分法求出对应的 t
    low, high = 0.0, 1.0
    for _ in range(32):
        middle = (low + high) / 2.0
        if coordinate(x1, x2, middle) < progress:
            low = middle
        else:
            high = middle
    return coordinate(y1, y2, (low + high) / 2.0)


def frame_at(
    kind: str | None, elapsed: float, period: float, depth: float | None = None
) -> AnimationFrame:
    """计算动画在指定时刻的取值。

    Args:
        kind: 动画名称；None 或未知名称返回静止帧
        elapsed: 已经过的秒数
        period: 一个周期的秒数；须为正数
        depth: 变化幅度，0 到 1；None 用该动画的默认值。spin 无此参数

    Returns:
        该时刻的 AnimationFrame。spin 的角度不做量化，由调用方按需量化；
        其余动画已按 FRAME_RATE 量化为每周期 max(MIN_STEPS, 周期秒数 x
        FRAME_RATE) 帧，画面变化次数与屏幕刷新同步。
    """
    if kind is None or period <= 0:
        return STATIC_FRAME
    if kind == "spin":
        return AnimationFrame(rotate=(elapsed / period * 360.0) % 360.0)
    if kind not in DEFAULT_DEPTHS:
        return STATIC_FRAME
    phase = (elapsed / period) % 1.0
    steps = max(MIN_STEPS, round(period * FRAME_RATE))
    # 加一点容差，正好落在帧边界上的时刻不会因浮点误差被归到上一帧
    step = math.floor(phase * steps + 1e-9) / steps
    amount = DEFAULT_DEPTHS[kind] if depth is None else depth
    if kind == "pulse":
        eased = 0.5 - 0.5 * math.cos(2.0 * math.pi * step)
        return AnimationFrame(scale=max(MIN_SCALE, 1.0 - amount * eased))
    if kind == "breathe":
        eased = 0.5 - 0.5 * math.cos(2.0 * math.pi * step)
        return AnimationFrame(opacity=1.0 - amount * eased)
    # ping、bounce 都把本体缩小到 1 / (1 + 幅度)，剩下的空间留给水波或弹跳，
    # 这样动画到最大幅度时刚好贴着控件边缘，不会被裁掉。
    base = 1.0 / (1.0 + amount)
    if kind == "ping":
        if step >= PING_ACTIVE:
            return AnimationFrame(scale=base)
        spread = _bezier(*EASE_OUT, step / PING_ACTIVE)
        return AnimationFrame(
            scale=base,
            ghost_scale=base + (1.0 - base) * spread,
            ghost_opacity=1.0 - spread,
        )
    # bounce：周期起点在最高处，前半周期下落，后半周期上升
    if step < 0.5:
        height = 1.0 - _bezier(*EASE_IN, step / 0.5)
    else:
        height = _bezier(*EASE_OUT, (step - 0.5) / 0.5)
    return AnimationFrame(scale=base, offset_y=(1.0 - base) / 2.0 * (1.0 - 2.0 * height))
