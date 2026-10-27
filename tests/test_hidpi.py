"""高分屏下标准 QIcon 与 IconWidget 是否按物理像素渲染。

屏幕缩放比必须在创建 QApplication 之前通过环境变量设置，所以每个缩放比起一个
子进程，在里面画图并把测量结果传回来。

Qt6 里 QIconEngine 会收到 scaledPixmap(size, scale)；Qt5（PyQt5、PySide2）不会，
只收到 pixmap(size)，并且要应用开启 AA_UseHighDpiPixmaps 才会把尺寸放大成物理像素。
两条路径最终都应画出相同的物理像素宽度，这里一并验证。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from pyside_iconify import _qt

# 子进程里运行的脚本：左 3/4 涂红的图标，量红色的横向像素数
_CHILD = r"""
import json, sys
from pyside_iconify import _qt
Qt = _qt.Qt
if _qt.IS_QT5:
    _qt.QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    _qt.QtCore.QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, sys.argv[1] == "pixmaps")
app = _qt.QApplication(["child"])
from pyside_iconify import IconWidget, add_icon, get_icon
add_icon("t:three", '<rect width="12" height="16" fill="#ff0000"/>')

def red_width(image, row):
    return sum(
        1
        for x in range(image.width())
        if image.pixelColor(x, row).red() > 200 and image.pixelColor(x, row).green() < 60
    )

pixmap = get_icon("t:three", size=24).pixmap(24, 24)
image = pixmap.toImage()
widget = IconWidget("t:three", size=24)
widget.resize(24, 24)
widget.show()
app.processEvents()
grabbed = widget.grab().toImage()
button = _qt.QtWidgets.QPushButton()
button.setIcon(get_icon("t:three", size=24))
button.setIconSize(_qt.QSize(24, 24))
button.resize(60, 40)
button.show()
app.processEvents()
shot = button.grab().toImage()
print(json.dumps({
    "dpr": app.primaryScreen().devicePixelRatio(),
    "qicon_px": pixmap.width(),
    "qicon_dpr": pixmap.devicePixelRatio(),
    "qicon_red": red_width(image, image.height() // 2),
    "widget_px": grabbed.width(),
    "widget_red": red_width(grabbed, grabbed.height() // 2),
    "button_red": red_width(shot, shot.height() // 2),
}))
"""


def _run_child(scale: float, pixmaps: bool = True) -> dict[str, float]:
    """在指定屏幕缩放比下起子进程测量，返回它打印的 JSON。

    Args:
        scale: 屏幕缩放比，通过 QT_SCALE_FACTOR 设置
        pixmaps: Qt5 下是否开启 AA_UseHighDpiPixmaps；Qt6 忽略

    Returns:
        子进程测得的各项数值。
    """
    env = dict(os.environ)
    env["QT_SCALE_FACTOR"] = str(scale)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env[_qt.ENV_VAR] = _qt.BINDING
    # 子进程需要找得到被测的库，沿用父进程的导入路径
    env["PYTHONPATH"] = os.pathsep.join(path for path in sys.path if path)
    result = subprocess.run(
        [sys.executable, "-c", _CHILD, "pixmaps" if pixmaps else "plain"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-800:]
    line = [line for line in result.stdout.splitlines() if line.startswith("{")][-1]
    return json.loads(line)


@pytest.mark.parametrize("scale", [1.0, 1.5, 2.0, 3.0])
def test_qicon_and_widget_render_at_physical_resolution(scale: float) -> None:
    """QIcon、IconWidget、按钮上的图标，红色宽度都应等于逻辑宽度乘缩放比。"""
    measured = _run_child(scale)
    expected = 24 * 0.75 * scale  # 12/16 的视口宽度，逻辑 24px
    assert measured["dpr"] == scale
    assert measured["qicon_px"] == round(24 * scale)
    assert measured["qicon_dpr"] == scale
    for key in ("qicon_red", "widget_red", "button_red"):
        assert abs(measured[key] - expected) <= 1.5, (key, measured)


@pytest.mark.skipif(not _qt.IS_QT5, reason="Qt6 does not need AA_UseHighDpiPixmaps")
def test_qt5_without_high_dpi_pixmaps_is_documented_boundary() -> None:
    """Qt5 应用没开 AA_UseHighDpiPixmaps 时 QIcon 退回 1 倍，IconWidget 不受影响。

    这是 README 里写明的边界：开关属于应用的全局设置，库不替用户打开。
    """
    measured = _run_child(2.0, pixmaps=False)
    assert measured["qicon_px"] == 24 and measured["qicon_dpr"] == 1.0
    assert measured["widget_px"] == 48
    assert abs(measured["widget_red"] - 36) <= 1.5
