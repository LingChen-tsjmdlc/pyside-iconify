"""公开 API、默认配置和缓存测试。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton

from pyside_iconify import (
    IconData,
    InvalidOpacityError,
    add_collection,
    get_default_config,
    get_icon,
    get_pixmap,
    set_cache_limits,
    set_default_config,
)
from tests.helpers import assert_color, icon_color


@pytest.fixture
def api_collection() -> None:
    add_collection(
        {
            "prefix": "api",
            "width": 24,
            "height": 24,
            "icons": {
                "square": {
                    "body": '<rect width="24" height="24" fill="currentColor"/>'
                },
                "replace": {"body": '<rect width="24" height="24" fill="#00ff00"/>'},
            },
        }
    )


def test_get_icon_is_usable_by_standard_qt_widgets(api_collection: None) -> None:
    icon = get_icon("api:square", size=20, color="#ff0000")
    button = QPushButton()
    button.setIcon(icon)
    assert not button.icon().isNull()
    assert icon.actualSize(QSize(90, 90)).width() == 20


def test_get_pixmap_and_inline_icon_data(api_collection: None) -> None:
    pixmap = get_pixmap("api:square", size=20, color="#ff0000")
    assert (pixmap.width(), pixmap.height()) == (20, 20)
    inline = get_icon(IconData('<rect width="24" height="24" fill="#123456"/>', 24, 24))
    assert_color(icon_color(inline), "#123456")


def test_existing_qicon_refreshes_after_replacement(api_collection: None) -> None:
    icon = get_icon("api:replace")
    assert_color(icon_color(icon), "#00ff00")
    add_collection(
        {
            "prefix": "api",
            "icons": {
                "replace": {"body": '<rect width="24" height="24" fill="#0000ff"/>'}
            },
        },
        replace=True,
    )
    assert_color(icon_color(icon), "#0000ff")


def test_default_config_only_affects_future_icons(api_collection: None) -> None:
    set_default_config(size=30, color="#ff0000")
    old = get_icon("api:square")
    set_default_config(size=40, color="#0000ff")
    new = get_icon("api:square")
    assert old.actualSize(QSize(99, 99)).width() == 30
    assert new.actualSize(QSize(99, 99)).width() == 40
    set_default_config(size=None, color=None)
    assert get_default_config().size == 24


def test_configuration_and_cache_limits_validate() -> None:
    with pytest.raises(InvalidOpacityError):
        set_default_config(disabled_opacity=2)
    set_cache_limits(pixmap_mib=8, data_entries=100)
    with pytest.raises(ValueError):
        set_cache_limits(data_entries=0)
    with pytest.raises(ValueError):
        set_cache_limits(pixmap_mib=0)


def test_disabled_qicon_uses_opacity(api_collection: None) -> None:
    icon = get_icon("api:square", color="#ff0000")
    alpha = icon_color(icon, mode=QIcon.Mode.Disabled).alpha()
    assert 90 < alpha < 115
