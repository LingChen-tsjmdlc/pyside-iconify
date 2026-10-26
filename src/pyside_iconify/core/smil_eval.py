"""SMIL 时间轴求值：给定时刻，算出每个被动画元素的属性值，生成静态 SVG body。

不依赖 Qt。解析见 smil.py。
"""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from xml.etree import ElementTree

from pyside_iconify.core.smil import (
    BeginRef,
    Timeline,
    Track,
    UnsupportedSmilError,
    local_name,
    parse_time,
)

# 起始时间引用链展开的时间上限（秒）。循环引用（a 结束后启动 b，b 结束后启动 a）
# 在这个窗口内展开成具体实例；超过窗口的时刻按周期折回，见 Schedule.wrap。
_HORIZON = 600.0
_MAX_INSTANCES = 4096
# 画面周期的上限（秒）：超过它就不折回，缓存键会随时间变化但画面本身仍正确
_MAX_PERIOD = 60.0


@dataclass(frozen=True, slots=True)
class Instance:
    """一条轨道的一次运行实例。

    Attributes:
        start: 起点，秒
        end: 单次运行的结束时刻（start + 简单时长 x 重复次数），无限重复时为 inf
        stop: 被后一个实例打断的时刻（restart="always"），没有时为 inf
    """

    start: float
    end: float
    stop: float


class Schedule:
    """把时间轴里所有轨道的起始时间引用展开成具体的运行实例。

    Attributes:
        instances: 每条轨道的实例列表，按起点升序
        period: 整个图标的循环周期；非循环图标为 0
        final: 完成态对应的时刻，所有非循环动画在此时刻都已结束
    """

    def __init__(self, timeline: Timeline) -> None:
        """展开起始时间。

        Args:
            timeline: 解析好的时间轴
        """
        self._timeline = timeline
        self.instances: list[list[Instance]] = [[] for _ in timeline.tracks]
        self._expand()
        self.final = self._final_time()
        self.period = self._period()

    def _expand(self) -> None:
        """按时间顺序反复展开引用，直到不再产生新的实例。"""
        tracks = self._timeline.tracks
        ids = self._timeline.ids
        starts: list[list[float]] = [[] for _ in tracks]
        for index, track in enumerate(tracks):
            for begin in track.begins:
                if not isinstance(begin, BeginRef):
                    starts[index].append(float(begin))
        # 引用展开是个不动点迭代：每轮把被引用轨道已知实例的 begin/end 时刻
        # 折算成引用者的新起点，直到没有新的起点出现或超出时间窗口。
        for _ in range(64):
            changed = False
            ends = [self._ends(index, starts[index]) for index in range(len(tracks))]
            for index, track in enumerate(tracks):
                for begin in track.begins:
                    if not isinstance(begin, BeginRef) or begin.target not in ids:
                        continue
                    source = ids[begin.target]
                    moments = starts[source] if begin.event == "begin" else ends[source]
                    for moment in moments:
                        value = moment + begin.offset
                        if math.isfinite(value) and value <= _HORIZON and not _has(starts[index], value):
                            starts[index].append(value)
                            changed = True
                if len(starts[index]) > _MAX_INSTANCES:
                    raise UnsupportedSmilError("too many begin instances")
            if not changed:
                break
        for index, track in enumerate(tracks):
            self.instances[index] = self._instances(track, sorted(set(starts[index])))

    def _ends(self, index: int, starts: list[float]) -> list[float]:
        """计算一条轨道现有各起点对应的结束时刻。

        Args:
            index: 轨道下标
            starts: 该轨道当前已知的起点

        Returns:
            有限的结束时刻列表；无限重复的实例没有结束时刻，不在其中。
        """
        track = self._timeline.tracks[index]
        total = track.duration * track.repeat
        if not math.isfinite(total):
            return []
        return [start + total for start in starts]

    @staticmethod
    def _instances(track: Track, starts: list[float]) -> list[Instance]:
        """把升序起点转成实例，并处理 restart 打断。

        Args:
            track: 轨道
            starts: 升序且去重的起点

        Returns:
            实例列表；restart="always" 时，每个实例在下一个起点处被打断。
        """
        total = track.duration * track.repeat if track.kind != "set" else 0.0
        result: list[Instance] = []
        for position, start in enumerate(starts):
            following = starts[position + 1] if position + 1 < len(starts) else math.inf
            stop = following if track.restart else math.inf
            result.append(Instance(start, start + total, stop))
        return result

    def _final_time(self) -> float:
        """完成态时刻：第一轮动画全部播完之后。

        起始时间互相引用形成循环时，会被展开成一长串实例；这里只看到"第一轮"
        为止：从每条轨道的最早实例开始，到该实例结束；循环的后续实例不计入。

        Returns:
            秒数；含无限重复的轨道取其第一个完整周期结束的时刻。
        """
        latest = 0.0
        for track, instances in zip(self._timeline.tracks, self.instances):
            if not instances:
                continue
            first = instances[0]
            if math.isfinite(first.end):
                latest = max(latest, min(first.end, first.stop))
            else:
                latest = max(latest, first.start + track.duration)
        return latest

    def _period(self) -> float:
        """整个图标的循环周期。

        各条循环轨道（无限重复，或靠 ``id.end`` 互相引用而周期性重现的轨道）各有自己的周期，
        整个画面的周期是它们的最小公倍数。例如一条 1.5 秒、一条 2 秒的循环，画面每 6 秒才重复一次。

        Returns:
            秒数；图标不循环时为 0；最小公倍数超过 ``_MAX_PERIOD`` 时也返回 0，
            表示不折回，按真实时间一直播放。
        """
        periods: set[int] = set()
        for track, instances in zip(self._timeline.tracks, self.instances):
            if not instances:
                continue
            if math.isinf(instances[0].end):
                periods.add(round(track.duration * 1000))
                continue
            gaps = [round((b.start - a.start) * 1000) for a, b in zip(instances, instances[1:])]
            # 链式引用形成的循环：相邻实例的间隔在末尾稳定下来
            if len(gaps) >= 3 and gaps[-1] > 0 and len(set(gaps[-3:])) == 1:
                periods.add(gaps[-1])
        if not periods:
            return 0.0
        total = 1
        for value in periods:
            total = total * value // math.gcd(total, value)
            if total > _MAX_PERIOD * 1000:
                return 0.0
        return total / 1000.0


