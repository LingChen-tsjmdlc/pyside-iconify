"""离线打包工具的真联网测试。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    bool(os.environ.get("PYSIDE_ICONIFY_NO_NETWORK")),
    reason="PYSIDE_ICONIFY_NO_NETWORK is set",
)

from pyside_iconify._errors import IconNotFoundError
from pyside_iconify.network.client import default_client
from pyside_iconify.pack import load_bundle, pack_icons, scan_project
from pyside_iconify import get_pixmap
from pyside_iconify.core.registry import registry


def test_scan_project_extracts_icon_names(qtbot: object, tmp_path: object) -> None:
    source = tmp_path / "app.py"
    source.write_text(
        """
        ICONS = ["mdi:home", "mdi:account"]
        label = IconWidget("bi:house")
        url = "10:30"
        plain = "hello world"
        """,
        encoding="utf-8",
    )
    found = scan_project(tmp_path)
    assert found == ["bi:house", "mdi:account", "mdi:home"]
    assert "10:30" not in found


def test_pack_and_load_bundle_offline(
    qtbot: object, tmp_path: object
) -> None:
    """打包后清空内存、离线加载，图标照常显示。"""
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()
    default_client().set_offline(True)
    out = str(tmp_path) + "/bundle.json"
    path = pack_icons(["mdi:truck", "bi:bookmark"], out)
    assert path.exists()
    registry.clear()
    default_client().reset_failures()
    load_bundle(path)
    assert registry.contains("mdi:truck") and registry.contains("bi:bookmark")
    assert not get_pixmap("mdi:truck", size=24).isNull()
    assert not get_pixmap("bi:bookmark", size=24).isNull()
    assert registry.get("bi:bookmark").width == 16.0


def test_pack_reports_missing_icon(qtbot: object, tmp_path: object) -> None:
    with pytest.raises(IconNotFoundError):
        pack_icons(["mdi:not-a-real-icon-xyz"], str(tmp_path) + "/x.json")


def test_load_bundle_finds_meipass(
    qtbot: object, tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """相对路径找不到时自动查 sys._MEIPASS（PyInstaller 打包形态）。"""
    from pyside_iconify import get_pixmap
    from pyside_iconify.core.registry import registry
    from pyside_iconify.pack import load_bundle

    out = str(tmp_path) + "/bundle.json"
    pack_icons(["mdi:flag"], out)
    meipass = tmp_path / "dist"
    meipass.mkdir()
    (meipass / "bundle.json").write_text(
        Path(out).read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(
        "sys._MEIPASS", str(meipass), raising=False
    )
    registry.clear()
    load_bundle("bundle.json")  # 当前目录没有，应从 _MEIPASS 找到
    assert registry.contains("mdi:flag")
    assert not get_pixmap("mdi:flag", size=24).isNull()
