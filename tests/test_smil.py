"""SMIL 解析与求值测试（不依赖 Qt）。

只用手写的小图标，覆盖每一种被支持的写法，并断言具体数值。
"""

from __future__ import annotations

import math
import re

import pytest

from pyside_iconify.core.smil import (
    BeginRef,
    UnsupportedSmilError,
    has_animation,
    is_supported_animation,
    parse_time,
    parse_timeline,
)
from pyside_iconify.core.smil_eval import Schedule, bezier, evaluate


def attrs(body: str, tag: str = "path") -> dict[str, str]:
    """取求值结果里第一个指定标签的属性。"""
    match = re.search(rf"<{tag}\b([^>]*)>", body)
    assert match is not None, body
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', match.group(1)))


def at(body: str, time: float, tag: str = "path") -> dict[str, str]:
    timeline = parse_timeline(body)
    return attrs(evaluate(timeline, Schedule(timeline), time), tag)


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("0.4s", 0.4), (".67s", 0.67), ("-1.2s", -1.2), ("200ms", 0.2), ("3", 3.0), ("1min", 60.0)],
)
def test_parse_time(text: str, seconds: float) -> None:
    assert parse_time(text) == pytest.approx(seconds)


def test_parse_time_rejects_garbage() -> None:
    with pytest.raises(UnsupportedSmilError):
        parse_time("soon")


def test_line_drawing_with_to_freeze() -> None:
    body = (
        '<path stroke-dasharray="18" stroke-dashoffset="18" d="M0 0h18">'
        '<animate fill="freeze" attributeName="stroke-dashoffset" begin="0.4s" dur="0.4s" to="0"/></path>'
    )
    assert float(at(body, 0.2)["stroke-dashoffset"]) == 18  # 未开始：保持基础值
    assert float(at(body, 0.6)["stroke-dashoffset"]) == pytest.approx(9)
    assert float(at(body, 5)["stroke-dashoffset"]) == 0  # freeze：停在最后一个值


def test_without_freeze_returns_to_base_value() -> None:
    body = (
        '<circle r="2" opacity="1"><animate attributeName="opacity" begin="1s" dur="1s" values="0;1"/></circle>'
    )
    assert float(at(body, 1.5, "circle")["opacity"]) == pytest.approx(0.5)
    assert float(at(body, 3, "circle")["opacity"]) == 1  # 结束且不 freeze：回到基础值


def test_key_times_and_indefinite_repeat() -> None:
    body = (
        '<path d="M0 0" stroke-width="2"><animate attributeName="stroke-width" dur="3s" '
        'keyTimes="0;0.1;0.2;0.3;1" repeatCount="indefinite" values="2;3;3;2;2"/></path>'
    )
    assert float(at(body, 0.15)["stroke-width"]) == pytest.approx(2.5)
    assert float(at(body, 0.3)["stroke-width"]) == pytest.approx(3)
    assert float(at(body, 3.3)["stroke-width"]) == pytest.approx(3)  # 第二圈
    assert Schedule(parse_timeline(body)).period == pytest.approx(3.0)


def test_spline_easing_matches_css_bezier() -> None:
    body = (
        '<circle r="1"><animate attributeName="r" dur="1s" calcMode="spline" keyTimes="0;1" '
        'keySplines=".42 0 .58 1" values="1;3"/></circle>'
    )
    eased = float(at(body, 0.25, "circle")["r"])
    assert eased == pytest.approx(1 + 2 * bezier(0.42, 0, 0.58, 1, 0.25))
    assert 1 < eased < 1.5  # ease-in-out 在前 25% 比线性慢
    assert float(at(body, 0.5, "circle")["r"]) == pytest.approx(2)


def test_discrete_holds_each_value() -> None:
    body = (
        '<path d="M0" opacity="0"><animate attributeName="opacity" calcMode="discrete" dur="1s" '
        'values="0;1;0" fill="freeze"/></path>'
    )
    assert float(at(body, 0.2)["opacity"]) == 0
    assert float(at(body, 0.5)["opacity"]) == 1  # 每个取值各占 1/3 时长
    assert float(at(body, 0.8)["opacity"]) == 0


def test_begin_reference_chain_and_loop() -> None:
    # x 先播，播完过 1 秒轮到 y，y 播完过 1 秒 x 再来：这是 SMIL 表达无限循环的写法
    body = (
        '<g><circle r="1"><animate id="x" attributeName="r" begin="0;y.end+1s" dur="1s" values="1;2"/></circle>'
        '<circle r="1"><animate id="y" attributeName="r" begin="x.end+1s" dur="1s" values="5;6"/></circle></g>'
    )
    timeline = parse_timeline(body)
    schedule = Schedule(timeline)
    assert [round(i.start, 3) for i in schedule.instances[0][:3]] == [0.0, 4.0, 8.0]
    assert [round(i.start, 3) for i in schedule.instances[1][:3]] == [2.0, 6.0, 10.0]
    assert schedule.period == pytest.approx(4.0)
    rs = lambda t: re.findall(r'r="([\d.]+)"', evaluate(timeline, schedule, t))
    assert rs(0.5) == ["1.5", "1"] and rs(2.5) == ["1", "5.5"] and rs(4.5) == ["1.5", "1"]


