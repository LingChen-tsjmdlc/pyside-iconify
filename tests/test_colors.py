"""颜色解析、颜色映射和透明度测试。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from pyside_iconify import (
    IconWidget,
    InvalidColorError,
    add_collection,
    get_icon,
    get_icon_colors,
    hex_argb,
    hex_rgba,
    is_monotone,
)
from tests.helpers import assert_color, show_widget, widget_color


@pytest.fixture
def color_collection() -> None:
    add_collection(
        {
            "prefix": "color",
            "width": 24,
            "height": 24,
            "icons": {
                "mono": {"body": '<rect width="24" height="24" fill="currentColor"/>'},
                "multi": {
                    "body": '<rect width="12" height="24" fill="#4285f4"/>'
                    '<rect x="12" width="12" height="24" fill="hsl(0, 100%, 50%)"/>'
                },
            },
        }
    )


@pytest.mark.parametrize(
    "color",
    [
        "red",
        "#f00",
        "#f008",
        "#ff0000",
        "#ff000080",
        "rgb(255, 0, 0)",
        "rgba(255, 0, 0, 0.5)",
        "hsl(0, 100%, 50%)",
        "hsla(0, 100%, 50%, 0.5)",
        (255, 0, 0),
        (255, 0, 0, 128),
        QColor("red"),
        Qt.GlobalColor.red,
    ],
)
def test_accepts_supported_color_forms(color: object, color_collection: None) -> None:
    assert not get_icon("color:mono", color=color).isNull()


def test_hex_helpers_match() -> None:
    assert hex_argb("#80ff0000") == hex_rgba("#ff000080")


def test_invalid_color_raises(color_collection: None) -> None:
    with pytest.raises(InvalidColorError):
        get_icon("color:mono", color="not-a-color")


def test_multicolor_single_color_keeps_original_palette(
    qtbot: object, color_collection: None
) -> None:
    widget = show_widget(qtbot, IconWidget("color:multi", size=24, color="#00ff00"))
    assert_color(widget_color(widget, 6, 12), "#4285f4")
    assert_color(widget_color(widget, 18, 12), "#ff0000")


def test_mapping_matches_normalized_color_and_keeps_unmapped_color(
    qtbot: object, color_collection: None
) -> None:
    widget = show_widget(
        qtbot,
        IconWidget("color:multi", size=24, color={"rgb(66, 133, 244)": "#00a0ff"}),
    )
    assert_color(widget_color(widget, 6, 12), "#00a0ff")
    assert_color(widget_color(widget, 18, 12), "#ff0000")


def test_color_introspection(color_collection: None) -> None:
    assert is_monotone("color:mono")
    assert not is_monotone("color:multi")
    assert get_icon_colors("color:multi") == ("#4285f4", "#ff0000")
