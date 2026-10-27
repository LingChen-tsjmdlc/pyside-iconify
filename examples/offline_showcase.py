"""Offline feature showcase for pyside-iconify (no network).

Every icon comes from Iconify JSON registered in the window itself. The sections
cover sizes, color formats, multicolor icons, animation, QSS, missing-icon states,
aliases, delayed data, runtime updates and a built-in interface self-check.

Run: uv run examples/offline_showcase.py
Other Qt binding: uv run --isolated --extra pyqt6 examples/offline_showcase.py
(or --extra pyqt5; PySide2: --python 3.10 --extra pyside2)
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable

from _qt import (
    QColor,
    QEvent,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSize,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
    make_app,
    run,
)

from _common import add_controls
from _i18n import bind, on_change, t
from _theme import is_dark
from pyside_iconify import (
    IconData,
    IconifyError,
    IconWidget,
    WrongThreadError,
    add_collection,
    add_icon,
    get_default_config,
    get_icon,
    get_icon_colors,
    get_pixmap,
    hex_argb,
    hex_rgba,
    is_monotone,
    mark_pending,
    set_cache_limits,
    set_default_config,
    set_disabled_opacity,
)


def register_icons() -> None:
    """注册演示使用的离线图标。"""
    add_collection(
        {
            "prefix": "demo",
            "width": 24,
            "height": 24,
            "aliases": {
                "home-90": {"parent": "home", "rotate": 1},
                "home-flip": {"parent": "home", "hFlip": True},
            },
            "icons": {
                "home": {
                    "body": '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>'
                },
                "mutable": {
                    "body": '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>'
                },
                "spinner": {
                    "body": '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" '
                    'stroke-width="3" stroke-linecap="round" stroke-dasharray="36 15"/>'
                },
                "brand": {
                    "body": '<circle cx="7" cy="12" r="5" fill="#4285f4"/>'
                    '<circle cx="17" cy="7" r="5" fill="#ea4335"/>'
                    '<circle cx="17" cy="17" r="5" fill="#fbbc05"/>'
                },
                "arrow": {
                    "body": '<path d="M4 12h13m-5-5 5 5-5 5" fill="none" stroke="currentColor" '
                    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
                },
                "help": {
                    "body": '<rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor"/>'
                    '<text x="12" y="17" text-anchor="middle" fill="#ffffff" font-size="14">?</text>'
                },
            },
        }
    )


def bind_state(setter: Callable[[str], object], en: str, zh: str, **fields: object) -> Callable[..., None]:
    """绑定一段随状态变化的文本，返回更新函数。

    语言切换时按最近一次的文本和字段重新渲染。

    Args:
        setter: 接收字符串的设置函数。
        en: 初始英文文本。
        zh: 初始中文文本。
        **fields: 初始格式化字段。

    Returns:
        update(en, zh, **fields)：保存新的文本与字段并立即刷新。
    """
    current: dict[str, object] = {"en": en, "zh": zh, "fields": fields}

    def refresh() -> None:
        setter(t(current["en"], current["zh"], **current["fields"]))

    def update(en: str, zh: str, **fields: object) -> None:
        current.update(en=en, zh=zh, fields=fields)
        refresh()

    on_change(refresh)
    return update


def new_caption() -> QLabel:
    """创建带说明样式、尚未设置文字的标签。"""
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    label.setWordWrap(True)
    label.setStyleSheet("color: palette(mid); font-size: 12px;")
    return label


def make_caption(en: str, zh: str) -> QLabel:
    """创建随语言切换的图标说明文字。

    Args:
        en: 英文文本。
        zh: 中文文本。
    """
    label = new_caption()
    bind(label.setText, en, zh)
    return label


def make_cell(icon: IconWidget, en: str, zh: str) -> QWidget:
    """创建一个图标展示单元。

    Args:
        icon: 要展示的图标控件。
        en: 图标下方的英文说明。
        zh: 图标下方的中文说明。
    """
    cell = QWidget()
    cell.setObjectName("demoCell")
    layout = QVBoxLayout(cell)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(make_caption(en, zh))
    return cell


def make_section(
    title_en: str, title_zh: str, description_en: str, description_zh: str
) -> tuple[QWidget, QGridLayout]:
    """创建一个功能展示区。

    Args:
        title_en: 英文标题。
        title_zh: 中文标题。
        description_en: 英文说明。
        description_zh: 中文说明。

    Returns:
        分区控件和放置单元格的网格布局。
    """
    section = QFrame()
    section.setObjectName("section")
    section.setFrameShape(QFrame.Shape.StyledPanel)
    outer = QVBoxLayout(section)
    outer.setContentsMargins(14, 12, 14, 12)
    outer.setSpacing(8)
    heading = QLabel()
    heading.setStyleSheet("font-size: 15px; font-weight: 600;")
    bind(heading.setText, title_en, title_zh)
    outer.addWidget(heading)
    description = QLabel()
    bind(description.setText, description_en, description_zh)
    outer.addWidget(description)
    grid = QGridLayout()
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(10)
    outer.addLayout(grid)
    return section, grid


def _extra_style(dark: bool) -> str:
    """返回 _theme 未覆盖的专有样式：分区面板与 IconWidget 的 qss 配色。"""
    if dark:
        return """
            QFrame#section { background: #161b22; border: 1px solid #4f5866; border-radius: 8px; }
            QWidget#demoCell { background: transparent; }
            IconWidget[qss~="qss-blue"] { color: #58a6ff; background: #102a43; }
            IconWidget[qss~="qss-blue"]:disabled { color: #58a6ff; background: #102a43; }
            IconWidget[qss~="qss-green"] { color: #3fb950; background: #12261a; }
        """
    return """
        QFrame#section { background: #ffffff; border: 1px solid #8c959f; border-radius: 8px; }
        QWidget#demoCell { background: transparent; }
        IconWidget[qss~="qss-blue"] { color: #378add; background: #eaf3ff; }
        IconWidget[qss~="qss-blue"]:disabled { color: #378add; background: #eaf3ff; }
        IconWidget[qss~="qss-green"] { color: #1a7f37; background: #dafbe1; }
    """


class DemoWindow(QWidget):
    """演示窗口，应用主题变化时同步专有样式。"""

    content: QWidget | None = None

    def event(self, event: QEvent) -> bool:
        """应用调色板变化后，刷新内容区的专有样式。"""
        handled = super().event(event)
        if event.type() == QEvent.Type.ApplicationPaletteChange and self.content is not None:
            self.content.setStyleSheet(_extra_style(is_dark()))
        return handled


def build_window() -> QWidget:
    """创建离线功能演示窗口。"""
    set_default_config(size=24, color=None, color_light_theme=None, color_dark_theme=None)
    window = DemoWindow()
    window.setObjectName("demoWindow")
    bind(window.setWindowTitle, "pyside-iconify · Feature showcase", "pyside-iconify · 功能演示")
    window.setMinimumSize(820, 620)
    outer = QVBoxLayout(window)
    outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea()
    scroll.setObjectName("demoScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    outer.addWidget(scroll)
    content = QWidget()
    content.setObjectName("demoContent")
    scroll.setWidget(content)
    window.content = content
    root = QVBoxLayout(content)
    root.setContentsMargins(20, 18, 20, 18)
    root.setSpacing(14)

    title = QLabel()
    title.setStyleSheet("font-size: 22px; font-weight: 700;")
    bind(title.setText, "pyside-iconify · Offline icons", "pyside-iconify · 离线图标能力")
    root.addWidget(title)
    intro = QLabel()
    bind(
        intro.setText,
        "All icons come from Iconify JSON registered in this window; no network requests. "
        "Each group shows one visible capability.",
        "所有图标来自本窗口注册的 Iconify JSON；不请求网络。每一组展示一项可见能力。",
    )
    root.addWidget(intro)

    size_section, size_grid = make_section(
        "Size, color and rotation",
        "尺寸、颜色与旋转",
        "Default size=24; number, pixel string, tuple, QSize and em sizes; "
        "color arguments, opacity and rotation by any angle.",
        "默认 size=24；数字、像素字符串、元组、QSize、em；颜色参数、透明度和任意角度旋转。",
    )
    size_icons = [
        (IconWidget("demo:home", color="#57606a"), "No size\ndefault size=24", "不传 size\n默认 size=24"),
        (
            IconWidget("demo:home", size=18, color="#d1242f"),
            "size=18\ncolor=#d1242f",
            "size=18\ncolor=#d1242f",
        ),
        (
            IconWidget("demo:home", size="28px", color="rgb(9, 105, 218)"),
            "size='28px'\nrgb()",
            "size='28px'\nrgb()",
        ),
        (
            IconWidget("demo:home", size=QSize(30, 30), color=QColor("#8250df")),
            "size=QSize(30, 30)\nQColor",
            "size=QSize(30, 30)\nQColor",
        ),
        (
            IconWidget("demo:home", size=(36, 24), color="hsl(142, 71%, 45%)"),
            "size=(36, 24)\nhsl()",
            "size=(36, 24)\nhsl()",
        ),
        (
            IconWidget("demo:arrow", size=34, color="#8250df", rotate=45),
            "rotate=45\nnot clipped",
            "rotate=45\n不裁切",
        ),
        (
            IconWidget("demo:home", size="1.8em", color="#bf8700"),
            "size='1.8em'\nfollows font size",
            "size='1.8em'\n跟随字号",
        ),
    ]
    for index, (icon, en, zh) in enumerate(size_icons):
        size_grid.addWidget(make_cell(icon, en, zh), index // 7, index % 7)
    size_grid.addWidget(
        make_cell(
            IconWidget("demo:home", size=24.5, color="#0969da"),
            "size=24.5\nfractional logical pixels",
            "size=24.5\n小数逻辑像素",
        ),
        1,
        0,
    )
    size_grid.addWidget(
        make_cell(
            IconWidget("demo:home", size=24, width=48, height=20, color="#1a7f37"),
            "width=48\nheight=20",
            "width=48\nheight=20",
        ),
        1,
        1,
    )
    size_grid.addWidget(
        make_cell(
            IconWidget("demo:arrow", size=34, color="#8250df", h_flip=True),
            "h_flip=True\nflipped horizontally",
            "h_flip=True\n水平翻转",
        ),
        1,
        2,
    )
    size_grid.addWidget(
        make_cell(
            IconWidget("demo:arrow", size=34, color="#bf8700", v_flip=True),
            "v_flip=True\nflipped vertically",
            "v_flip=True\n垂直翻转",
        ),
        1,
        3,
    )
    root.addWidget(size_section)

    format_section, format_grid = make_section(
        "Color formats, opacity and conversion functions",
        "颜色输入格式、透明度与转换函数",
        "Color names, HEX with 3/4/6/8 digits, rgba, hsla, tuples, QColor, Qt enums and the "
        "two explicit HEX orders. Translucent icons blend with the background.",
        "颜色名、HEX 3/4/6/8 位、rgba、hsla、元组、QColor、Qt 枚举以及两种显式 HEX 顺序。半透明图标会与背景混合。",
    )
    color_formats = [
        ("#f00", "HEX 3 digits\n#f00", "HEX 3 位\n#f00"),
        ("#f008", "HEX 4 digits\n#f008", "HEX 4 位\n#f008"),
        ("#ff0000", "HEX 6 digits\n#ff0000", "HEX 6 位\n#ff0000"),
        ("#ff000080", "HEX 8 digits\n#ff000080", "HEX 8 位\n#ff000080"),
        ("rgba(255, 0, 0, 0.5)", "rgba()", "rgba()"),
        ("hsla(210, 100%, 50%, 0.5)", "hsla()", "hsla()"),
        ((255, 0, 0), "RGB tuple\n(255, 0, 0)", "RGB 元组\n(255, 0, 0)"),
        ((255, 0, 0, 128), "RGBA tuple\n(255, 0, 0, 128)", "RGBA 元组\n(255, 0, 0, 128)"),
        (QColor("#8250df"), "QColor\n#8250df", "QColor\n#8250df"),
        (Qt.GlobalColor.darkGreen, "Qt.GlobalColor\ndarkGreen", "Qt.GlobalColor\ndarkGreen"),
        (hex_argb("#80ff0000"), "hex_argb()\n#80ff0000", "hex_argb()\n#80ff0000"),
        (hex_rgba("#ff000080"), "hex_rgba()\n#ff000080", "hex_rgba()\n#ff000080"),
    ]
    for index, (color, en, zh) in enumerate(color_formats):
        format_grid.addWidget(
            make_cell(IconWidget("demo:home", size=28, color=color), en, zh),
            index // 6,
            index % 6,
        )
    root.addWidget(format_section)

    color_section, color_grid = make_section(
        "Multicolor icons, theme, disabled state and opacity",
        "多色图标、主题、禁用与透明度",
        "Multicolor icons keep their original colors; a mapping replaces only the colors "
        "you name. Without a color, the icon follows the text color.",
        "多色图标保持原配色；映射表只替换指定原色。未指定颜色时跟随文字色。",
    )
    original = IconWidget("demo:brand", size=42, color="#00ff00")
    mapped = IconWidget("demo:brand", size=42, color={"rgb(66, 133, 244)": "#00a0ff"})
    theme_icon = IconWidget("demo:home", size=42)
    theme_override = IconWidget(
        "demo:home",
        size=42,
        color="#57606a",
        color_light_theme="#8250df",
        color_dark_theme="#1a7f37",
    )
    disabled = IconWidget("demo:home", size=42, color="#d1242f", opacity=0.5)
    disabled.setEnabled(False)
    for column, (icon, en, zh) in enumerate(
        [
            (
                original,
                "Multicolor + single color argument\nkeeps original colors",
                "多色 + 单色参数\n保持原配色",
            ),
            (mapped, "Color mapping\nreplaces only blue", "颜色映射表\n只替换蓝色"),
            (theme_icon, "No color\nfollows theme text color", "不传 color\n跟随主题文字色"),
            (
                theme_override,
                "color_light_theme / color_dark_theme\ntakes priority over color",
                "color_light_theme / color_dark_theme\n优先于 color",
            ),
            (disabled, "opacity=0.5\nfades further when disabled", "opacity=0.5\n禁用后继续变淡"),
        ]
    ):
        color_grid.addWidget(make_cell(icon, en, zh), 0, column)
    root.addWidget(color_section)

    behavior_section, behavior_grid = make_section(
        "Animation, QSS, missing states and QIcon",
        "动画、QSS、缺失状态与 QIcon",
        "A spinning icon keeps a stable size; QSS can set color and background; the three "
        "missing states show a fallback, the built-in placeholder and a transparent blank.",
        "旋转图标保持稳定尺寸；QSS 可设置颜色和背景；三个缺失状态分别展示回退、内置占位图和透明空白。",
    )
    spinner = IconWidget("demo:spinner", size=42, spin=True, qss="qss-blue")
    qss_icon = IconWidget("demo:home", size=42, qss="qss-blue")
    fallback = IconWidget(
        "demo:not-found", size=42, fallback="demo:help", qss="qss-blue"
    )
    builtin_placeholder = IconWidget(
        "demo:not-found", size=42, fallback="demo:also-not-found"
    )
    blank_on_failure = IconWidget("demo:not-found", size=42, fallback=None)
    missing_signal = new_caption()
    show_missing = bind_state(
        missing_signal.setText, "failed signal: waiting for paint", "failed 信号：等待绘制"
    )
    builtin_placeholder.failed.connect(
        lambda name, error: show_missing(
            "failed signal: {name}", "failed 信号：{name}", name=name
        )
    )
    button = QPushButton()
    bind(button.setText, "get_icon() on a plain QPushButton", "get_icon() 设置给普通 QPushButton")
    button.setIcon(get_icon("demo:home", size=22, color="#378add"))
    button.setIconSize(QSize(22, 22))
    behavior_grid.addWidget(
        make_cell(spinner, "spin=True\nshared animation clock", "spin=True\n共享动画时钟"), 0, 0
    )
    behavior_grid.addWidget(
        make_cell(qss_icon, "qss='qss-blue'\ncolor + background", "qss='qss-blue'\n颜色 + 背景"), 0, 1
    )
    behavior_grid.addWidget(
        make_cell(fallback, "Icon missing\nfallback succeeds", "图标缺失\nfallback 成功"), 0, 2
    )
    placeholder_cell = make_cell(
        builtin_placeholder,
        "Icon and fallback both missing\nbuilt-in placeholder",
        "图标和 fallback 都缺失\n内置占位图",
    )
    placeholder_cell.layout().addWidget(missing_signal)
    behavior_grid.addWidget(placeholder_cell, 0, 3)
    behavior_grid.addWidget(
        make_cell(
            blank_on_failure,
            "Icon missing\nfallback=None, transparent blank",
            "图标缺失\nfallback=None，透明空白",
        ),
        0,
        4,
    )
    behavior_grid.addWidget(button, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
    root.addWidget(behavior_section)

    alias_section, alias_grid = make_section(
        "Aliases, flips, delayed data and static pixmaps",
        "别名、翻转、延迟数据与静态位图",
        "An Iconify alias inherits icon data and adds rotation or flipping; a delayed icon "
        "starts blank and appears once its data is registered.",
        "Iconify alias 会继承图标数据并叠加旋转或翻转；延迟图标先空白，数据注册后自动出现。",
    )
    alias_grid.addWidget(
        make_cell(
            IconWidget("demo:home-90", size=42, color="#8250df"),
            "aliases.rotate=1\n90° alias",
            "aliases.rotate=1\n90 度别名",
        ),
        0,
        0,
    )
    alias_grid.addWidget(
        make_cell(
            IconWidget("demo:home-flip", size=42, color="#d1242f"),
            "aliases.hFlip=true\nhorizontal flip alias",
            "aliases.hFlip=true\n水平翻转别名",
        ),
        0,
        1,
    )
    mark_pending("demo:later")
    loading_icon = IconWidget("demo:later", size=42, color="#1a7f37")
    loading_status = new_caption()
    show_loading = bind_state(
        loading_status.setText,
        "Status: loading, waiting for manual start",
        "状态：loading，等待手动开始演示",
    )
    loading_icon.statusChanged.connect(
        lambda value: show_loading(
            "Delayed icon status: {value}", "延迟图标状态：{value}", value=value
        )
    )
    loading_cell = make_cell(
        loading_icon,
        "mark_pending()\nblank first, shows home after 3 s",
        "mark_pending()\n先空白，3 秒后显示 home",
    )
    loading_cell.layout().addWidget(loading_status)
    loading_button = QPushButton()
    show_loading_button = bind_state(
        loading_button.setText, "Start 3-second delayed load", "开始 3 秒延迟加载"
    )
    loading_cell.layout().addWidget(loading_button)
    alias_grid.addWidget(loading_cell, 0, 2)
    static_pixmap = QLabel()
    static_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    static_pixmap.setPixmap(get_pixmap("demo:home", size=42, color="#bf8700"))
    static_cell = QWidget()
    static_layout = QVBoxLayout(static_cell)
    static_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    static_layout.addWidget(static_pixmap, alignment=Qt.AlignmentFlag.AlignHCenter)
    static_layout.addWidget(make_caption("get_pixmap()\nstatic QPixmap", "get_pixmap()\n静态 QPixmap"))
    alias_grid.addWidget(static_cell, 0, 3)
    root.addWidget(alias_section)

    advanced_section, advanced_grid = make_section(
        "Runtime updates, defaults, caches and interface checks",
        "运行时更新、默认值、缓存与接口自检",
        "These features don't always have a visual of their own, but you can trigger them "
        "here and see the result.",
        "这些能力不一定有独立图形，但可在窗口内触发并看到结果。",
    )
    refresh_button = QPushButton()
    bind(refresh_button.setText, "Replace registered icon data", "替换已注册图标数据")
    refresh_button.setIcon(get_icon("demo:mutable", size=22, color="#378add"))
    refresh_button.setIconSize(QSize(22, 22))
    qss_dynamic = IconWidget("demo:home", size=42, qss="qss-blue")
    qss_button = QPushButton()
    bind(qss_button.setText, "Toggle dynamic qss property", "切换动态 qss 属性")
    default_icon = IconWidget("demo:home")
    default_cell = make_cell(
        default_icon,
        "Global default size=24\narguments override defaults",
        "全局默认 size=24\n参数可覆盖默认",
    )
    check_result = QLabel()
    check_result.setWordWrap(True)
    check_result.setStyleSheet("color: palette(mid);")
    show_check = bind_state(
        check_result.setText, "Interface check: not run yet", "接口自检：尚未运行"
    )
    advanced_grid.addWidget(
        refresh_button, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter
    )
    advanced_grid.addWidget(qss_button, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
    advanced_grid.addWidget(
        make_cell(qss_dynamic, "Change qss at runtime\nre-polish", "运行中修改 qss\n重新 polish"), 0, 2
    )
    advanced_grid.addWidget(default_cell, 0, 3)
    advanced_grid.addWidget(check_result, 1, 0, 1, 4)
    root.addWidget(advanced_section)

    state = QLabel()
    state.setWordWrap(True)
    state.setStyleSheet("color: palette(mid);")
    show_state = bind_state(state.setText, "", "")
    root.addWidget(state)

    controls = QHBoxLayout()
    disabled_button = QPushButton()
    bind(disabled_button.setText, "Toggle QIcon button enabled state", "切换 QIcon 按钮禁用状态")
    check_button = QPushButton()
    bind(check_button.setText, "Run interface checks", "运行接口自检")
    controls.addWidget(disabled_button)
    controls.addWidget(check_button)
    controls.addStretch()
    root.addLayout(controls)

    def refresh_state() -> None:
        colors = ", ".join(get_icon_colors("demo:brand"))
        show_state(
            "Inspection: demo:brand is multicolor={multi}; fixed colors={colors}; "
            "button enabled={enabled}.",
            "检查信息：demo:brand 是多色图标={multi}；固定颜色={colors}；按钮已启用={enabled}。",
            multi=not is_monotone("demo:brand"),
            colors=colors,
            enabled=button.isEnabled(),
        )

    mutable_is_home = True
    qss_is_blue = True

    def complete_later() -> None:
        add_icon(
            "demo:later",
            IconData(
                '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>',
                24,
                24,
            ),
            replace=True,
        )
        show_loading(
            "Delayed icon status: ready, home shown",
            "延迟图标状态：ready，已显示 home",
        )
        loading_button.setEnabled(True)
        show_loading_button("Replay 3-second delayed load", "重新演示 3 秒延迟加载")

    def start_delayed_loading() -> None:
        mark_pending("demo:later")
        loading_icon.update()
        show_loading(
            "Status: loading, icon cleared, home registers in 3 s",
            "状态：loading，图标已清空，3 秒后注册 home",
        )
        loading_button.setEnabled(False)
        show_loading_button("Waiting 3 seconds…", "正在等待 3 秒…")
        QTimer.singleShot(3000, complete_later)

    def replace_registered_icon() -> None:
        nonlocal mutable_is_home
        body = (
            '<path d="M5 12h14M12 5v14" fill="none" stroke="currentColor" '
            'stroke-width="2.5" stroke-linecap="round"/>'
            if mutable_is_home
            else '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z" fill="currentColor"/>'
        )
        add_icon("demo:mutable", body, replace=True)
        mutable_is_home = not mutable_is_home
        refresh_button.update()
        show_check(
            "Replaced demo:mutable data; existing QIcons show the new shape after repainting.",
            "已替换 demo:mutable 数据；既有 QIcon 重新绘制后显示新图形。",
        )

    def toggle_dynamic_qss() -> None:
        nonlocal qss_is_blue
        qss_dynamic.setProperty("qss", "qss-green" if qss_is_blue else "qss-blue")
        style = qss_dynamic.style()
        style.unpolish(qss_dynamic)
        style.polish(qss_dynamic)
        qss_dynamic.update()
        qss_is_blue = not qss_is_blue
        show_check(
            "Changed the dynamic qss property and ran unpolish/polish.",
            "已修改动态 qss 属性并执行 unpolish/polish。",
        )

    def run_interface_checks() -> None:
        set_cache_limits(pixmap_mib=8, data_entries=200)
        set_disabled_opacity(0.35)
        defaults_before = get_default_config()
        set_default_config(size=30)
        new_default = IconWidget("demo:home")
        set_default_config(size=24)
        argb_matches = hex_argb("#80ff0000") == hex_rgba("#ff000080")
        invalid_color = False
        try:
            get_icon("demo:home", color="not-a-color")
        except IconifyError:
            invalid_color = True
        thread_result: list[bool] = []
        worker = threading.Thread(
            target=lambda: thread_result.append(_wrong_thread_raises())
        )
        worker.start()
        worker.join()
        data_thread: list[bool] = []
        registration_worker = threading.Thread(
            target=lambda: (
                add_icon(
                    "demo:background",
                    '<rect width="24" height="24" fill="currentColor"/>',
                ),
                data_thread.append(True),
            )
        )
        registration_worker.start()
        registration_worker.join()
        inline_icon = get_icon(
            IconData('<circle cx="12" cy="12" r="8" fill="#1a7f37"/>', 24, 24),
            size=18,
        )
        show_check(
            "Interface check passed: hex_argb equivalent={argb}; invalid color raises={invalid}; "
            "background Qt call={thread_en}; background data registration={data}; "
            "new default size={new_size}; old default size={old_size}; "
            "inline IconData={inline}; cache limits=8MiB/200 entries; "
            "disabled opacity=0.35. Original default size={original_size}.",
            "接口自检通过："
            "hex_argb 等价={argb}；非法颜色报错={invalid}；"
            "后台 Qt 调用={thread_zh}；后台注册数据={data}；"
            "新默认 size={new_size}；旧默认 size={old_size}；"
            "内联 IconData={inline}；缓存上限=8MiB/200 条；"
            "禁用透明度=0.35。原默认 size={original_size}。",
            argb=argb_matches,
            invalid=invalid_color,
            thread_en="WrongThreadError" if thread_result[0] else "failed",
            thread_zh="WrongThreadError" if thread_result[0] else "失败",
            data=data_thread == [True],
            new_size=new_default.sizeHint().width(),
            old_size=default_icon.sizeHint().width(),
            inline=not inline_icon.isNull(),
            original_size=defaults_before.size,
        )

    def _wrong_thread_raises() -> bool:
        try:
            get_icon("demo:home")
        except WrongThreadError:
            return True
        return False

    loading_button.clicked.connect(start_delayed_loading)
    refresh_button.clicked.connect(replace_registered_icon)
    qss_button.clicked.connect(toggle_dynamic_qss)
    check_button.clicked.connect(run_interface_checks)
    disabled_button.clicked.connect(
        lambda: (button.setEnabled(not button.isEnabled()), refresh_state())
    )
    add_controls(window, root)
    content.setStyleSheet(_extra_style(is_dark()))
    refresh_state()
    return window


def main() -> int:
    """运行演示窗口。"""
    app = make_app(sys.argv)
    register_icons()
    window = build_window()
    window.show()
    return run(app)


if __name__ == "__main__":
    raise SystemExit(main())