def _has(values: list[float], candidate: float) -> bool:
    """判断列表里是否已有（在浮点误差内）相同的时刻。

    Args:
        values: 已有时刻
        candidate: 待检查时刻

    Returns:
        已有则为 True。
    """
    return any(abs(value - candidate) < 1e-9 for value in values)


def evaluate(timeline: Timeline, schedule: Schedule, time: float) -> str:
    """在指定时刻求值，返回静态 SVG body。

    Args:
        timeline: 解析好的时间轴
        schedule: 展开后的运行实例
        time: 时刻，秒；负数按 0 处理

    Returns:
        可交给现有渲染管线的 SVG body 片段。
    """
    root = copy.deepcopy(timeline.root)
    elements: dict[int, ElementTree.Element] = {}
    parents: dict[int, ElementTree.Element] = {}
    for element in root.iter():
        marker = element.get("data-i")
        if marker is not None:
            elements[int(marker)] = element
        for child in element:
            parents[id(child)] = element
    transforms: dict[int, list[str]] = {}
    # SMIL 的优先级规则：作用在同一属性上的多条动画，开始时间晚的优先（相同则文档顺序靠后的优先）。
    # 所以先按"当前实例的起点"升序求值，后写入的覆盖先写入的。
    ordered: list[tuple[float, int]] = []
    for index, (track, instances) in enumerate(zip(timeline.tracks, schedule.instances)):
        found = _active_instance(track, instances, max(time, 0.0))
        ordered.append((found[0].start if found else -math.inf, index))
    ordered.sort()
    for _start, index in ordered:
        track = timeline.tracks[index]
        instances = schedule.instances[index]
        element = elements.get(track.target)
        base = _base_value(element, track.attribute, parents) if element is not None else ""
        value = _track_value(_with_base(track, base), instances, time)
        if value is None:
            continue
        if element is None:
            continue
        if track.kind == "transform":
            transforms.setdefault(track.target, []).append(_transform_text(track, value, element))
        elif track.kind == "motion":
            transforms.setdefault(track.target, []).append(value)
        else:
            _apply(element, track, value)
    for target, parts in transforms.items():
        element = elements[target]
        base = element.get("transform", "")
        element.set("transform", " ".join(part for part in (base, *parts) if part))
    for element in root.iter():
        element.attrib.pop("data-i", None)
        _apply_origin(element)
    return "".join(
        ElementTree.tostring(child, encoding="unicode") for child in root
    ).replace(' xmlns="http://www.w3.org/2000/svg"', "").replace(' xmlns:ns0="http://www.w3.org/1999/xlink"', "")


