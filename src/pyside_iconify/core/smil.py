"""SMIL 动画解析：把图标 body 里的动画元素解析成时间轴。

只支持 SMIL（SVG 内置的 animate / set / animateTransform / animateMotion），
不依赖 Qt。遇到不支持的写法时抛出 UnsupportedSmilError，调用方据此降级为静态图。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree

from pyside_iconify._errors import IconifyError

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
_ANIMATION_TAGS = {"animate", "set", "animateTransform", "animateMotion"}

# 解析时就拒绝的属性：出现即降级，不做半成品
_UNSUPPORTED_ATTRIBUTES = ("keyPoints", "end", "min", "max", "repeatDur")
_TRANSFORM_TYPES = {"translate", "rotate", "scale"}


class UnsupportedSmilError(IconifyError):
    """图标使用了本库不支持的 SMIL 写法。"""


class InvalidSmilError(UnsupportedSmilError):
    """某个动画元素按 SMIL 规范本身就是无效的。

    规范规定无效的动画元素不起作用（浏览器也是这样处理），图标的其余部分照常播放。
    """


@dataclass(frozen=True, slots=True)
class BeginRef:
    """引用另一条动画开始或结束时刻的起始时间，如 ``a.end+0.5s``。

    Attributes:
        target: 被引用动画的 id
        event: "begin" 或 "end"
        offset: 在被引用时刻上再加的秒数，可为负
    """

    target: str
    event: str
    offset: float


@dataclass(slots=True)
class Track:
    """一条动画轨道，对应图标里的一个动画元素。

    Attributes:
        kind: "animate"、"set"、"transform" 或 "motion"
        target: 被动画的元素在文档中的序号（见 Timeline.elements）
        attribute: 被动画的属性名；transform 轨道为 "transform"，motion 轨道为 "motion"
        transform_type: transform 轨道的变换类型（translate、rotate、scale）
        id: 动画元素自己的 id，没有时为 None
        begins: 起始时间列表；元素是固定秒数，BeginRef 是引用其他动画
        duration: 单次时长，秒
        values: 关键帧取值（已按分号拆开、去掉空项）
        key_times: 与 values 等长的关键帧时刻，0 到 1
        calc_mode: "linear"、"discrete" 或 "spline"
        key_splines: spline 模式下每个区间的贝塞尔控制点 (x1, y1, x2, y2)
        repeat: 重复次数；math.inf 表示无限
        freeze: 结束后是否停在最后一个值（False 为回到基础值）
        additive: True 表示叠加在基础值之上（additive="sum"）
        restart: 是否允许在运行中被重新触发（restart="always"，缺省）
        motion_path: motion 轨道的路径数据
    """

    kind: str
    target: int
    attribute: str
    duration: float
    values: list[str]
    key_times: list[float]
    begins: list[float | BeginRef] = field(default_factory=lambda: [0.0])
    transform_type: str = ""
    id: str | None = None
    calc_mode: str = "linear"
    key_splines: list[tuple[float, float, float, float]] = field(default_factory=list)
    repeat: float = 1.0
    freeze: bool = False
    additive: bool = False
    restart: bool = True
    motion_path: str = ""


@dataclass(slots=True)
class Timeline:
    """一个图标的完整动画时间轴。

    Attributes:
        root: 解析后的 body 根（包在一个虚拟 g 里），保留全部非动画结构
        elements: 文档顺序的元素列表，Track.target 是这里的下标
        tracks: 全部动画轨道
        ids: 动画元素 id 到轨道下标的映射
    """

    root: ElementTree.Element
    elements: list[ElementTree.Element]
    tracks: list[Track]
    ids: dict[str, int]


def parse_timeline(body: str) -> Timeline:
    """把图标 body 解析成时间轴。

    动画元素会从文档树里摘出来放进 tracks，树里只留下被动画元素本身的基础属性。
    ``<use>`` 引用的 ``<symbol>`` 会被展开成内联的 ``<g>``，使每份引用都能独立求值。

    Args:
        body: 图标 body，即 SVG 根元素的内容片段

    Returns:
        解析好的 Timeline；body 里没有动画元素时 tracks 为空。

    起始时间引用其他动画的开始或结束，彼此可以形成环（a 结束后启动 b，b 结束后再启动 a），
    这是 SMIL 表达无限循环的常见写法，所以这里不检查环；求值时按时间顺序逐个展开实例。

    Raises:
        UnsupportedSmilError: 出现不支持的写法，或 body 不是合法的 XML。
    """
    root = _parse_xml(body)
    _expand_use(root)
    convert_clip_paths(root)
    _legacy_href(root)
    elements: list[ElementTree.Element] = []
    tracks: list[Track] = []
    ids: dict[str, int] = {}
    _collect(root, elements, tracks, ids)
    return Timeline(root=root, elements=elements, tracks=tracks, ids=ids)


_SUPPORTED: dict[str, bool] = {}


def is_supported_animation(body: str) -> bool:
    """body 是否含有本库能播放的 SMIL 动画。

    结果按 body 缓存。含有不支持的写法时为 False，此时图标显示为完成态静态图。

    Args:
        body: 图标 body

    Returns:
        含动画且全部写法受支持时为 True。
    """
    if not has_animation(body):
        return False
    cached = _SUPPORTED.get(body)
    if cached is None:
        try:
            cached = bool(parse_timeline(body).tracks)
        except UnsupportedSmilError:
            cached = False
        if len(_SUPPORTED) >= 512:
            _SUPPORTED.pop(next(iter(_SUPPORTED)))
        _SUPPORTED[body] = cached
    return cached


def has_animation(body: str) -> bool:
    """快速判断 body 里是否出现 SMIL 动画元素，不做完整解析。

    Args:
        body: 图标 body

    Returns:
        出现 animate、set、animateTransform 或 animateMotion 标签时为 True。
    """
    return bool(re.search(r"<(animate|animateTransform|animateMotion|set)[\s/>]", body))


def parse_time(text: str) -> float:
    """解析 SMIL 时钟值，支持 ``0.4s``、``.67s``、``-1.2s``、``200ms``、``3``。

    Args:
        text: 时钟值文本，两端空白会被忽略

    Returns:
        对应的秒数。

    Raises:
        UnsupportedSmilError: 不是支持的时钟值写法。
    """
    value = text.strip()
    match = re.fullmatch(r"([+-]?(?:\d+\.?\d*|\.\d+))(ms|s|min|h)?", value)
    if match is None:
        raise UnsupportedSmilError(f"unsupported time value: {text!r}")
    number = float(match.group(1))
    return number * {"ms": 0.001, "s": 1.0, "min": 60.0, "h": 3600.0, None: 1.0}[match.group(2)]


def _parse_xml(body: str) -> ElementTree.Element:
    """把 body 包进带命名空间的根元素后解析，保证标签名一致。

    Args:
        body: 图标 body

    Returns:
        包裹 body 的虚拟根元素（标签为 g）。

    Raises:
        UnsupportedSmilError: body 不是合法的 XML。
    """
    ElementTree.register_namespace("", SVG_NS)
    ElementTree.register_namespace("xlink", XLINK_NS)
    document = (
        f'<g xmlns="{SVG_NS}" xmlns:xlink="{XLINK_NS}">{body}</g>'
    )
    try:
        return ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        raise UnsupportedSmilError(f"invalid icon markup: {error}") from error


def local_name(tag: str) -> str:
    """去掉标签名里的命名空间前缀。

    Args:
        tag: ElementTree 标签名，形如 ``{命名空间}名称``

    Returns:
        不带命名空间的名称。
    """
    return tag.rsplit("}", 1)[-1]


def _expand_use(root: ElementTree.Element) -> None:
    """把 ``<use href="#id">`` 展开成被引用元素的内联副本。

    被引用的可以是 ``<symbol>``，也可以是 defs 里任何带 id 的元素（如 ``<rect>``）。
    展开后每份引用拥有独立的元素，动画元素的 id 会加上前缀避免冲突。
    被引用的原元素保留在 defs 里，Qt 不会直接渲染 defs 的内容。

    Args:
        root: 虚拟根元素，原地修改

    Raises:
        UnsupportedSmilError: 引用的目标不存在，或引用成环。
    """
    in_defs = _defs_members(root)
    symbols = {
        element.get("id"): element
        for element in root.iter()
        if element.get("id")
        and (local_name(element.tag) == "symbol" or id(element) in in_defs)
        and local_name(element.tag) not in _ANIMATION_TAGS
    }
    if not symbols or not any(local_name(e.tag) == "use" for e in root.iter()):
        return
    counter = [0]

    def expand(parent: ElementTree.Element, stack: tuple[str, ...]) -> None:
        """递归展开 parent 下的所有 use。

        Args:
            parent: 当前要处理的父元素，原地修改
            stack: 正在展开的引用链，用来发现循环引用
        """
        for index, child in enumerate(list(parent)):
            if local_name(child.tag) == "use":
                href = child.get("href") or child.get(f"{{{XLINK_NS}}}href") or ""
                target = symbols.get(href[1:]) if href.startswith("#") else None
                if target is None:
                    continue
                if href in stack:
                    raise UnsupportedSmilError(f"circular <use> reference: {href}")
                parent[index] = _inline_symbol(child, target, counter)
                expand(parent[index], stack + (href,))
            else:
                expand(child, stack)

    expand(root, ())


def _legacy_href(root: ElementTree.Element) -> None:
    """把渐变、滤镜等元素上不带前缀的 ``href`` 改写成 ``xlink:href``。

    SVG 2 允许直接写 ``href``，但 Qt 只认 ``xlink:href``，不认的话渐变会丢掉
    从被引用渐变继承来的 ``<stop>``，画成白色。静态图也有这个问题，与动画无关。

    Args:
        root: 虚拟根元素，原地修改
    """
    for element in root.iter():
        if "href" in element.attrib and local_name(element.tag) != "use":
            element.set(f"{{{XLINK_NS}}}href", element.attrib.pop("href"))


def convert_clip_paths(root: ElementTree.Element) -> None:
    """把 ``<clipPath>`` 转成等价的 ``<mask>``。

    Qt 的 SVG 渲染器不支持 ``clip-path``（静态图也一样，不是 SMIL 的问题），
    但完整支持 ``mask``。clipPath 的语义是"形状内可见、形状外不可见"，
    等价于一个白色形状的 mask：把 clipPath 里的形状填成白色，引用处的
    ``clip-path="url(#id)"`` 改成 ``mask="url(#id)"``。

    clipPath 内部形状的 transform、动画（已在解析阶段摘成轨道）都原样保留。
    已经带有 mask 属性的元素不处理（同时存在两种裁剪的情形生态里没有）。

    Args:
        root: 虚拟根元素，原地修改
    """
    clips = {
        element.get("id"): element
        for element in root.iter()
        if local_name(element.tag) == "clipPath" and element.get("id")
    }
    if not clips:
        return
    for clip in clips.values():
        clip.tag = f"{{{SVG_NS}}}mask"
        clip.attrib.pop("clipPathUnits", None)
        for shape in clip.iter():
            if shape is clip or local_name(shape.tag) in _ANIMATION_TAGS:
                continue
            shape.set("fill", "#fff")
            shape.attrib.pop("fill-opacity", None)
            shape.attrib.pop("stroke", None)
    for element in root.iter():
        value = element.attrib.pop("clip-path", None)
        if value is None:
            continue
        if "mask" in element.attrib:
            raise UnsupportedSmilError("element has both clip-path and mask")
        element.set("mask", value)


def _defs_members(root: ElementTree.Element) -> set[int]:
    """收集位于 ``<defs>`` 内部的所有元素。

    Args:
        root: 虚拟根元素

    Returns:
        这些元素的 ``id()`` 集合。
    """
    members: set[int] = set()
    for element in root.iter():
        if local_name(element.tag) == "defs":
            for inner in element.iter():
                if inner is not element:
                    members.add(id(inner))
    return members


def _inline_symbol(
    use: ElementTree.Element, symbol: ElementTree.Element, counter: list[int]
) -> ElementTree.Element:
    """生成一个 ``<use>`` 对应的内联元素。

    结构是两层 ``<g>``：外层带 use 自己的 transform、样式属性和写在 use 里面的动画元素；
    内层带 symbol 的 viewBox 映射和被引用的内容。这样外层的 additive 动画会叠加在
    use 的 transform 之后、viewBox 映射之前，和 SVG 规范里的求值顺序一致。

    按 SVG 规则，use 引用 symbol 时，symbol 的 viewBox 会被映射到
    use 的 width、height 区域。

    Args:
        use: 引用元素
        symbol: 被引用的元素（symbol，或 defs 里的其他元素）
        counter: 单元素列表，用来给每份展开生成不重复的 id 前缀

    Returns:
        内联后的外层 ``<g>`` 元素。
    """
    import copy

    counter[0] += 1
    prefix = f"u{counter[0]}_"
    outer = ElementTree.Element(f"{{{SVG_NS}}}g")
    inner = ElementTree.SubElement(outer, f"{{{SVG_NS}}}g")
    transform = use.get("transform", "")
    x = float(use.get("x", "0") or 0)
    y = float(use.get("y", "0") or 0)
    if x or y:
        transform = " ".join(part for part in (transform, f"translate({x:g} {y:g})") if part)
    if transform:
        outer.set("transform", transform)
    for key, value in use.attrib.items():
        if key in {"href", f"{{{XLINK_NS}}}href", "width", "height", "transform", "x", "y"}:
            continue
        outer.set(key, value)
    for child in list(use):
        if local_name(child.tag) in _ANIMATION_TAGS:
            clone = copy.deepcopy(child)
            _prefix_ids(clone, prefix)
            outer.insert(0, clone)
    view_box = symbol.get("viewBox") if local_name(symbol.tag) == "symbol" else None
    width = use.get("width")
    height = use.get("height")
    if view_box and width and height:
        left, top, vb_width, vb_height = (float(part) for part in view_box.replace(",", " ").split())
        scale = min(float(width) / vb_width, float(height) / vb_height)
        offset_x = (float(width) - vb_width * scale) / 2 - left * scale
        offset_y = (float(height) - vb_height * scale) / 2 - top * scale
        inner.set("transform", f"translate({offset_x:g} {offset_y:g}) scale({scale:g})")
    if local_name(symbol.tag) == "symbol":
        for child in symbol:
            clone = copy.deepcopy(child)
            _prefix_ids(clone, prefix)
            inner.append(clone)
    else:
        clone = copy.deepcopy(symbol)
        clone.attrib.pop("id", None)
        _prefix_ids(clone, prefix)
        inner.append(clone)
    return outer


def _prefix_ids(element: ElementTree.Element, prefix: str) -> None:
    """给元素树里所有 id 以及指向这些 id 的引用加前缀。

    Args:
        element: 要处理的元素，原地修改
        prefix: 要加的前缀
    """
    ids = {node.get("id") for node in element.iter() if node.get("id")}
    if not ids:
        return
    for node in element.iter():
        if node.get("id") in ids:
            node.set("id", prefix + node.get("id"))
        for key, value in list(node.attrib.items()):
            if key == "begin" and "." in value:
                node.set(key, re.sub(r"([\w-]+)\.(begin|end)", lambda m: (prefix + m.group(1) if m.group(1) in ids else m.group(1)) + "." + m.group(2), value))
            elif "url(#" in value:
                node.set(key, re.sub(r"url\(#([^)]+)\)", lambda m: "url(#" + (prefix + m.group(1) if m.group(1) in ids else m.group(1)) + ")", value))


def _collect(
    parent: ElementTree.Element,
    elements: list[ElementTree.Element],
    tracks: list[Track],
    ids: dict[str, int],
) -> None:
    """遍历元素树，摘出动画元素并生成轨道。

    Args:
        parent: 当前父元素，原地修改（动画子元素会被移除）
        elements: 按文档顺序登记的非动画元素
        tracks: 收集到的轨道
        ids: 动画元素 id 到轨道下标的映射
    """
    for child in list(parent):
        name = local_name(child.tag)
        if name in _ANIMATION_TAGS:
            parent.remove(child)
            try:
                track = _make_track(child, parent, elements, len(tracks))
            except InvalidSmilError:
                continue
            if track.id:
                if track.id in ids:
                    raise UnsupportedSmilError(f"duplicate animation id: {track.id}")
                ids[track.id] = len(tracks)
            tracks.append(track)
            continue
        if name in {"style", "script", "foreignObject"}:
            raise UnsupportedSmilError(f"unsupported element: <{name}>")
        elements.append(child)
        child.set("data-i", str(len(elements) - 1))
        _collect(child, elements, tracks, ids)


def _make_track(
    node: ElementTree.Element,
    parent: ElementTree.Element,
    elements: list[ElementTree.Element],
    index: int,
) -> Track:
    """把一个动画元素转换成轨道。

    Args:
        node: 动画元素
        parent: 动画元素的父元素，即被动画的目标
        elements: 已登记的元素列表，用于确定目标序号
        index: 该轨道在 tracks 里的下标，用于报错信息

    Returns:
        解析好的 Track。

    Raises:
        UnsupportedSmilError: 出现不支持的写法。
    """
    name = local_name(node.tag)
    attrib = {local_name(key): value for key, value in node.attrib.items()}
    for key in _UNSUPPORTED_ATTRIBUTES:
        if key in attrib:
            raise UnsupportedSmilError(f"unsupported attribute on <{name}>: {key}")
    if attrib.get("accumulate", "none") != "none":
        raise UnsupportedSmilError("accumulate other than 'none' is not supported")
    if attrib.get("href") or attrib.get("xlink:href"):
        raise UnsupportedSmilError("animation targets by href are not supported")
    if name == "animateMotion" and parent.find(f"{{{SVG_NS}}}mpath") is not None:
        raise UnsupportedSmilError("<mpath> is not supported")
    if name == "animateMotion" and "rotate" in attrib:
        raise UnsupportedSmilError("animateMotion rotate is not supported")

    target = _target_index(parent, elements)
    attribute = attrib.get("attributeName", "")
    kind = {"animate": "animate", "set": "set", "animateTransform": "transform", "animateMotion": "motion"}[name]
    transform_type = ""
    if kind == "transform":
        transform_type = attrib.get("type", "translate")
        if transform_type not in _TRANSFORM_TYPES:
            raise UnsupportedSmilError(f"unsupported transform type: {transform_type}")
        attribute = "transform"
    elif kind == "motion":
        attribute = "motion"
    elif not attribute:
        raise UnsupportedSmilError(f"<{name}> without attributeName")

    duration = 0.0
    if kind != "set":
        duration = _duration(attrib.get("dur"), kind)
    begins = _parse_begins(attrib.get("begin", "0s"))
    calc_mode = attrib.get("calcMode", "paced" if kind == "motion" else "linear")
    if kind == "motion":
        calc_mode = "linear" if calc_mode in {"paced", "linear"} else calc_mode
    if calc_mode not in {"linear", "discrete", "spline"}:
        raise UnsupportedSmilError(f"unsupported calcMode: {calc_mode}")
    values, key_times = _values_and_times(attrib, kind, calc_mode == "discrete")
    key_splines = _parse_splines(attrib.get("keySplines"), len(values) - 1) if calc_mode == "spline" else []

    repeat = 1.0
    repeat_count = attrib.get("repeatCount")
    if repeat_count == "indefinite":
        repeat = math.inf
    elif repeat_count is not None:
        try:
            repeat = float(repeat_count)
        except ValueError as error:
            raise UnsupportedSmilError(f"bad repeatCount: {repeat_count!r}") from error
    additive = attrib.get("additive", "replace")
    if additive not in {"sum", "replace"}:
        raise UnsupportedSmilError(f"unsupported additive: {additive}")
    fill = attrib.get("fill", "remove")
    if fill not in {"freeze", "remove"}:
        raise UnsupportedSmilError(f"unsupported fill: {fill}")
    restart = attrib.get("restart", "always")
    if restart not in {"always", "whenNotActive", "never"}:
        raise UnsupportedSmilError(f"unsupported restart: {restart}")
    return Track(
        kind=kind,
        target=target,
        attribute=attribute,
        duration=duration,
        values=values,
        key_times=key_times,
        begins=begins,
        transform_type=transform_type,
        id=attrib.get("id"),
        calc_mode=calc_mode,
        key_splines=key_splines,
        repeat=repeat,
        freeze=fill == "freeze",
        additive=additive == "sum" or kind == "transform" and additive == "sum",
        restart=restart == "always",
        motion_path=attrib.get("path", ""),
    )


def _target_index(parent: ElementTree.Element, elements: list[ElementTree.Element]) -> int:
    """返回动画目标元素在 elements 里的序号。

    Args:
        parent: 动画元素的父元素
        elements: 已登记的元素列表

    Returns:
        目标序号；父元素是虚拟根时为 -1（动画直接挂在顶层，不支持）。

    Raises:
        UnsupportedSmilError: 动画元素没有可作为目标的父元素。
    """
    marker = parent.get("data-i")
    if marker is None:
        raise UnsupportedSmilError("animation element without a target element")
    return int(marker)


def _duration(text: str | None, kind: str) -> float:
    """解析 dur。

    Args:
        text: dur 属性值
        kind: 轨道类型，用于报错信息

    Returns:
        时长，秒。

    Raises:
        UnsupportedSmilError: 缺失、为 indefinite 或不是正数。
    """
    if text is None or text.strip() in {"indefinite", "media"}:
        raise UnsupportedSmilError(f"<{kind}> without a finite dur")
    value = parse_time(text)
    if value <= 0:
        raise UnsupportedSmilError(f"dur must be positive: {text!r}")
    return value


def _parse_begins(text: str) -> list[float | BeginRef]:
    """解析 begin 的分号列表。

    Args:
        text: begin 属性值，如 ``0s; x1.end+1s``

    Returns:
        起始时间列表；固定秒数为 float，引用其他动画为 BeginRef。

    Raises:
        UnsupportedSmilError: 出现事件触发、indefinite 或其他不支持的写法。
    """
    begins: list[float | BeginRef] = []
    for part in text.split(";"):
        item = part.strip()
        if not item:
            continue
        match = re.fullmatch(r"([\w-]+)\.(begin|end)\s*(?:([+-])\s*([\d.]+(?:ms|s|min|h)?))?", item)
        if match:
            offset = parse_time(match.group(4)) if match.group(4) else 0.0
            if match.group(3) == "-":
                offset = -offset
            begins.append(BeginRef(match.group(1), match.group(2), offset))
            continue
        if item == "indefinite":
            raise UnsupportedSmilError("begin='indefinite' needs scripting")
        begins.append(parse_time(item))
    return begins or [0.0]


def _values_and_times(
    attrib: dict[str, str], kind: str, discrete: bool = False
) -> tuple[list[str], list[float]]:
    """从 values / from / to 取出关键帧取值，并算出 keyTimes。

    Args:
        attrib: 动画元素的属性（已去命名空间）
        kind: 轨道类型
        discrete: calcMode 是否为 discrete；离散模式没有 keyTimes 时按 i/n 均分，
            即每个取值各占 1/n 时长，而连续模式按 i/(n-1) 均分

    Returns:
        (取值列表, 关键帧时刻列表)，两者等长。
        ``to`` 单独出现时取值为 ["", to]，空串表示"基础值"，求值时再替换。

    Raises:
        UnsupportedSmilError: keyTimes 不合法，或缺少取值。
    """
    if kind == "motion":
        return [], [0.0, 1.0]
    if "values" in attrib:
        values = [part.strip() for part in attrib["values"].split(";")]
        while values and values[-1] == "":
            values.pop()
        if len(values) < 1 or any(value == "" for value in values):
            raise UnsupportedSmilError("empty entry in values")
    elif "to" in attrib:
        start = attrib.get("from", "")
        values = [start.strip(), attrib["to"].strip()]
        if kind == "set":
            values = [attrib["to"].strip()]
    else:
        raise UnsupportedSmilError("animation without values or to")
    if "keyTimes" in attrib:
        try:
            times = [float(part) for part in attrib["keyTimes"].split(";") if part.strip()]
        except ValueError as error:
            raise UnsupportedSmilError("bad keyTimes") from error
        if len(times) != len(values):
            raise InvalidSmilError("keyTimes and values differ in length")
        if times and (times[0] != 0.0 or any(b < a for a, b in zip(times, times[1:]))):
            raise InvalidSmilError("keyTimes must start at 0 and not decrease")
    elif len(values) == 1:
        times = [0.0]
    elif discrete:
        times = [index / len(values) for index in range(len(values))]
    else:
        times = [index / (len(values) - 1) for index in range(len(values))]
    return values, times


def _parse_splines(text: str | None, count: int) -> list[tuple[float, float, float, float]]:
    """解析 keySplines。

    Args:
        text: keySplines 属性值；每段四个数，段间用分号分隔
        count: 需要的区间数

    Returns:
        每个区间的 (x1, y1, x2, y2)。

    Raises:
        UnsupportedSmilError: 缺失、个数不对或数值不合法。
    """
    if text is None:
        raise UnsupportedSmilError("calcMode='spline' without keySplines")
    splines: list[tuple[float, float, float, float]] = []
    for part in text.split(";"):
        if not part.strip():
            continue
        numbers = [float(item) for item in re.split(r"[\s,]+", part.strip()) if item]
        if len(numbers) != 4 or not (0.0 <= numbers[0] <= 1.0 and 0.0 <= numbers[2] <= 1.0):
            raise UnsupportedSmilError(f"bad keySplines entry: {part!r}")
        splines.append((numbers[0], numbers[1], numbers[2], numbers[3]))
    if len(splines) != count:
        raise UnsupportedSmilError("keySplines count does not match values")
    return splines
