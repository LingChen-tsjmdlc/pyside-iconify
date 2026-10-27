"""Network showcase: on-demand icon downloads, caching and offline mode.

The icons below are not registered locally, so each one is fetched from the
Iconify API on first use and cached. Needs network.

Run: uv run examples/network_showcase.py
Other Qt binding: uv run --isolated --extra pyqt6 examples/network_showcase.py
(or --extra pyqt5; PySide2: --python 3.10 --extra pyside2)
"""

from __future__ import annotations

import sys

from _qt import (
    QApplication,
    QColor,
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPalette,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    Qt,
    make_app,
    run,
)

from _common import add_controls
from _i18n import bind, on_change, t
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

# 事件日志最多保留的条数
MAX_LOG_ENTRIES = 8


def build_window() -> QWidget:
    """创建联网下载与缓存的演示窗口。

    Returns:
        已布置好的顶层窗口。
    """
    window = QWidget()
    bind(
        window.setWindowTitle,
        "pyside-iconify · Network download and cache",
        "pyside-iconify · 联网下载与缓存",
    )
    window.setMinimumSize(760, 620)
    root = QVBoxLayout(window)
    root.setContentsMargins(18, 18, 18, 18)
    root.setSpacing(12)

    hint = QLabel()
    bind(
        hint.setText,
        "These icons are not registered locally, so each one is downloaded from "
        "api.iconify.design on first use. The widget refreshes itself when the "
        "download finishes, stays blank while loading, and shows a placeholder "
        "only once the icon is confirmed missing.",
        "以下图标未本地注册，首次显示会自动从 api.iconify.design 下载；"
        "下载完成自动刷新，加载期间显示空白，确认不存在才显示占位图。",
    )
    hint.setWordWrap(True)
    hint.setStyleSheet("color: palette(mid);")
    root.addWidget(hint)

    log = QLabel()
    log.setWordWrap(True)
    log.setStyleSheet("color: palette(mid);")
    # 日志条目存为 (英文, 中文, 字段)，切换语言时整体重新渲染，最新的在前
    log_entries: list[tuple[str, str, dict[str, object]]] = []

    def refresh_log() -> None:
        """按当前语言重新渲染整个事件日志。"""
        header = t("Event log:", "事件日志：")
        lines = [t(en, zh, **fields) for en, zh, fields in log_entries]
        log.setText(header + "\n" + "\n".join(lines) if lines else header)

    def append_log(en: str, zh: str, **fields: object) -> None:
        """追加一条日志，并只保留最新的若干条。

        Args:
            en: 英文文本，可含 {占位符}。
            zh: 中文文本，可含 {占位符}。
            **fields: 占位符对应的字段。
        """
        log_entries.insert(0, (en, zh, fields))
        del log_entries[MAX_LOG_ENTRIES:]
        refresh_log()

    on_change(refresh_log)

    grid = QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(12)
    for index, name in enumerate(REMOTE_ICONS):
        icon = IconWidget(name, size=40)
        icon.statusChanged.connect(
            lambda value, name=name: append_log(
                "{name} -> {value}", "{name} -> {value}", name=name, value=value
            )
        )
        icon.loaded.connect(
            lambda value, name=name: append_log(
                "{name} data ready", "{name} 数据就绪", name=name
            )
        )
        icon.failed.connect(
            lambda value, error, name=name: append_log(
                "{name} failed: {kind}",
                "{name} 失败：{kind}",
                name=name,
                kind=type(error).__name__,
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

    preview_title = QLabel()
    bind(
        preview_title.setText,
        "Dynamic preview (enter any icon name; loaded over the network):",
        "动态预览（输入任意图标名，联网加载）：",
    )
    root.addWidget(preview_title)

    controls = QHBoxLayout()
    name_edit = QLineEdit("mdi:lightning-bolt")
    bind(
        name_edit.setPlaceholderText,
        "Icon name, e.g. mdi:lightning-bolt",
        "图标名，如 mdi:lightning-bolt",
    )
    confirm_button = QPushButton()
    bind(confirm_button.setText, "Show", "显示")
    size_label = QLabel()
    bind(size_label.setText, "Size", "大小")
    size_box = QSpinBox()
    size_box.setRange(12, 128)
    size_box.setValue(40)
    light_button = QPushButton()
    bind(
        light_button.setToolTip,
        "Light theme color (color_light_theme); leave unset to follow the theme text color",
        "亮色主题颜色（color_light_theme）；不选则跟随主题文字色",
    )
    dark_button = QPushButton()
    bind(
        dark_button.setToolTip,
        "Dark theme color (color_dark_theme); leave unset to follow the theme text color",
        "暗色主题颜色（color_dark_theme）；不选则跟随主题文字色",
    )
    controls.addWidget(name_edit, 1)
    controls.addWidget(confirm_button)
    controls.addWidget(size_label)
    controls.addWidget(size_box)
    controls.addWidget(light_button)
    controls.addWidget(dark_button)
    controls.addStretch()
    root.addLayout(controls)
    preview = IconWidget("mdi:lightning-bolt", size=40)
    preview.failed.connect(
        lambda name, error: append_log(
            "Preview failed for {name}: {kind} ({error})",
            "预览失败 {name}：{kind}（{error}）",
            name=name,
            kind=type(error).__name__,
            error=error,
        )
    )
    root.addWidget(preview, alignment=Qt.AlignmentFlag.AlignHCenter)

    bottom = QHBoxLayout()
    offline_button = QPushButton()
    preload_button = QPushButton()
    bind(
        preload_button.setText,
        "Preload icons (load_icons)",
        "预加载一批图标（load_icons）",
    )
    reset_button = QPushButton()
    bind(
        reset_button.setText,
        "Clear failures (allow retry)",
        "清除失败记录（允许重试）",
    )
    bottom.addWidget(offline_button)
    bottom.addWidget(preload_button)
    bottom.addWidget(reset_button)
    bottom.addStretch()
    root.addLayout(bottom)

    chosen_light: list[QColor | None] = [None]
    chosen_dark: list[QColor | None] = [None]

    def refresh_color_button(
        button: QPushButton, chosen: list[QColor | None], en: str, zh: str
    ) -> None:
        """按已选颜色刷新颜色按钮的文字与底色。

        Args:
            button: 要刷新的按钮。
            chosen: 已选颜色，None 表示跟随主题。
            en: 英文名称。
            zh: 中文名称。
        """
        label = t(en, zh)
        if chosen[0] is None:
            button.setText(t("{label} (follows theme)", "{label}（跟随）", label=label))
            button.setStyleSheet("")
        else:
            button.setText(f"{label} {chosen[0].name()}")
            button.setStyleSheet(f"background: {chosen[0].name()};")

    def make_picker(
        button: QPushButton,
        chosen: list[QColor | None],
        names: tuple[str, str],
        title: tuple[str, str],
        default_role: QPalette.ColorRole,
    ) -> object:
        """生成颜色按钮的点击处理函数，并登记按钮文字的语言刷新。

        Args:
            button: 对应的颜色按钮。
            chosen: 保存已选颜色的列表。
            names: 按钮上的名称（英文, 中文）。
            title: 颜色对话框标题（英文, 中文）。
            default_role: 未选色时对话框的初始调色板角色。
        """

        def pick() -> None:
            color = QColorDialog.getColor(
                chosen[0] or QApplication.palette().color(default_role),
                window,
                t(*title),
            )
            if color.isValid():
                chosen[0] = color
                refresh_color_button(button, chosen, *names)
                apply_preview()

        on_change(lambda: refresh_color_button(button, chosen, *names))
        return pick

    def apply_preview() -> None:
        """按当前输入重新设置预览图标。"""
        preview.setSize(size_box.value())
        preview.setColorLightTheme(chosen_light[0])
        preview.setColorDarkTheme(chosen_dark[0])
        preview.setIcon(name_edit.text().strip())

    confirm_button.clicked.connect(apply_preview)
    light_button.clicked.connect(
        make_picker(
            light_button,
            chosen_light,
            ("Light", "亮色"),
            ("Choose light theme color", "选择亮色"),
            QPalette.ColorRole.WindowText,
        )
    )
    dark_button.clicked.connect(
        make_picker(
            dark_button,
            chosen_dark,
            ("Dark", "暗色"),
            ("Choose dark theme color", "选择暗色"),
            QPalette.ColorRole.Window,
        )
    )
    size_box.valueChanged.connect(lambda _: apply_preview())
    name_edit.returnPressed.connect(apply_preview)

    def refresh_offline_button() -> None:
        """按当前在线状态刷新离线按钮文字。"""
        offline_button.setText(
            t(
                "Toggle offline mode (now: {state})",
                "切换离线模式（当前：{state}）",
                state=t("offline", "离线") if is_offline() else t("online", "在线"),
            )
        )

    def toggle_offline() -> None:
        """切换离线模式并记录日志。"""
        set_offline(not is_offline())
        refresh_offline_button()
        append_log(
            "Offline mode = {state}; no requests are sent while offline",
            "离线模式={state}，离线时不发出任何请求",
            state=is_offline(),
        )

    def preload() -> None:
        """预加载一批图标，完成后把结果写入日志。"""
        names = ["mdi:star", "mdi:heart", "mdi:bookmark"]
        append_log("Preloading {names}", "开始预加载 {names}", names=", ".join(names))

        def on_finished(results: dict[str, object]) -> None:
            """预加载结束后把各图标的结果写入日志。

            Args:
                results: 图标名到错误的映射，None 表示成功。
            """
            en = "; ".join(
                f"{name}: {'ok' if error is None else type(error).__name__}"
                for name, error in results.items()
            )
            zh = "；".join(
                f"{name}: {'成功' if error is None else type(error).__name__}"
                for name, error in results.items()
            )
            # 不带字段，文本不会被 format，图标名中的花括号也无影响
            append_log("Preload finished: " + en, "预加载完成 " + zh)

        load_icons(names, on_finished=on_finished)

    def reset_failures() -> None:
        """清除失败记录并写入日志。"""
        default_client().reset_failures()
        append_log(
            "Failures cleared; icons that failed earlier can be loaded again",
            "失败记录已清除，之前失败的图标可重新加载",
        )

    reset_button.clicked.connect(reset_failures)
    offline_button.clicked.connect(toggle_offline)
    preload_button.clicked.connect(preload)

    on_change(refresh_offline_button)
    add_controls(window, root)
    return window


def main() -> int:
    """运行演示窗口。"""
    app = make_app(sys.argv)
    window = build_window()
    window.show()
    return run(app)


if __name__ == "__main__":
    raise SystemExit(main())