# 会从父元素继承的表现属性，以及没有任何地方设置时的 SVG 默认值
_INHERITED = {
    "fill", "fill-opacity", "stroke", "stroke-opacity", "stroke-width",
    "stroke-dashoffset", "stroke-dasharray", "stroke-linecap", "stroke-linejoin",
}
_DEFAULTS = {
    "opacity": "1", "fill-opacity": "1", "stroke-opacity": "1",
    "stroke-width": "1", "stroke-dashoffset": "0",
    # 几何属性没写时都是 0，例如不带 r 的 circle 会从半径 0 长出来
    "r": "0", "rx": "0", "ry": "0", "cx": "0", "cy": "0",
    "x": "0", "y": "0", "width": "0", "height": "0",
}


def _base_value(
    element: ElementTree.Element, attribute: str, parents: dict[int, ElementTree.Element]
) -> str:
    """求被动画属性在没有动画时的取值（基础值）。

    元素自己写了就用自己的；可继承的属性沿祖先往上找；都没有就用 SVG 默认值。

    Args:
        element: 被动画的元素
        attribute: 属性名
        parents: 元素到父元素的映射，键为 ``id(元素)``

    Returns:
        基础值文本；找不到且没有已知默认值时为空串。
    """
    current: ElementTree.Element | None = element
    while current is not None:
        value = current.get(attribute)
        if value is not None:
            return value
        if attribute not in _INHERITED:
            break
        current = parents.get(id(current))
    return _DEFAULTS.get(attribute, "")


def _with_base(track: Track, base: str) -> Track:
    """to 单独出现时起点是元素的基础值：把空起点替换成基础值。

    Args:
        track: 轨道
        base: 被动画属性在元素上的基础取值，没有时为空串

    Returns:
        起点已填好的轨道；不需要替换时原样返回。
    """
    if track.kind not in {"animate", "transform"} or not track.values or track.values[0] != "":
        return track
    if base == "":
        base = track.values[-1]
    from dataclasses import replace

    return replace(track, values=[base, *track.values[1:]])


def _active_instance(track: Track, instances: list[Instance], time: float) -> tuple[Instance, float] | None:
    """找出时刻 time 起作用的实例，返回它和实例内局部时间。

    已结束且不 freeze 的实例不再起作用；已结束且 freeze 的实例保持最后一个值。

    Args:
        track: 轨道
        instances: 轨道的实例列表（按起点升序）
        time: 时刻，秒

    Returns:
        (实例, 局部时间)；轨道在该时刻完全没有开始、或已结束并移除时返回 None。
    """
    chosen: Instance | None = None
    for instance in instances:
        if instance.start <= time:
            chosen = instance
        else:
            break
    if chosen is None:
        return None
    local = min(time, chosen.stop) - chosen.start
    return chosen, local


def _track_value(track: Track, instances: list[Instance], time: float) -> str | None:
    """计算一条轨道在时刻 time 的取值文本。

    Args:
        track: 轨道
        instances: 轨道的实例列表
        time: 时刻，秒

    Returns:
        属性值文本；轨道此刻没有作用（未开始，或结束后不 freeze）时为 None。
    """
    found = _active_instance(track, instances, max(time, 0.0))
    if found is None:
        return None
    instance, local = found
    if track.kind == "set":
        return track.values[0]
    total = track.duration * track.repeat
    finished = math.isfinite(total) and local >= total
    # 被下一个实例取代的旧实例，在被取代的那一刻就算结束，之后由新实例接管
    superseded = time >= instance.stop
    if (finished or superseded) and not track.freeze:
        return None
    progress = 1.0 if finished else (local % track.duration) / track.duration
    if track.kind == "motion":
        return _motion_value(track, progress)
    return _interpolate(track, progress)


