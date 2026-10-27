"""Animated icons that ship their own SMIL animation (line-md, meteocons, ...).

The panel at the top swaps one IconWidget between icons with ``setIcon()``; the
new icon starts playing from the beginning.

Pick an icon set from the combo box to see every animated icon in it. Each cell
is a plain ``IconWidget``: the icon plays by itself, no extra code needed.

Needs network on first run (the icon sets are fetched from the Iconify API and
cached on disk). Only SMIL animations are played; other kinds of animation are
not supported and such icons are drawn as static images.

Run: uv run examples/smil_showcase.py
Other Qt binding: uv run --isolated --extra pyqt6 examples/smil_showcase.py
(or --extra pyqt5; PySide2: --python 3.10 --extra pyside2)
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

from _qt import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
    make_app,
    run,
)

from _common import add_controls
from _i18n import bind, on_change, t
from pyside_iconify import IconWidget, add_collection

# Icon sets that contain SMIL-animated icons.
SETS = ("line-md", "meteocons", "svg-spinners", "eos-icons")
API = "https://api.iconify.design"
COLUMNS = 8


def _get(path: str) -> dict:
    """请求 Iconify API 并解析 JSON。

    Args:
        path: 以 / 开头的接口路径

    Returns:
        解析后的 JSON 对象。

    Raises:
        OSError: 网络不可用或服务返回错误。
    """
    request = urllib.request.Request(API + path, headers={"User-Agent": "pyside-iconify-example"})
    with urllib.request.urlopen(request, timeout=30) as reply:
        return json.load(reply)


def fetch_animated(prefix: str, limit: int) -> list[str]:
    """取一套图标里带 SMIL 动画的图标，并注册进库里。

    Args:
        prefix: 图标集合前缀
        limit: 最多返回多少个

    Returns:
        已注册的图标名（不含前缀）；网络失败时为空列表。
    """
    try:
        info = _get(f"/collection?prefix={prefix}")
        names = sorted(
            set(info.get("uncategorized", []))
            | {name for group in info.get("categories", {}).values() for name in group}
        )
        icons: dict[str, dict] = {}
        defaults: dict[str, object] = {}
        for start in range(0, len(names), 80):
            chunk = urllib.parse.quote(",".join(names[start : start + 80]))
            data = _get(f"/{prefix}.json?icons={chunk}")
            defaults = {key: value for key, value in data.items() if key != "icons"}
            icons.update(data.get("icons", {}))
            animated = [n for n, icon in icons.items() if "<animate" in icon["body"] or "<set " in icon["body"]]
            if len(animated) >= limit:
                break
    except OSError:
        return []
    chosen = animated[:limit]
    add_collection({**defaults, "prefix": prefix, "icons": {name: icons[name] for name in chosen}}, replace=True)
    return chosen


def build_window() -> QWidget:
    """创建示例窗口。"""
    window = QWidget()
    window.resize(820, 700)
    bind(window.setWindowTitle, "SMIL animated icons", "自带 SMIL 动画的图标")
    root = QVBoxLayout(window)

    top = QHBoxLayout()
    sets = QComboBox()
    sets.addItems(SETS)
    top.addWidget(QLabel("icon set"))
    top.addWidget(sets)
    autoplay = QCheckBox()
    bind(autoplay.setText, "autoplay", "自动播放")
    autoplay.setChecked(True)
    top.addWidget(autoplay)
    replay = QPushButton()
    bind(replay.setText, "Replay all", "全部重播")
    top.addWidget(replay)
    pause = QPushButton()
    bind(pause.setText, "Pause all", "全部暂停")
    top.addWidget(pause)
    play = QPushButton()
    bind(play.setText, "Play all", "全部播放")
    top.addWidget(play)
    top.addStretch(1)
    root.addLayout(top)

    speed_row = QHBoxLayout()
    speed_label = QLabel()
    speed = QSlider(Qt.Orientation.Horizontal)
    speed.setRange(1, 40)
    speed.setValue(10)
    speed_row.addWidget(speed_label)
    speed_row.addWidget(speed, 1)
    root.addLayout(speed_row)

    # setIcon 演示：同一个 IconWidget，换成另一个图标后新图标从头播放
    swap_box = QGroupBox()
    bind(swap_box.setTitle, "Swap the icon with setIcon()", "用 setIcon() 换图标")
    swap_row = QHBoxLayout(swap_box)
    stage = IconWidget("line-md:loading-loop", size=72)
    swap_row.addWidget(stage)
    swap_names = QComboBox()
    swap_names.setMinimumWidth(240)
    swap_row.addWidget(swap_names)
    swap_next = QPushButton()
    bind(swap_next.setText, "Next icon", "下一个图标")
    swap_row.addWidget(swap_next)
    swap_auto = QCheckBox()
    bind(swap_auto.setText, "Swap every 3 s", "每 3 秒自动换")
    swap_row.addWidget(swap_auto)
    swap_code = QLabel()
    swap_code.setStyleSheet("color: palette(mid); font-family: monospace;")
    swap_row.addWidget(swap_code, 1)
    root.addWidget(swap_box)
    swap_timer = QTimer(window)
    swap_timer.setInterval(3000)

    status = QLabel()
    status.setStyleSheet("color: palette(mid);")
    root.addWidget(status)

    area = QScrollArea()
    area.setWidgetResizable(True)
    holder = QWidget()
    grid = QGridLayout(holder)
    area.setWidget(holder)
    root.addWidget(area, 1)
    state: dict[str, object] = {"widgets": [], "count": 0, "prefix": ""}

    def widgets() -> list[IconWidget]:
        return state["widgets"]  # type: ignore[return-value]

    def refresh_texts() -> None:
        """刷新随语言变化的文字。"""
        value = speed.value() / 10
        speed_label.setText(t("speed = {value:.1f}x", "speed = {value:.1f} 倍", value=value))
        count = state["count"]
        status.setText(
            t(
                "{count} animated icons from {prefix}. Hover shows the icon name.",
                "{prefix} 中共 {count} 个带动画的图标，鼠标悬停显示图标名。",
                count=count,
                prefix=state["prefix"],
            )
            if count
            else t("Loading icons, or the network is unavailable...", "正在加载，或网络不可用……")
        )

    def load(prefix: str) -> None:
        """加载一套图标并摆进网格。

        Args:
            prefix: 图标集合前缀
        """
        for widget in widgets():
            widget.setParent(None)
            widget.deleteLater()
        state["widgets"] = []
        state["prefix"] = prefix
        names = fetch_animated(prefix, 96)
        state["count"] = len(names)
        swap_names.blockSignals(True)
        swap_names.clear()
        swap_names.addItems([f"{prefix}:{name}" for name in names])
        swap_names.blockSignals(False)
        if names:
            swap_to(0)
        size = 56 if prefix == "meteocons" else 40
        for index, name in enumerate(names):
            icon = IconWidget(f"{prefix}:{name}", size=size, autoplay=autoplay.isChecked(), speed=speed.value() / 10)
            icon.setToolTip(f"{prefix}:{name}")
            icon.setCursor(Qt.CursorShape.PointingHandCursor)
            icon.mousePressEvent = lambda _event, target=icon: target.replay()  # type: ignore[method-assign]
            grid.addWidget(icon, index // COLUMNS, index % COLUMNS, Qt.AlignmentFlag.AlignCenter)
            widgets().append(icon)
        refresh_texts()

    def swap_to(index: int) -> None:
        """用 setIcon 把演示控件换成列表里第 index 个图标。

        Args:
            index: 图标在下拉框里的序号
        """
        if swap_names.count() == 0:
            return
        index %= swap_names.count()
        name = swap_names.itemText(index)
        swap_names.blockSignals(True)
        swap_names.setCurrentIndex(index)
        swap_names.blockSignals(False)
        stage.setIcon(name)
        swap_code.setText(f'stage.setIcon("{name}")')

    swap_names.currentIndexChanged.connect(swap_to)
    swap_next.clicked.connect(lambda: swap_to(swap_names.currentIndex() + 1))
    swap_auto.toggled.connect(lambda on: swap_timer.start() if on else swap_timer.stop())
    swap_timer.timeout.connect(lambda: swap_to(swap_names.currentIndex() + 1))
    sets.currentTextChanged.connect(load)
    replay.clicked.connect(lambda: [w.replay() for w in widgets()])
    pause.clicked.connect(lambda: [w.pause() for w in widgets()])
    play.clicked.connect(lambda: [w.play() for w in widgets()])
    speed.valueChanged.connect(lambda _v: ([w.setSpeed(speed.value() / 10) for w in widgets()], refresh_texts()))
    on_change(refresh_texts)
    add_controls(window, root)
    load(sets.currentText())
    return window


def main() -> int:
    """运行示例。"""
    app = make_app(sys.argv)
    window = build_window()
    window.show()
    return run(app)


if __name__ == "__main__":
    raise SystemExit(main())
