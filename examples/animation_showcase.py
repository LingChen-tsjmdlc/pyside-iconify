"""Built-in animations (spin, pulse, breathe, ping, bounce) and the rotation overflow mode.

Everything uses locally registered icons, so no network is needed. The top
section shows the three animations side by side with adjustable period and depth. The
bottom section rotates the same full-bleed square with and without
``rotate_overflow`` so the difference is visible against a shaded icon box.

Run: uv run examples/animation_showcase.py
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from _common import add_controls
from _i18n import bind, on_change, t
from pyside_iconify import IconWidget, add_collection

ICONS = {
    "prefix": "demo",
    "width": 24,
    "height": 24,
    "icons": {
        "heart": {
            "body": '<path d="M12 21s-7-4.6-9.5-9C.9 8.4 2.7 4.5 6.4 4.5c2.1 0 3.8 1.2 5.6 3.4 1.8-2.2 3.5-3.4 5.6-3.4 3.7 0 5.5 3.9 3.9 7.5C19 16.4 12 21 12 21z" fill="currentColor"/>'
        },
        "bell": {
            "body": '<path d="M12 22a2.5 2.5 0 0 0 2.5-2.5h-5A2.5 2.5 0 0 0 12 22zm7-6V11c0-3.1-1.6-5.6-4.5-6.3V4a2.5 2.5 0 0 0-5 0v.7C6.6 5.4 5 7.9 5 11v5l-2 2v1h18v-1z" fill="currentColor"/>'
        },
        "spinner": {
            "body": '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="36 15"/>'
        },
        "square": {
            "body": '<rect x="0" y="0" width="24" height="24" fill="currentColor"/>'
        },
        "arrow": {
            "body": '<path d="M12 1 22 12h-6v11H8V12H2z" fill="currentColor"/>'
        },
    },
}

BOX_STYLE = """
IconWidget[qss~="box"] { background: rgba(128, 128, 128, 0.28); }
"""


def _cell(icon: IconWidget, name: str, en: str, zh: str) -> QWidget:
    """创建一个带标题的图标单元。

    Args:
        icon: 要展示的图标控件。
        name: 动画或参数的原名，原样显示在第一行。
        en: 第二行的英文说明。
        zh: 第二行的中文说明。
    """
    cell = QWidget()
    layout = QVBoxLayout(cell)
    layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
    caption = QLabel()
    caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    caption.setStyleSheet("color: palette(mid);")
    bind(caption.setText, f"{name}\n{en}", f"{name}\n{zh}")
    layout.addWidget(caption)
    return cell


def build_window() -> QWidget:
    """创建示例窗口。"""
    add_collection(ICONS)
    window = QWidget()
    window.setMinimumWidth(760)
    bind(window.setWindowTitle, "Animations and rotation overflow", "动画与旋转溢出")
    root = QVBoxLayout(window)

    # 动画区：内置动画 + 周期、幅度滑块
    animations = QGroupBox()
    bind(animations.setTitle, "Built-in animations", "内置动画")
    animations_layout = QVBoxLayout(animations)
    row = QHBoxLayout()
    spin = IconWidget("demo:spinner", size=48, animation="spin")
    pulse = IconWidget("demo:heart", size=48, color="#d1242f", animation="pulse")
    breathe = IconWidget("demo:bell", size=48, color="#0969da", animation="breathe")
    ping = IconWidget("demo:bell", size=48, color="#bf3989", animation="ping")
    bounce = IconWidget("demo:arrow", size=48, color="#1a7f37", animation="bounce")
    row.addWidget(_cell(spin, 'animation="spin"', "keeps a stable size", "旋转，大小保持稳定"))
    row.addWidget(_cell(pulse, 'animation="pulse"', "scales down and back", "缩小再复原"))
    row.addWidget(_cell(breathe, 'animation="breathe"', "fades out and in", "淡出再淡入"))
    row.addWidget(_cell(ping, 'animation="ping"', "ripple that expands and fades", "水波扩散并淡出"))
    row.addWidget(_cell(bounce, 'animation="bounce"', "jumps up and down", "上下跳跃"))
    animations_layout.addLayout(row)

    period_row = QHBoxLayout()
    period_label = QLabel()
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(2, 40)
    slider.setValue(10)
    period_row.addWidget(period_label)
    period_row.addWidget(slider, 1)
    animations_layout.addLayout(period_row)

    depth_row = QHBoxLayout()
    depth_label = QLabel()
    depth_slider = QSlider(Qt.Orientation.Horizontal)
    depth_slider.setRange(0, 100)
    depth_slider.setValue(35)
    depth_row.addWidget(depth_label)
    depth_row.addWidget(depth_slider, 1)
    animations_layout.addLayout(depth_row)

    def apply_period() -> None:
        """把滑块的周期和幅度应用到所有动画图标，并刷新说明文字。"""
        seconds = slider.value() / 10
        depth = depth_slider.value() / 100
        spin.setAnimation("spin", seconds)
        pulse.setAnimation("pulse", seconds, depth)
        breathe.setAnimation("breathe", seconds, depth)
        ping.setAnimation("ping", seconds, depth)
        bounce.setAnimation("bounce", seconds, depth)
        depth_label.setText(
            t(
                "animation_depth = {depth:.2f}  (all except spin)",
                "animation_depth = {depth:.2f}（spin 以外都生效）",
                depth=depth,
            )
        )
        period_label.setText(
            t("animation_period = {seconds:.1f} s", "animation_period = {seconds:.1f} 秒", seconds=seconds)
        )

    slider.valueChanged.connect(lambda _value: apply_period())
    depth_slider.valueChanged.connect(lambda _value: apply_period())
    on_change(apply_period)
    root.addWidget(animations)

    # 旋转溢出区：同一个铺满的方块，开关溢出
    overflow = QGroupBox()
    bind(overflow.setTitle, "rotate_overflow", "rotate_overflow（旋转溢出）")
    overflow.setStyleSheet(BOX_STYLE)
    overflow_layout = QVBoxLayout(overflow)
    grid = QGridLayout()
    fitted = IconWidget("demo:square", size=72, color="#2da44e", qss="box", rotate=45)
    kept = IconWidget(
        "demo:square", size=72, color="#2da44e", qss="box", rotate=45, rotate_overflow=True
    )
    fitted_spin = IconWidget(
        "demo:arrow", size=72, color="#bf8700", qss="box", animation="spin", animation_period=3.0
    )
    kept_spin = IconWidget(
        "demo:arrow",
        size=72,
        color="#bf8700",
        qss="box",
        animation="spin",
        animation_period=3.0,
        rotate_overflow=True,
    )
    grid.addWidget(_cell(fitted, "rotate=45", "default: shrinks to fit", "默认：缩小以免被裁切"), 0, 0)
    grid.addWidget(_cell(kept, "rotate=45, rotate_overflow=True", "keeps size, corners clip", "保持原大小，四角被裁"), 0, 1)
    grid.addWidget(_cell(fitted_spin, 'animation="spin"', "default: shrinks to fit", "默认：缩小以免被裁切"), 1, 0)
    grid.addWidget(_cell(kept_spin, 'animation="spin", rotate_overflow=True', "keeps size, corners clip", "保持原大小，四角被裁"), 1, 1)
    overflow_layout.addLayout(grid)

    toggle = QCheckBox()
    bind(toggle.setText, "Rotate overflow on the right column (setRotateOverflow)", "右列的旋转溢出开关（setRotateOverflow）")
    toggle.setChecked(True)

    def apply_overflow(checked: bool) -> None:
        """切换右列两个图标的旋转溢出。

        Args:
            checked: 是否保持原大小。
        """
        kept.setRotateOverflow(checked)
        kept_spin.setRotateOverflow(checked)

    toggle.toggled.connect(apply_overflow)
    overflow_layout.addWidget(toggle)
    root.addWidget(overflow)

    add_controls(window, root)
    return window


def main() -> int:
    """运行示例。"""
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
