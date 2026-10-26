"""SMIL 动画图标的播放层：缓存解析结果，把"时刻"换成一份静态 IconData。

渲染管线本身不认识 SMIL；这里把每一帧的静态 body 包成 IconData 交给它，
这样颜色替换、翻转、旋转、缓存全部沿用原有路径。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from threading import RLock

from pyside_iconify._logging import logger
from pyside_iconify.core.smil import (
    Timeline,
    UnsupportedSmilError,
    has_animation,
    parse_timeline,
)
from pyside_iconify.core.smil_eval import Schedule, evaluate
from pyside_iconify.core.types import IconData

FRAME_RATE = 60
MIN_STEPS = 48
# 无限循环的图标，画面每隔多少帧才会出现一次新的帧，用于限制缓存键的取值数量
_MAX_CACHED_PLANS = 512


@dataclass(frozen=True, slots=True)
class Plan:
    """一个图标的播放计划。

    Attributes:
        timeline: 解析好的时间轴
        schedule: 展开后的运行实例
        duration: 非循环部分的总时长，秒；播放到这个时刻后画面不再变化
        period: 循环周期，秒；0 表示不循环
    """

    timeline: Timeline
    schedule: Schedule
    duration: float
    period: float

    @property
    def loops(self) -> bool:
        """图标是否无限循环。"""
        return self.period > 0.0

    @property
    def finish(self) -> float:
        """完成态对应的时刻，秒。"""
        return self.schedule.final


class _Plans:
    """按 (图标 body) 缓存播放计划，解析失败的图标也记住，避免反复解析和刷日志。"""

    def __init__(self) -> None:
        """创建空的缓存。"""
        self._items: dict[str, Plan | None] = {}
        self._lock = RLock()

    def get(self, body: str, label: str) -> Plan | None:
        """返回图标的播放计划。

        Args:
            body: 图标 body
            label: 用于日志的图标名

        Returns:
            Plan；body 里没有 SMIL 动画，或使用了不支持的写法时为 None。
        """
        with self._lock:
            if body in self._items:
                return self._items[body]
        plan = _build(body, label)
        with self._lock:
            if len(self._items) >= _MAX_CACHED_PLANS:
                self._items.pop(next(iter(self._items)))
            self._items[body] = plan
        return plan

    def clear(self) -> None:
        """清空缓存。"""
        with self._lock:
            self._items.clear()


def _build(body: str, label: str) -> Plan | None:
    """解析并展开一个图标；失败时记一次警告并返回 None。

    Args:
        body: 图标 body
        label: 用于日志的图标名

    Returns:
        Plan 或 None。
    """
    if not has_animation(body):
        return None
    try:
        timeline = parse_timeline(body)
        if not timeline.tracks:
            return None
        schedule = Schedule(timeline)
    except UnsupportedSmilError as error:
        logger.warning("icon %s uses unsupported SMIL (%s); showing its static final state", label, error)
        return None
    return Plan(timeline, schedule, schedule.final, schedule.period)


plans = _Plans()


def get_plan(data: IconData, label: str = "") -> Plan | None:
    """取图标的播放计划。

    Args:
        data: 图标数据
        label: 用于日志的图标名

    Returns:
        Plan；图标不含 SMIL 动画或不受支持时为 None。
    """
    return plans.get(data.body, label)


def is_animated(data: IconData) -> bool:
    """图标是否带有可播放的 SMIL 动画。

    Args:
        data: 图标数据

    Returns:
        可以播放时为 True。
    """
    return get_plan(data) is not None


def frame_step(plan: Plan) -> float:
    """播放时每一帧的时间间隔，秒。

    帧数随总时长增长（每秒 FRAME_RATE 帧、不少于 MIN_STEPS 帧），
    这样长动画也不会一格一格地跳，同时同一时刻只会出现有限种画面，便于缓存命中。

    Args:
        plan: 播放计划

    Returns:
        间隔秒数。
    """
    span = plan.period if plan.loops else max(plan.duration, 0.001)
    steps = max(MIN_STEPS, round(span * FRAME_RATE))
    return span / steps


def quantize(plan: Plan, elapsed: float) -> float:
    """把"已播放的秒数"换成要渲染的时刻（量化到帧，并按周期折回）。

    非循环图标播放到完成态后停在那里；循环图标先播完第一遍，之后在周期内折回。

    Args:
        plan: 播放计划
        elapsed: 已播放的秒数，须大于等于 0

    Returns:
        用来求值的时刻，秒。
    """
    elapsed = max(elapsed, 0.0)
    if not plan.loops:
        return min(_snap(plan, elapsed), plan.duration)
    # 循环图标：时间轴里有一个"起始段"（各轨道的 begin 偏移），之后才进入稳定的周期。
    # 起始段按原样播放，进入周期后用取模折回，保证无论播多久时刻都有界。
    lead = _lead_in(plan)
    if elapsed <= lead:
        return _snap(plan, elapsed)
    return lead + _snap(plan, (elapsed - lead) % plan.period)


def _lead_in(plan: Plan) -> float:
    """循环图标进入稳定周期之前的时长。

    Args:
        plan: 播放计划

    Returns:
        秒数；取各轨道第一次运行的最晚起点。
    """
    latest = 0.0
    for instances in plan.schedule.instances:
        if instances and math.isinf(instances[0].end):
            latest = max(latest, instances[0].start)
    return latest


def _snap(plan: Plan, value: float) -> float:
    """量化到帧边界。

    Args:
        plan: 播放计划
        value: 时刻，秒

    Returns:
        不大于 value 的最近帧边界，已修掉浮点误差。
    """
    step = frame_step(plan)
    return round(math.floor(value / step + 1e-9) * step, 6)


def render_data(data: IconData, plan: Plan, moment: float) -> IconData:
    """求出指定时刻的静态图标数据。

    Args:
        data: 原图标数据，其尺寸、翻转等元数据保持不变
        plan: 播放计划
        moment: 时刻，秒

    Returns:
        body 被替换为该时刻静态画面的新 IconData。
    """
    return replace(data, body=evaluate(plan.timeline, plan.schedule, moment))


def final_data(data: IconData, label: str = "") -> IconData:
    """求出完成态（动画播完后的画面）对应的静态图标数据。

    Args:
        data: 原图标数据
        label: 用于日志的图标名

    Returns:
        完成态的 IconData；图标没有 SMIL 动画或不受支持时返回原数据。
    """
    plan = get_plan(data, label)
    if plan is None:
        return data
    try:
        return render_data(data, plan, plan.finish)
    except UnsupportedSmilError as error:
        logger.warning("icon %s cannot be evaluated (%s); showing it as written", label, error)
        return data
