"""IconWidget、QSS、状态和动画测试。"""

from __future__ import annotations

import pytest
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


def test_qss_color_background_and_explicit_color_priority(
    qtbot: object, widget_collection: None
) -> None:
    host = QWidget()
    host.resize(200, 100)
    host.setStyleSheet(
        'IconWidget[qss~="blue"] { color: #0000ff; background: #111111; }'
    )
    qtbot.addWidget(host)
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
    host.show()
    theme = IconWidget("widget:square", size=24, parent=host)
    override = IconWidget(
        "widget:square",
        size=24,
        color="#ff0000",
        light_color="#8250df",
        dark_color="#1a7f37",
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
    image = blank._pixmap(option).toImage()
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
