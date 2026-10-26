"""IconWidget、QSS、状态和动画测试。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QStyleOption, QWidget

from pyside_iconify import IconWidget, add_collection, add_icon, mark_pending
from tests.helpers import assert_color, show_widget, widget_color


@pytest.fixture
def widget_collection() -> None:
    add_collection(
        {
            "prefix": "widget",
            "width": 24,
            "height": 24,
            "icons": {
                "square": {
                    "body": '<rect width="24" height="24" fill="currentColor"/>'
                },
                "half": {"body": '<rect width="12" height="24" fill="currentColor"/>'},
                "spinner": {
                    "body": '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="36 15"/>'
                },
                "fallback": {"body": '<rect width="24" height="24" fill="#00ff00"/>'},
            },
        }
    )


@pytest.mark.parametrize("value", [18, "18px", (18, 18)])
def test_size_forms(value: object, widget_collection: None) -> None:
    assert IconWidget("widget:square", size=value).sizeHint().width() == 18


def test_em_follows_font(widget_collection: None) -> None:
    widget = IconWidget("widget:square", size="2em")
    font = QFont(widget.font())
    font.setPixelSize(10)
    widget.setFont(font)
    first = widget.sizeHint().height()
    font.setPixelSize(20)
    widget.setFont(font)
    assert widget.sizeHint().height() > first


def test_wide_widget_does_not_stretch_icon(
    qtbot: object, widget_collection: None
) -> None:
    widget = show_widget(
        qtbot, IconWidget("widget:square", size=24, color="#ff0000"), 160, 40
    )
    image = widget.grab().toImage()
    pixels = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).name() == "#ff0000"
    ]
    xs = [point[0] for point in pixels]
    ys = [point[1] for point in pixels]
    assert abs((max(xs) - min(xs)) - (max(ys) - min(ys))) <= 2


def test_squeezed_widget_keeps_placeholder_square(qtbot: object) -> None:
    """控件被压成扁矩形时，占位图按逻辑尺寸居中绘制，不被拉伸。"""
    widget = IconWidget("widget:no-such-icon", size=40)
    qtbot.addWidget(widget)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    widget.resize(120, 30)
    widget.show()
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()
    image = widget.grab().toImage()
    points = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        # 排除 offscreen 平台不透明的窗口背景色
        if image.pixelColor(x, y).alpha() > 60
        and image.pixelColor(x, y) != QColor("#efefef")
    ]
    assert points, "placeholder did not render"
    xs = [point[0] for point in points]
    ink_width = max(xs) - min(xs)
    # 不横向拉伸：墨迹是占位图自身宽度（40 的画布含内边距约 33），
    # 而不是控件宽 120。
    assert ink_width <= 45, ink_width
    # 水平居中。
    assert abs((min(xs) + max(xs)) / 2 - image.width() / 2) <= 3


def test_qss_color_background_and_explicit_color_priority(
    qtbot: object, widget_collection: None
) -> None:
    host = QWidget()
    host.resize(200, 100)
    host.setStyleSheet(
        'IconWidget[qss~="blue"] { color: #0000ff; background: #111111; }'
    )
    qtbot.addWidget(host)
    host.move(400, 400)
    host.show()
    qss = IconWidget("widget:half", size=24, qss="blue", parent=host)
    qss.show()
    explicit = IconWidget(
        "widget:square", size=24, color="#ff0000", qss="blue", parent=host
    )
    explicit.move(30, 0)
    explicit.show()
    assert_color(widget_color(qss, 6, 12), "#0000ff")
    assert_color(widget_color(qss, 20, 12), "#111111")
    assert_color(widget_color(explicit, 12, 12), "#ff0000")


def test_theme_and_light_dark_priority(
    qtbot: object, qapp: object, widget_collection: None
) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    host.move(400, 400)
    host.show()
    theme = IconWidget("widget:square", size=24, parent=host)
    override = IconWidget(
        "widget:square",
        size=24,
        color="#ff0000",
        color_light_theme="#8250df",
        color_dark_theme="#1a7f37",
        parent=host,
    )
    override.move(30, 0)
    theme.show()
    override.show()
    light = QPalette()
    light.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    light.setColor(QPalette.ColorRole.WindowText, QColor("#101010"))
    qapp.setPalette(light)
    assert_color(widget_color(theme, 12, 12), "#101010")
    assert_color(widget_color(override, 12, 12), "#8250df")
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Window, QColor("#101010"))
    dark.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
    qapp.setPalette(dark)
    assert_color(widget_color(theme, 12, 12), "#f0f0f0")
    assert_color(widget_color(override, 12, 12), "#1a7f37")


def test_missing_fallback_placeholder_and_blank(
    qtbot: object, widget_collection: None
) -> None:
    fallback = show_widget(
        qtbot, IconWidget("widget:missing", size=24, fallback="widget:fallback")
    )
    assert_color(widget_color(fallback, 12, 12), "#00ff00")
    placeholder = show_widget(
        qtbot, IconWidget("widget:missing", size=24, fallback="widget:also-missing")
    )
    assert any(
        placeholder.grab().toImage().pixelColor(x, y).alpha()
        for x in range(24)
        for y in range(24)
    )
    blank = show_widget(qtbot, IconWidget("widget:missing", size=24, fallback=None))
    option = QStyleOption()
    option.initFrom(blank)
    image = blank._pixmap().toImage()
    assert not any(image.pixelColor(x, y).alpha() for x in range(24) for y in range(24))


def test_pending_data_refreshes_and_emits_loaded(
    qtbot: object, widget_collection: None
) -> None:
    mark_pending("widget:later")
    widget = show_widget(qtbot, IconWidget("widget:later", size=24, color="#00ff00"))
    assert widget._status == "loading"
    with qtbot.waitSignal(widget.loaded, timeout=1000):
        add_icon(
            "widget:later",
            '<rect width="24" height="24" fill="currentColor"/>',
            replace=True,
        )
    assert_color(widget_color(widget, 12, 12), "#00ff00")


def test_spin_uses_stable_scale(qtbot: object, widget_collection: None) -> None:
    spinner = show_widget(
        qtbot, IconWidget("widget:spinner", size=48, spin=True, spin_period=0.3), 48, 48
    )
    areas: list[int] = []
    for _ in range(4):
        qtbot.wait(45)
        image = spinner.grab().toImage()
        pixels = [
            (x, y)
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y).alpha() > 40
        ]
        xs = [point[0] for point in pixels]
        ys = [point[1] for point in pixels]
        areas.append((max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1))
    assert max(areas) - min(areas) <= 300


def _opaque_pixels(widget_icon: object, **options: object) -> int:
    """统计无背景位图中不透明像素的数量。"""
    from pyside_iconify import get_pixmap

    image = get_pixmap(widget_icon, size=48, color="#ff0000", **options).toImage()
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 128
    )


def test_rotate_overflow_keeps_original_size(widget_collection: None) -> None:
    shrunk = _opaque_pixels("widget:square", rotate=45)
    kept = _opaque_pixels("widget:square", rotate=45, rotate_overflow=True)
    assert kept > shrunk * 1.4
    assert _opaque_pixels("widget:square", rotate=90, rotate_overflow=True) == 48 * 48


def test_animation_validation(widget_collection: None) -> None:
    from pyside_iconify import InvalidAnimationError

    for options in (
        {"animation": "wobble"},
        {"spin": True, "animation": "pulse"},
        {"animation": "pulse", "animation_period": 0},
        {"animation": "pulse", "animation_period": True},
    ):
        with pytest.raises(InvalidAnimationError):
            IconWidget("widget:square", **options)


def test_spin_is_alias_of_animation(widget_collection: None) -> None:
    legacy = IconWidget("widget:square", spin=True, spin_period=0.5)
    assert legacy._options.animation == "spin"
    assert legacy._options.animation_period == 0.5
    named = IconWidget("widget:square", animation="spin", animation_period=0.5)
    assert named._options.animation_period == 0.5
    assert IconWidget("widget:square", animation="pulse")._options.animation_period == 1.0
    assert (
        IconWidget("widget:square", animation="breathe")._options.animation_period == 2.0
    )
    assert IconWidget("widget:square", animation="ping")._options.animation_period == 1.0
    assert IconWidget("widget:square", animation="bounce")._options.animation_period == 1.0


def test_set_animation_switches_and_stops(widget_collection: None) -> None:
    widget = IconWidget("widget:square", animation="pulse")
    widget.setSpin(False)
    assert widget._options.animation == "pulse"
    widget.setAnimation("spin", 0.4)
    assert widget._options.animation_period == 0.4
    widget.setAnimation(None)
    assert widget._options.animation is None


def test_pulse_changes_size_and_breathe_changes_opacity(
    qtbot: object, widget_collection: None
) -> None:
    from pyside_iconify.rendering.motion import frame_at

    scales = {frame_at("pulse", step / 20, 1.0).scale for step in range(20)}
    opacities = {frame_at("breathe", step / 20, 1.0).opacity for step in range(20)}
    assert min(scales) < 0.8 and max(scales) == 1.0
    assert min(opacities) < 0.4 and max(opacities) == 1.0
    assert frame_at("pulse", 0.0, 1.0).rotate == 0.0
    assert frame_at("breathe", 0.0, 1.0).scale == 1.0

    widget = show_widget(
        qtbot,
        IconWidget("widget:square", size=48, color="#ff0000", animation="pulse", animation_period=0.4),
        48,
        48,
    )
    areas = set()
    for _ in range(6):
        qtbot.wait(70)
        image = widget.grab().toImage()
        areas.add(
            sum(
                1
                for y in range(image.height())
                for x in range(image.width())
                if image.pixelColor(x, y).red() > 200 and image.pixelColor(x, y).green() < 80
            )
        )
    assert len(areas) > 1


def test_animation_depth(widget_collection: None) -> None:
    from pyside_iconify import InvalidAnimationError
    from pyside_iconify.rendering.motion import frame_at

    # 默认幅度与显式幅度
    assert min(frame_at("pulse", t / 20, 1.0).scale for t in range(20)) < 0.8
    deep = min(frame_at("pulse", t / 20, 1.0, 0.5).scale for t in range(20))
    flat = min(frame_at("pulse", t / 20, 1.0, 0.0).scale for t in range(20))
    assert deep < 0.6 and flat == 1.0
    assert min(frame_at("breathe", t / 20, 1.0, 0.2).opacity for t in range(20)) > 0.75
    assert min(frame_at("pulse", t / 20, 1.0, 1.0).scale for t in range(20)) > 0.0

    widget = IconWidget("widget:square", animation="pulse", animation_depth=0.4)
    assert widget._options.animation_depth == 0.4
    assert IconWidget("widget:square", animation="breathe")._options.animation_depth == 0.7
    assert IconWidget("widget:square", animation="spin")._options.animation_depth is None
    assert IconWidget("widget:square", animation="ping")._options.animation_depth == 1.0
    assert IconWidget("widget:square", animation="bounce")._options.animation_depth == 0.25

    for options in (
        {"animation": "spin", "animation_depth": 0.5},
        {"animation_depth": 0.5},
        {"animation": "pulse", "animation_depth": 1.5},
        {"animation": "pulse", "animation_depth": True},
    ):
        with pytest.raises(InvalidAnimationError):
            IconWidget("widget:square", **options)

    widget.setAnimation("spin")
    assert widget._options.animation_depth is None
    widget.setAnimation("breathe", 2.0, 0.3)
    assert widget._options.animation_depth == 0.3
    widget.setColor("#ff0000")
    assert widget._options.animation_depth == 0.3


@pytest.mark.parametrize("period", [0.4, 1.0, 4.0])
def test_pulse_changes_every_refresh_regardless_of_period(period: float) -> None:
    from pyside_iconify.rendering.motion import frame_at

    # 以 60 帧/秒采样，每帧画面都应不同；周期越长不能退化成一格一格地跳。
    values = [frame_at("pulse", i / 60, period).scale for i in range(60)]
    changes = sum(1 for a, b in zip(values, values[1:]) if abs(a - b) > 1e-9)
    expected = 59 if period <= 1.0 else int(59 * 0.9)
    assert changes >= expected


def test_ping_ripple_expands_and_fades() -> None:
    from pyside_iconify.rendering.motion import frame_at

    # 默认幅度 1：本体缩到一半，水波从本体大小扩散到铺满控件
    start = frame_at("ping", 0.0, 1.0)
    assert start.scale == pytest.approx(0.5)
    assert start.ghost_scale == pytest.approx(0.5)
    assert start.ghost_opacity == pytest.approx(1.0)

    middle = frame_at("ping", 0.4, 1.0)
    assert 0.5 < middle.ghost_scale < 1.0
    assert 0.0 < middle.ghost_opacity < 1.0

    # 周期的后 25% 水波不可见，只剩本体
    resting = frame_at("ping", 0.9, 1.0)
    assert resting.ghost_opacity == 0.0 and resting.ghost_scale == 0.0
    assert resting.scale == pytest.approx(0.5)

    scales = [frame_at("ping", t / 100, 1.0).ghost_scale for t in range(100)]
    assert max(scales) <= 1.0 + 1e-9
    opacities = [frame_at("ping", t / 100, 1.0, 0.5).ghost_opacity for t in range(100)]
    assert opacities == sorted(opacities, reverse=True)


def test_bounce_falls_then_rises_inside_the_widget() -> None:
    from pyside_iconify.rendering.motion import frame_at

    frames = [frame_at("bounce", t / 100, 1.0) for t in range(100)]
    base = 1 / 1.25
    margin = (1 - base) / 2
    assert all(frame.scale == pytest.approx(base) for frame in frames)

    # 周期起点在最高处，周期中点落地；位移始终让图标完整落在控件内
    offsets = [frame.offset_y for frame in frames]
    assert offsets[0] == pytest.approx(-margin)
    assert 45 <= offsets.index(max(offsets)) <= 55
    assert max(offsets) == pytest.approx(margin)
    assert all(abs(offset) + base / 2 <= 0.5 + 1e-9 for offset in offsets)

    # 幅度为 0 时不跳，本体也不缩小
    still = frame_at("bounce", 0.3, 1.0, 0.0)
    assert still.scale == 1.0 and still.offset_y == 0.0


@pytest.mark.parametrize("kind", ["ping", "bounce"])
@pytest.mark.parametrize("period", [0.4, 4.0])
def test_ping_and_bounce_change_every_refresh(kind: str, period: float) -> None:
    from pyside_iconify.rendering.motion import frame_at

    # 以 60 帧/秒采样周期的前 70%（ping 的水波在此区间内可见），周期长也要逐帧变化
    count = int(0.7 * period * 60)
    frames = [frame_at(kind, i / 60, period).shape for i in range(count)]
    changes = sum(1 for a, b in zip(frames, frames[1:]) if a != b)
    assert changes >= count - 2


def test_bounce_widget_moves_without_clipping(qtbot: object, widget_collection: None) -> None:
    widget = show_widget(
        qtbot,
        IconWidget(
            "widget:square", size=48, color="#ff0000", animation="bounce", animation_period=0.4
        ),
        48,
        48,
    )
    tops = set()
    areas = []
    for _ in range(8):
        qtbot.wait(50)
        image = widget.grab().toImage()
        reds = [
            (x, y)
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y).red() > 200 and image.pixelColor(x, y).green() < 80
        ]
        tops.add(min(y for _x, y in reds))
        areas.append(len(reds))
    assert len(tops) > 1
    # 本体始终完整可见：面积不随位置缩水（缩到 80% 即 38 x 38 像素）
    assert min(areas) > 0.9 * 38 * 38
    assert min(areas) > 0.9 * max(areas)


def test_ping_widget_draws_ripple_beyond_the_icon(qtbot: object, widget_collection: None) -> None:
    widget = show_widget(
        qtbot,
        IconWidget(
            "widget:square", size=48, color="#ff0000", animation="ping", animation_period=0.4
        ),
        48,
        48,
    )
    areas = set()
    for _ in range(8):
        qtbot.wait(40)
        image = widget.grab().toImage()
        areas.add(
            sum(
                1
                for y in range(image.height())
                for x in range(image.width())
                if image.pixelColor(x, y).alpha() > 40
            )
        )
    # 本体占一半边长（24 x 24）；水波出现时可见像素明显多于本体
    assert max(areas) > 24 * 24 * 1.5


# --- 图标自带的 SMIL 动画 ---------------------------------------------------

DRAW_LINE = (
    '<path fill="none" stroke="currentColor" stroke-width="4" stroke-dasharray="20" '
    'stroke-dashoffset="20" d="M2 12h20">'
    '<animate fill="freeze" attributeName="stroke-dashoffset" dur="0.4s" to="0"/></path>'
)
SPINNER = (
    '<path fill="none" stroke="currentColor" stroke-width="4" d="M12 2v6">'
    '<animateTransform attributeName="transform" type="rotate" dur="0.6s" repeatCount="indefinite" '
    'values="0 12 12;360 12 12"/></path>'
)


INK = "#ff0000"


def ink(widget: QWidget) -> int:
    """控件截图中图标自己的颜色（纯红）的像素数，用来比较画面。

    只数图标颜色，不看亮度，所以与系统是浅色还是深色主题无关。
    """
    image = widget.grab().toImage()
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).red() > 200 and image.pixelColor(x, y).green() < 60
    )


@pytest.fixture
def smil_icons() -> None:
    from pyside_iconify.core.icon_data import create_icon_data

    add_icon("smil:line", create_icon_data(DRAW_LINE, width=24, height=24))
    add_icon("smil:spin", create_icon_data(SPINNER, width=24, height=24))
    add_icon("smil:plain", create_icon_data('<path stroke="currentColor" d="M0 12h24"/>', width=24, height=24))


def test_smil_icon_draws_itself_then_rests(qtbot: object, smil_icons: None) -> None:
    widget = show_widget(qtbot, IconWidget("smil:line", size=48, color=INK), 48, 48)
    assert widget.isAnimated() and widget.isPlaying()
    qtbot.wait(80)
    partial = ink(widget)
    qtbot.wait(700)
    done = ink(widget)
    assert 0 < partial < done  # 线条一点点画出来
    assert not widget.isPlaying()
    qtbot.wait(100)
    assert ink(widget) == done  # 播完后画面不再变


def test_smil_finished_widget_releases_the_shared_timer(qtbot: object, smil_icons: None) -> None:
    from pyside_iconify.widgets.animation import get_spin_clock

    widget = show_widget(qtbot, IconWidget("smil:line", size=48, color=INK), 48, 48)
    qtbot.wait(900)
    assert not get_spin_clock()._timer.isActive()  # 播完的图标不应让 60fps 定时器空转
    widget.replay()
    assert get_spin_clock()._timer.isActive()


def test_smil_autoplay_false_shows_finished_state_until_play(
    qtbot: object, smil_icons: None
) -> None:
    reference = show_widget(qtbot, IconWidget("smil:line", size=48, color=INK), 48, 48)
    qtbot.wait(900)
    finished = ink(reference)
    widget = show_widget(qtbot, IconWidget("smil:line", size=48, color=INK, autoplay=False), 48, 48)
    qtbot.wait(100)
    assert ink(widget) == finished and not widget.isPlaying()
    widget.play()
    qtbot.wait(60)
    assert ink(widget) < finished  # play() 之后从头画


def test_smil_loop_keeps_moving_and_pause_freezes(qtbot: object, smil_icons: None) -> None:
    widget = show_widget(qtbot, IconWidget("smil:spin", size=48, color=INK), 48, 48)
    frames = set()
    for _ in range(10):
        qtbot.wait(45)
        frames.add(widget.grab().toImage().constBits().tobytes())
    assert len(frames) > 4 and widget.isPlaying()
    widget.pause()
    first = widget.grab().toImage().constBits().tobytes()
    qtbot.wait(250)
    assert widget.grab().toImage().constBits().tobytes() == first and not widget.isPlaying()
    widget.play()
    qtbot.wait(120)
    assert widget.grab().toImage().constBits().tobytes() != first


def test_smil_speed_and_validation(qtbot: object, smil_icons: None) -> None:
    from pyside_iconify import InvalidAnimationError

    for value in (0, -1, True, float("inf")):
        with pytest.raises(InvalidAnimationError):
            IconWidget("smil:line", speed=value)
    widget = IconWidget("smil:line", speed=2.0)
    with pytest.raises(InvalidAnimationError):
        widget.setSpeed(0)
    widget.setSpeed(0.5)


def test_plain_icon_ignores_smil_controls(qtbot: object, smil_icons: None) -> None:
    widget = show_widget(qtbot, IconWidget("smil:plain", size=48, color=INK), 48, 48)
    assert not widget.isAnimated() and not widget.isPlaying()
    widget.play()
    widget.pause()
    widget.replay()


def test_get_icon_shows_the_finished_state(qtbot: object, smil_icons: None) -> None:
    from pyside_iconify import get_icon, is_animated

    assert is_animated("smil:line") and not is_animated("smil:plain")
    pixmap = get_icon("smil:line", size=48, color=INK).pixmap(48, 48)
    image = pixmap.toImage()
    assert image.pixelColor(24, 24).alpha() > 200  # 线条已完整画出，而不是动画第 0 帧的空白


def test_unsupported_smil_falls_back_to_the_finished_icon(
    qtbot: object, caplog: object
) -> None:
    import logging

    from pyside_iconify.core.icon_data import create_icon_data

    body = DRAW_LINE.replace('dur="0.4s"', 'dur="0.4s" end="2s"')
    add_icon("smil:bad", create_icon_data(body, width=24, height=24))
    with caplog.at_level(logging.WARNING, logger="pyside_iconify"):
        widget = show_widget(qtbot, IconWidget("smil:bad", size=48, color=INK), 48, 48)
        qtbot.wait(100)
    assert not widget.isAnimated()
    assert any("unsupported SMIL" in record.getMessage() for record in caplog.records)


def test_set_icon_method_restarts_the_new_animation(qtbot: object, smil_icons: None) -> None:
    from pyside_iconify.core.icon_data import create_icon_data

    add_icon("smil:other", create_icon_data(DRAW_LINE.replace("0.4s", "0.6s"), width=24, height=24))
    widget = show_widget(qtbot, IconWidget("smil:line", size=48, color=INK), 48, 48)
    qtbot.wait(900)
    finished = ink(widget)
    widget.setIcon("smil:other")  # 换成另一个动画图标：应从头画，而不是直接显示完成态
    qtbot.wait(60)
    assert ink(widget) < finished
    qtbot.wait(900)
    assert ink(widget) == finished and not widget.isPlaying()


def test_set_icon_method_respects_autoplay_false(qtbot: object, smil_icons: None) -> None:
    widget = show_widget(
        qtbot, IconWidget("smil:line", size=48, color=INK, autoplay=False), 48, 48
    )
    widget.play()
    qtbot.wait(900)
    finished = ink(widget)
    widget.setIcon("smil:spin")
    qtbot.wait(100)
    assert not widget.isPlaying()  # autoplay=False：换图标后回到完成态，等 play()
    widget.setIcon("smil:line")
    qtbot.wait(100)
    assert ink(widget) == finished
