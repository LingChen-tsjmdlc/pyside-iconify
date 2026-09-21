"""开箱即用路径测试：零注册，直接用公开 API。"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    bool(os.environ.get("PYSIDE_ICONIFY_NO_NETWORK")),
    reason="PYSIDE_ICONIFY_NO_NETWORK is set",
)

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QPushButton

from pyside_iconify import IconWidget, get_icon
from pyside_iconify.core.registry import registry
from pyside_iconify.network.client import default_client

from tests.test_network_integration import wait_until


def test_out_of_box_button_icon_appears(qtbot: object) -> None:
    """get_icon 直接给按钮，下载完成自动出现，不写任何加载代码。"""
    client = default_client()
    client.set_offline(False)
    client.reset_failures()
    button = QPushButton("按钮")
    button.setIcon(get_icon("mdi:account-supervisor", size=24))
    button.setIconSize(QSize(24, 24))
    qtbot.addWidget(button)
    button.show()
    assert wait_until(lambda: registry.contains("mdi:account-supervisor"))
    qtbot.waitUntil(
        lambda: any(
            button.icon().pixmap(24, 24).toImage().pixelColor(x, y).alpha() > 0
            for y in range(24)
            for x in range(24)
        ),
        timeout=3000,
    )


def test_out_of_box_widget_icon_appears(qtbot: object) -> None:
    """IconWidget 零注册直接显示远程图标。"""
    client = default_client()
    client.set_offline(False)
    client.reset_failures()
    widget = IconWidget("mdi:email-outline", size=32)
    qtbot.addWidget(widget)
    widget.show()
    assert wait_until(lambda: registry.contains("mdi:email-outline"))
    qtbot.waitUntil(
        lambda: any(
            widget.grab().toImage().pixelColor(x, y).alpha() > 0
            for y in range(widget.height())
            for x in range(widget.width())
        ),
        timeout=3000,
    )


def test_construction_triggers_load_before_paint(qtbot: object) -> None:
    """构造 get_icon 时就发起加载，不等首次绘制（树节点/菜单场景）。"""
    client = default_client()
    client.set_offline(False)
    client.reset_failures()
    icon = get_icon("mdi:truck-delivery", size=24)  # 不创建任何控件、不绘制
    assert wait_until(lambda: registry.contains("mdi:truck-delivery"))
    assert not icon.isNull()
