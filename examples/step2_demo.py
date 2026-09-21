"""Step 2 功能演示窗口：联网下载与缓存。运行需要联网。"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyside_iconify import IconWidget, is_offline, set_offline
from pyside_iconify.network import default_client, load_icons

REMOTE_ICONS = [
    "mdi:home",
    "mdi:account",
    "mdi:weather-night",
    "mdi:weather-sunny",
    "mdi:cog",
    "mdi:this-does-not-exist",
]


def set_palette(window: QWidget, dark: bool) -> None:
    """切换窗口亮暗主题。"""
    palette = QPalette()
    if dark:
        palette.setColor(QPalette.ColorRole.Window, QColor("#1d2128"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#2b313a"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6edf3"))
        palette.setColor(QPalette.ColorRole.Mid, QColor("#9da7b3"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#378add"))
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor("#f6f8fa"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#20242b"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#20242b"))
        palette.setColor(QPalette.ColorRole.Mid, QColor("#57606a"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#378add"))
    QApplication.setPalette(palette)
    window.setStyleSheet(
        """
        QWidget { background: palette(window); color: palette(window-text); }
        QPushButton { padding: 6px 10px; }
        QLabel { background: transparent; }
        """
    )


def build_window() -> QWidget:
    """创建 Step 2 演示窗口。"""
    window = QWidget()
    window.setWindowTitle("pyside-iconify · Step 2：联网下载与缓存")
    window.setMinimumSize(760, 620)
    root = QVBoxLayout(window)
    root.setContentsMargins(18, 18, 18, 18)
    root.setSpacing(12)

    hint = QLabel(
        "以下图标未本地注册，首次显示会自动从 api.iconify.design 下载；"
        "下载完成自动刷新，加载期间显示空白，确认不存在才显示占位图。"
    )
    hint.setWordWrap(True)
    hint.setStyleSheet("color: palette(mid);")
    root.addWidget(hint)

    log = QLabel("事件日志：")
    log.setWordWrap(True)
    log.setStyleSheet("color: palette(mid);")

    def append_log(text: str) -> None:
        lines = log.text().splitlines()
        events = [line for line in lines[1:]] if len(lines) > 1 else []
        log.setText("事件日志：\n" + "\n".join([text] + events[:7]))

    grid = QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(12)
    for index, name in enumerate(REMOTE_ICONS):
        icon = IconWidget(name, size=40)
        icon.statusChanged.connect(
            lambda value, name=name: append_log(f"{name} -> {value}")
        )
        icon.loaded.connect(lambda value, name=name: append_log(f"{name} 数据就绪"))
        icon.failed.connect(
            lambda value, error, name=name: append_log(
                f"{name} 失败：{type(error).__name__}"
            )
        )
        cell = QVBoxLayout()
        cell.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cell.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        label = QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        label.setStyleSheet("color: palette(mid); font-size: 12px;")
        cell.addWidget(label)
        host = QWidget()
        host.setLayout(cell)
        grid.addWidget(host, index // 3, index % 3)
    root.addLayout(grid)
    root.addWidget(log)

    root.addWidget(QLabel("动态预览（输入任意图标名，联网加载）："))

    controls = QHBoxLayout()
    name_edit = QLineEdit("mdi:lightning-bolt")
    name_edit.setPlaceholderText("图标名，如 mdi:lightning-bolt")
    confirm_button = QPushButton("显示")
    size_box = QSpinBox()
    size_box.setRange(12, 128)
    size_box.setValue(40)
    color_button = QPushButton()
    color_button.setToolTip("点击选择颜色；不选则跟随亮暗主题")
    controls.addWidget(name_edit, 1)
    controls.addWidget(confirm_button)
    controls.addWidget(QLabel("大小"))
    controls.addWidget(size_box)
    controls.addWidget(color_button)
    controls.addStretch()
    root.addLayout(controls)
    preview = IconWidget("mdi:lightning-bolt", size=40)
    preview.failed.connect(
        lambda name, error: append_log(
            f"预览失败 {name}：{type(error).__name__}（{error}）"
        )
    )
    root.addWidget(preview, alignment=Qt.AlignmentFlag.AlignHCenter)

    bottom = QHBoxLayout()
    theme_button = QPushButton("切换亮暗主题")
    offline_button = QPushButton()
    preload_button = QPushButton("预加载一批图标（load_icons）")
    reset_button = QPushButton("清除失败记录（允许重试）")
    bottom.addWidget(theme_button)
    bottom.addWidget(offline_button)
    bottom.addWidget(preload_button)
    bottom.addWidget(reset_button)
    bottom.addStretch()
    root.addLayout(bottom)

    chosen_color: list[QColor | None] = [None]

    def refresh_color_button() -> None:
        if chosen_color[0] is None:
            color_button.setText("选择颜色（跟随主题）")
            color_button.setStyleSheet("")
        else:
            color_button.setText(f"颜色 {chosen_color[0].name()}")
            color_button.setStyleSheet(
                f"background: {chosen_color[0].name()};"
            )

    def pick_color() -> None:
        color = QColorDialog.getColor(
            chosen_color[0] or QApplication.palette().color(QPalette.ColorRole.WindowText),
            window,
            "选择图标颜色",
        )
        if color.isValid():
            chosen_color[0] = color
            refresh_color_button()
            apply_preview()

    def apply_preview() -> None:
        preview.setSize(size_box.value())
        preview.setColor(chosen_color[0])
        preview.setIcon(name_edit.text().strip())

    confirm_button.clicked.connect(apply_preview)
    color_button.clicked.connect(pick_color)
    size_box.valueChanged.connect(lambda _: apply_preview())
    name_edit.returnPressed.connect(apply_preview)
    refresh_color_button()

    def refresh_offline_button() -> None:
        offline_button.setText(
            "切换离线模式（当前：离线）" if is_offline() else "切换离线模式（当前：在线）"
        )

    def toggle_offline() -> None:
        set_offline(not is_offline())
        refresh_offline_button()
        append_log(f"离线模式={is_offline()}，离线时不发出任何请求")

    def preload() -> None:
        names = ["mdi:star", "mdi:heart", "mdi:bookmark"]
        append_log("开始预加载 " + ", ".join(names))
        load_icons(
            names,
            on_finished=lambda results: append_log(
                "预加载完成 "
                + "；".join(
                    f"{name}: {'成功' if error is None else type(error).__name__}"
                    for name, error in results.items()
                )
            ),
        )

    def reset_failures() -> None:
        default_client().reset_failures()
        append_log("失败记录已清除，之前失败的图标可重新加载")

    reset_button.clicked.connect(reset_failures)
    offline_button.clicked.connect(toggle_offline)
    preload_button.clicked.connect(preload)

    def toggle_theme() -> None:
        dark = (
            QApplication.palette()
            .color(QPalette.ColorRole.Window)
            .lightness()
            < 128
        )
        set_palette(window, not dark)

    theme_button.clicked.connect(toggle_theme)
    set_palette(window, False)
    refresh_offline_button()
    return window


def main() -> int:
    """运行演示窗口。"""
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