def test_dangling_reference_never_fires() -> None:
    body = (
        '<path d="M0" opacity="0"><animate attributeName="opacity" begin="0.5s; nowhere.end+1s" '
        'dur="1s" values="0;1;0"/></path>'
    )
    timeline = parse_timeline(body)
    assert len(Schedule(timeline).instances[0]) == 1  # 引用不存在的 id：该时间点永远不触发
    assert float(at(body, 1.0)["opacity"]) == pytest.approx(1.0)
    assert float(at(body, 4.0)["opacity"]) == 0


def test_additive_sum_keeps_base_transform() -> None:
    summed = (
        '<path d="M0 0" transform="translate(5 5)"><animateTransform additive="sum" attributeName="transform" '
        'dur="2s" repeatCount="indefinite" type="rotate" values="0 12 12;90 12 12"/></path>'
    )
    replaced = summed.replace(' additive="sum"', "")
    assert at(summed, 1)["transform"] == "translate(5 5) rotate(45 12 12)"
    assert at(replaced, 1)["transform"] == "rotate(45 12 12)"


def test_later_start_wins_on_the_same_attribute() -> None:
    body = (
        '<circle cx="0" r="1"><animate attributeName="cx" begin="0s" dur="4s" values="0;100" fill="freeze"/>'
        '<animate attributeName="cx" begin="2s" dur="1s" values="500;600" fill="freeze"/></circle>'
    )
    assert float(at(body, 1, "circle")["cx"]) == pytest.approx(25)
    assert float(at(body, 2.5, "circle")["cx"]) == pytest.approx(550)  # 晚开始的优先


def test_path_morph_and_structure_mismatch() -> None:
    body = (
        '<path d="M4 9l0 0l0 0Z"><animate fill="freeze" attributeName="d" begin="0.6s" dur="0.2s" '
        'values="M4 9l0 0l0 0Z;M5.63 7.38l-2.13 -2.13l0 4.25Z"/></path>'
    )
    middle = at(body, 0.7)["d"].split()
    assert float(middle[1]) == pytest.approx(4.815) and float(middle[2]) == pytest.approx(8.19)
    bad = body.replace("l0 4.25Z", "Z")
    with pytest.raises(UnsupportedSmilError):
        at(bad, 0.7)


def test_set_switches_at_begin() -> None:
    body = '<path d="M0 0" opacity="0"><set attributeName="opacity" begin="1s" to="1"/></path>'
    assert float(at(body, 0.5)["opacity"]) == 0 and float(at(body, 1)["opacity"]) == 1


def test_missing_attribute_uses_svg_default() -> None:
    body = '<circle cx="5"><animate fill="freeze" attributeName="r" begin="0s" dur="1s" to="4"/></circle>'
    assert float(at(body, 0.5, "circle")["r"]) == pytest.approx(2)  # 没写 r：从默认值 0 长出来


def test_inherited_base_value_comes_from_ancestor() -> None:
    body = (
        '<g fill-opacity="0.5"><path d="M0"><animate fill="freeze" attributeName="fill-opacity" dur="1s" to="1"/>'
        "</path></g>"
    )
    assert float(at(body, 0.5)["fill-opacity"]) == pytest.approx(0.75)


def test_motion_follows_curve_by_arc_length() -> None:
    body = '<g><circle r="1"><animateMotion dur="2s" path="M0 0H10V10" fill="freeze"/></circle></g>'
    assert at(body, 0, "circle")["transform"] == "translate(0 0)"
    assert at(body, 1, "circle")["transform"] == "translate(10 0)"  # 总长 20，一半处是转角
    assert at(body, 1.5, "circle")["transform"] == "translate(10 5)"


def test_use_expansion_keeps_independent_animation_per_copy() -> None:
    body = (
        '<defs><rect id="bar" width="10" height="4"><animate fill="freeze" attributeName="width" dur="1s" '
        'from="0" to="10"/></rect></defs><use href="#bar" y="0"><animate attributeName="opacity" begin="0.5s" '
        'dur="1s" values="0;1" fill="freeze"/></use><use href="#bar" y="8"/>'
    )
    timeline = parse_timeline(body)
    # defs 里的原件、两份内联各有一条宽度动画，加上第一个 use 自己的一条透明度动画
    assert len(timeline.tracks) == 4
    out = evaluate(timeline, Schedule(timeline), 0.5)
    assert "<use" not in out
    assert out.count("<rect") == 3  # defs 里的原件（不渲染）+ 两份内联
    widths = re.findall(r'<rect[^>]*width="([\d.]+)"', out)
    assert widths == ["5", "5", "5"]  # 每份各自播放，同一时刻进度相同
    first_copy = re.search(r'<g opacity="([\d.]+)"', out)
    assert first_copy is not None and float(first_copy.group(1)) == pytest.approx(0.0)  # use 自己的动画在 0.5s 刚开始


