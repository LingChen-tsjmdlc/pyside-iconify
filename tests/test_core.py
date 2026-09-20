"""图标数据、名称和离线注册测试。"""

from __future__ import annotations

import pytest

from pyside_iconify import (
    DuplicateIconError,
    IconData,
    InvalidIconDataError,
    InvalidIconNameError,
    UnsafeIconDataError,
    add_collection,
    add_icon,
    get_icon_data,
    mark_pending,
)
from pyside_iconify.core.registry import registry
from pyside_iconify.core.svg import build_svg


def test_parses_collection_defaults_and_aliases() -> None:
    add_collection(
        {
            "prefix": "app",
            "width": 48,
            "height": 24,
            "icons": {"bar": {"body": '<rect width="48" height="24"/>'}},
            "aliases": {
                "bar-90": {"parent": "bar", "rotate": 1},
                "bar-flip": {"parent": "bar", "hFlip": True},
            },
        }
    )
    rotated = get_icon_data("app:bar-90")
    assert (rotated.width, rotated.height, rotated.rotate) == (24.0, 48.0, 1)
    assert get_icon_data("app:bar-flip").h_flip
    assert 'viewBox="0 0 24 48"' in build_svg(rotated)


@pytest.mark.parametrize(
    ("name", "body", "error"),
    [
        ("invalid", '<rect width="16" height="16"/>', InvalidIconNameError),
        ("app:unsafe", "<script>alert(1)</script>", UnsafeIconDataError),
    ],
)
def test_rejects_invalid_names_and_unsafe_data(
    name: str, body: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        add_icon(name, body)


def test_rejects_invalid_icon_data() -> None:
    with pytest.raises(InvalidIconDataError):
        IconData("", 24, 24)
    with pytest.raises(InvalidIconDataError):
        IconData("<rect/>", 0, 24)


def test_duplicate_requires_replace() -> None:
    add_icon("app:item", '<rect width="16" height="16"/>')
    with pytest.raises(DuplicateIconError):
        add_icon("app:item", '<circle r="8"/>')


def test_raw_replacement_preserves_existing_coordinate_system() -> None:
    add_collection(
        {
            "prefix": "app",
            "width": 24,
            "height": 24,
            "icons": {"item": {"body": '<rect width="24" height="24"/>'}},
        }
    )
    add_icon("app:item", '<path d="M3 12h18M12 3v18"/>', replace=True)
    data = get_icon_data("app:item")
    assert (data.width, data.height) == (24.0, 24.0)


def test_pending_state_can_be_restarted() -> None:
    mark_pending("app:later")
    assert registry.is_pending("app:later")
    add_icon("app:later", '<rect width="16" height="16"/>')
    assert not registry.is_pending("app:later")
    mark_pending("app:later")
    assert registry.is_pending("app:later")