def _interpolate(track: Track, progress: float) -> str:
    """在关键帧之间取值。

    连续模式（linear、spline）：在相邻关键帧之间插值。
    离散模式（discrete）：每个取值保持到下一个关键帧时刻，不插值。

    Args:
        track: 轨道
        progress: 简单时长内的进度，0 到 1

    Returns:
        该进度处的取值文本。
    """
    values, times = track.values, track.key_times
    if len(values) == 1:
        return values[0]
    if track.calc_mode == "discrete":
        chosen = 0
        for index, moment in enumerate(times):
            if progress >= moment:
                chosen = index
        return values[chosen]
    if progress >= times[-1]:
        return values[-1]
    segment = 0
    for index in range(len(times) - 1):
        if times[index] <= progress < times[index + 1]:
            segment = index
            break
    start, end = times[segment], times[segment + 1]
    local = 0.0 if end <= start else (progress - start) / (end - start)
    if track.calc_mode == "spline":
        local = bezier(*track.key_splines[segment], local)
    return _mix(track, values[segment], values[segment + 1], local)


def bezier(x1: float, y1: float, x2: float, y2: float, progress: float) -> float:
    """按 CSS cubic-bezier(x1, y1, x2, y2) 计算缓动后的进度。

    Args:
        x1: 第一个控制点的横坐标，0 到 1
        y1: 第一个控制点的纵坐标
        x2: 第二个控制点的横坐标，0 到 1
        y2: 第二个控制点的纵坐标
        progress: 时间进度，0 到 1

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

    low, high = 0.0, 1.0
    for _ in range(32):
        middle = (low + high) / 2.0
        if coordinate(x1, x2, middle) < progress:
            low = middle
        else:
            high = middle
    return coordinate(y1, y2, (low + high) / 2.0)


_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _mix(track: Track, first: str, second: str, ratio: float) -> str:
    """对两个取值做线性混合。

    Args:
        track: 轨道，用来判断属性类型
        first: 起始取值文本；空串表示基础值（由调用方在应用时处理）
        second: 结束取值文本
        ratio: 混合比例，0 到 1

    Returns:
        混合后的取值文本。

    Raises:
        UnsupportedSmilError: 两端的结构不一致，无法逐项混合。
    """
    if track.attribute == "d":
        return _mix_path(first, second, ratio)
    a = _NUMBER.findall(first)
    b = _NUMBER.findall(second)
    if len(a) != len(b):
        raise UnsupportedSmilError("cannot interpolate values with different shapes")
    # 其余取值（数字、变换参数、颜色之外的列表）只混合数字，保持第二个值的分隔符和单位
    pieces = _NUMBER.split(second)
    mixed = [_format(float(x) + (float(y) - float(x)) * ratio) for x, y in zip(a, b)]
    out = [pieces[0]]
    for number, tail in zip(mixed, pieces[1:]):
        out.append(number)
        out.append(tail)
    return "".join(out)


def _mix_path(first: str, second: str, ratio: float) -> str:
    """路径数据逐命令逐数字混合；两端命令结构必须一致。

    Args:
        first: 起始路径
        second: 结束路径
        ratio: 混合比例

    Returns:
        混合后的路径。

    Raises:
        UnsupportedSmilError: 两端的命令序列或参数个数不同。
    """
    a = re.findall(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", first)
    b = re.findall(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", second)
    if len(a) != len(b):
        raise UnsupportedSmilError("path data differ in structure")
    out: list[str] = []
    for x, y in zip(a, b):
        if x.isalpha() or y.isalpha():
            if x != y:
                raise UnsupportedSmilError("path data differ in structure")
            out.append(x)
        else:
            out.append(_format(float(x) + (float(y) - float(x)) * ratio))
    return " ".join(out)


def _format(number: float) -> str:
    """把数字格式化为尽量短的文本。

    Args:
        number: 数值

    Returns:
        不带多余零的十进制文本，最多保留 6 位有效小数。
    """
    text = f"{number:.6f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _motion_value(track: Track, progress: float) -> str:
    """animateMotion 沿路径移动，按路径的弧长均匀取点（默认 calcMode="paced"）。

    支持 M、L、H、V、C、S、Q、T、Z 及其小写（相对）形式；不支持圆弧（A）。

    Args:
        track: motion 轨道
        progress: 简单时长内的进度，0 到 1

    Returns:
        translate 变换文本。

    Raises:
        UnsupportedSmilError: 路径为空、含圆弧或写法不合法。
    """
    points = _path_polyline(track.motion_path)
    if len(points) < 2:
        raise UnsupportedSmilError("animateMotion path has no length")
    lengths = [0.0]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.hypot(x2 - x1, y2 - y1))
    total = lengths[-1]
    if total <= 0.0:
        return f"translate({_format(points[0][0])} {_format(points[0][1])})"
    target = min(max(progress, 0.0), 1.0) * total
    index = 1
    while index < len(lengths) - 1 and lengths[index] < target:
        index += 1
    span = lengths[index] - lengths[index - 1]
    ratio = 0.0 if span <= 0 else (target - lengths[index - 1]) / span
    (x1, y1), (x2, y2) = points[index - 1], points[index]
    return f"translate({_format(x1 + (x2 - x1) * ratio)} {_format(y1 + (y2 - y1) * ratio)})"


_PATH_TOKEN = re.compile(r"([A-Za-z])|([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "Z": 0}


def _path_polyline(path: str) -> list[tuple[float, float]]:
    """把路径展开成折线点列，曲线按固定步数细分。

    Args:
        path: 路径数据

    Returns:
        折线顶点，闭合路径的最后一个点回到起点。

    Raises:
        UnsupportedSmilError: 含圆弧或写法不合法。
    """
    tokens = [(m.group(1), m.group(2)) for m in _PATH_TOKEN.finditer(path)]
    points: list[tuple[float, float]] = []
    x = y = start_x = start_y = 0.0
    last_control: tuple[float, float] | None = None
    last_command = ""
    index = 0
    command = ""
    steps = 24
    while index < len(tokens):
        letter, number = tokens[index]
        if letter:
            command = letter
            index += 1
            if command in "Zz":
                points.append((start_x, start_y))
                x, y = start_x, start_y
                continue
        if not command:
            raise UnsupportedSmilError("bad animateMotion path")
        upper = command.upper()
        if upper == "A":
            raise UnsupportedSmilError("arcs are not supported in animateMotion paths")
        if upper not in _ARITY:
            raise UnsupportedSmilError(f"unsupported path command: {command}")
        count = _ARITY[upper]
        values: list[float] = []
        for _ in range(count):
            if index >= len(tokens) or tokens[index][1] is None:
                raise UnsupportedSmilError("bad animateMotion path")
            values.append(float(tokens[index][1]))
            index += 1
        relative = command.islower()
        ox, oy = (x, y) if relative else (0.0, 0.0)
        if upper == "M":
            x, y = values[0] + ox, values[1] + oy
            start_x, start_y = x, y
            points.append((x, y))
            command = "l" if relative else "L"
        elif upper == "L":
            x, y = values[0] + ox, values[1] + oy
            points.append((x, y))
        elif upper == "H":
            x = values[0] + (x if relative else 0.0)
            points.append((x, y))
        elif upper == "V":
            y = values[0] + (y if relative else 0.0)
            points.append((x, y))
        elif upper == "C":
            p1 = (values[0] + ox, values[1] + oy)
            p2 = (values[2] + ox, values[3] + oy)
            p3 = (values[4] + ox, values[5] + oy)
            points.extend(_cubic((x, y), p1, p2, p3, steps))
            last_control = p2
            x, y = p3
        elif upper == "S":
            p1 = _reflect(last_control, (x, y)) if last_command in "CcSs" else (x, y)
            p2 = (values[0] + ox, values[1] + oy)
            p3 = (values[2] + ox, values[3] + oy)
            points.extend(_cubic((x, y), p1, p2, p3, steps))
            last_control = p2
            x, y = p3
        elif upper == "Q":
            c = (values[0] + ox, values[1] + oy)
            p3 = (values[2] + ox, values[3] + oy)
            points.extend(_quadratic((x, y), c, p3, steps))
            last_control = c
            x, y = p3
        else:  # T
            c = _reflect(last_control, (x, y)) if last_command in "QqTt" else (x, y)
            p3 = (values[0] + ox, values[1] + oy)
            points.extend(_quadratic((x, y), c, p3, steps))
            last_control = c
            x, y = p3
        last_command = command
    return points


def _reflect(control: tuple[float, float] | None, origin: tuple[float, float]) -> tuple[float, float]:
    """求上一个控制点关于当前点的对称点。

    Args:
        control: 上一个控制点
        origin: 当前点

    Returns:
        对称点；没有上一个控制点时返回当前点。
    """
    if control is None:
        return origin
    return (2 * origin[0] - control[0], 2 * origin[1] - control[1])


def _cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int,
) -> list[tuple[float, float]]:
    """三次贝塞尔曲线细分（不含起点）。

    Args:
        p0: 起点
        p1: 第一个控制点
        p2: 第二个控制点
        p3: 终点
        steps: 细分段数

    Returns:
        曲线上的点，最后一个是终点。
    """
    result = []
    for k in range(1, steps + 1):
        t = k / steps
        u = 1 - t
        result.append((
            u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        ))
    return result


def _quadratic(
    p0: tuple[float, float], c: tuple[float, float], p2: tuple[float, float], steps: int
) -> list[tuple[float, float]]:
    """二次贝塞尔曲线细分（不含起点）。

    Args:
        p0: 起点
        c: 控制点
        p2: 终点
        steps: 细分段数

    Returns:
        曲线上的点，最后一个是终点。
    """
    result = []
    for k in range(1, steps + 1):
        t = k / steps
        u = 1 - t
        result.append((
            u * u * p0[0] + 2 * u * t * c[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * c[1] + t * t * p2[1],
        ))
    return result


def _transform_text(track: Track, value: str, element: ElementTree.Element) -> str:
    """把 animateTransform 的取值写成 transform 片段。

    Args:
        track: transform 轨道
        value: 当前取值文本，如 ``"45 12 12"``
        element: 被动画的元素（用于 additive="replace" 时丢弃它自己的 transform）

    Returns:
        形如 ``rotate(45 12 12)`` 的文本。
    """
    numbers = " ".join(_NUMBER.findall(value))
    if track.kind == "transform" and not track.additive:
        element.attrib.pop("transform", None)
    return f"{track.transform_type}({numbers})"


def _apply(element: ElementTree.Element, track: Track, value: str) -> None:
    """把动画值写进元素的属性。

    additive="sum" 的数字属性和基础值相加；其他情况直接替换。

    Args:
        element: 被动画的元素，原地修改
        track: 轨道
        value: 当前取值文本；空串表示"保持基础值"
    """
    if value == "":
        return
    name = track.attribute
    if track.additive:
        base = element.get(name)
        if base is not None and _NUMBER.fullmatch(base.strip()) and _NUMBER.fullmatch(value.strip()):
            value = _format(float(base) + float(value))
    element.set(name, value)


def _apply_origin(element: ElementTree.Element) -> None:
    """把 ``transform-origin`` 折算进 ``transform``。

    Qt 不认 transform-origin。CSS 规定变换围绕该点进行，等价于
    ``translate(原点) 变换 translate(-原点)``。

    Args:
        element: 要处理的元素，原地修改；没有 transform-origin 时什么也不做
    """
    origin = element.attrib.pop("transform-origin", None)
    if origin is None:
        return
    numbers = _NUMBER.findall(origin)
    transform = element.get("transform", "")
    if len(numbers) != 2 or not transform:
        return
    x, y = float(numbers[0]), float(numbers[1])
    element.set(
        "transform", f"translate({_format(x)} {_format(y)}) {transform} translate({_format(-x)} {_format(-y)})"
    )


def finish_time(schedule: Schedule) -> float:
    """完成态对应的时刻。

    Args:
        schedule: 展开后的运行实例

    Returns:
        秒数。
    """
    return schedule.final


def at_finish(timeline: Timeline, schedule: Schedule) -> str:
    """求出完成态（动画播完后的画面）对应的 body。

    Args:
        timeline: 解析好的时间轴
        schedule: 展开后的运行实例

    Returns:
        SVG body 片段。
    """
    return evaluate(timeline, schedule, schedule.final)


__all__ = [
    "Instance",
    "Schedule",
    "at_finish",
    "bezier",
    "evaluate",
    "finish_time",
    "parse_time",
    "local_name",
]