def test_clip_path_becomes_mask() -> None:
    body = (
        '<defs><clipPath id="c"><path d="M0 0H10V10H0Z"/></clipPath></defs>'
        '<rect width="20" height="10" clip-path="url(#c)"><animate attributeName="opacity" dur="1s" to="1"/></rect>'
    )
    out = evaluate(parse_timeline(body), Schedule(parse_timeline(body)), 0)
    assert "clipPath" not in out and "clip-path" not in out
    assert '<mask id="c">' in out and 'mask="url(#c)"' in out


def test_transform_origin_is_folded_into_transform() -> None:
    body = (
        '<path d="M0" transform="scale(1 0)" transform-origin="4px 6px">'
        '<animateTransform attributeName="transform" type="scale" dur="1s" values="1 0;1 1"/></path>'
    )
    out = at(body, 0.5)
    assert "transform-origin" not in out
    assert out["transform"] == "translate(4 6) scale(1 0.5) translate(-4 -6)"


def test_invalid_key_times_only_drops_that_animation() -> None:
    body = (
        '<path d="M0" opacity="0"><animate attributeName="opacity" dur="1s" keyTimes="0;0.8;0.3;1" '
        'values="0;1;0;1"/><animate fill="freeze" attributeName="fill-opacity" dur="1s" to="1"/></path>'
    )
    timeline = parse_timeline(body)
    assert len(timeline.tracks) == 1  # 按规范，无效的动画元素不起作用，其余照常


@pytest.mark.parametrize(
    "fragment",
    [
        '<animate attributeName="opacity" dur="1s" to="1" end="2s"/>',
        '<animate attributeName="opacity" dur="1s" to="1" repeatDur="5s"/>',
        '<animate attributeName="opacity" begin="click" dur="1s" to="1"/>',
        '<animate attributeName="opacity" begin="indefinite" dur="1s" to="1"/>',
        '<animate attributeName="opacity" dur="1s" to="1" accumulate="sum"/>',
        '<animateMotion dur="1s" path="M0 0L1 1" keyPoints="0;1"/>',
        '<animate attributeName="opacity" dur="indefinite" to="1"/>',
        '<animate attributeName="opacity" dur="1s" calcMode="paced" to="1"/>',
    ],
)
def test_unsupported_writing_is_rejected_not_half_played(fragment: str) -> None:
    assert not is_supported_animation(f'<path d="M0">{fragment}</path>')
    with pytest.raises(UnsupportedSmilError):
        parse_timeline(f'<path d="M0">{fragment}</path>')


def test_css_and_script_are_not_smil() -> None:
    assert not has_animation('<path style="animation: spin 1s infinite" d="M0"/>')
    assert not is_supported_animation('<style>@keyframes a{}</style><path d="M0"/>')


def test_period_is_common_multiple_of_loops() -> None:
    body = (
        '<g><circle r="1"><animate attributeName="r" dur="1.5s" repeatCount="indefinite" values="1;2;1"/></circle>'
        '<circle r="1"><animate attributeName="r" dur="2s" repeatCount="indefinite" values="1;2;1"/></circle></g>'
    )
    assert Schedule(parse_timeline(body)).period == pytest.approx(6.0)


def test_finished_state_is_end_of_first_pass() -> None:
    body = (
        '<path d="M0" stroke-dashoffset="9" stroke-dasharray="9"><animate fill="freeze" '
        'attributeName="stroke-dashoffset" begin="0.2s" dur="0.4s" to="0"/></path>'
    )
    timeline = parse_timeline(body)
    schedule = Schedule(timeline)
    assert schedule.final == pytest.approx(0.6)
    assert float(attrs(evaluate(timeline, schedule, schedule.final))["stroke-dashoffset"]) == 0


def test_begin_references_are_parsed_with_offsets() -> None:
    body = (
        '<path d="M0"><animate id="a" attributeName="opacity" dur="1s" to="1"/>'
        '<animate attributeName="opacity" begin="a.end-0.25s; a.begin+2s" dur="1s" to="1"/></path>'
    )
    begins = parse_timeline(body).tracks[1].begins
    assert begins == [BeginRef("a", "end", -0.25), BeginRef("a", "begin", 2.0)]
    assert all(math.isfinite(i.start) for i in Schedule(parse_timeline(body)).instances[1])
