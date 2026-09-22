"""set_icon、悬停/选中与引擎 paint 路径测试。"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from pyside_iconify import (
    IconWidget,
    add_collection,
    get_icon,
    register_icon_target,
    set_icon,
)
from pyside_iconify._errors import UnsupportedTargetError
from tests.helpers import show_widget

SQ = '<rect width="24" height="24" fill="currentColor"/>'
BG = QColor("#efefef")


def _collection() -> None:
    add_collection(
        {"prefix": "intg", "width": 24, "height": 24, "icons": {"sq": {"body": SQ}}}
    )


def test_set_icon_targets(qtbot: object) -> None:
    _collection()
    button = QPushButton()
    set_icon(button, "intg:sq", size=16, color="#ff0000")
    assert not button.icon().isNull()
    action = QAction("a")
    set_icon(action, "intg:sq")
    assert not action.icon().isNull()
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "t")
    set_icon(tabs, "intg:sq", 0)
    assert not tabs.tabIcon(0).isNull()
    list_item = QListWidgetItem()
    set_icon(list_item, "intg:sq")
    assert not list_item.icon().isNull()
    tree = QTreeWidget()
    node = QTreeWidgetItem(tree, ["n"])
    set_icon(node, "intg:sq")
    assert not node.icon(0).isNull()
    window = QWidget()
    set_icon(window, "intg:sq")
    assert not window.windowIcon().isNull()


def test_set_icon_rejects_unknown_target(qtbot: object) -> None:
    _collection()
    try:
        set_icon(object(), "intg:sq")
    except UnsupportedTargetError:
        return
    raise AssertionError("should raise UnsupportedTargetError")


def test_register_icon_target_custom(qtbot: object) -> None:
    _collection()

    class Custom:
        def __init__(self) -> None:
            self.icon: QIcon | None = None

    register_icon_target(Custom, lambda target, icon: setattr(target, "icon", icon))
    custom = Custom()
    set_icon(custom, "intg:sq")
    assert custom.icon is not None and not custom.icon.isNull()


def test_hover_without_params_no_effect(qtbot: object) -> None:
    """不写 hover/selected 参数时，Active/Selected 与 Normal 完全一致。"""
    _collection()
    icon = get_icon("intg:sq", size=24, color="#808080")
    normal = icon.pixmap(QSize(24, 24), QIcon.Mode.Normal).toImage()
    active = icon.pixmap(QSize(24, 24), QIcon.Mode.Active).toImage()
    selected = icon.pixmap(QSize(24, 24), QIcon.Mode.Selected).toImage()
    assert active.pixelColor(12, 12).name() == "#808080"
    assert selected.pixelColor(12, 12).name() == "#808080"


def test_set_icon_button_without_hover_no_watcher(qtbot: object) -> None:
    """set_icon 不写 hover_color 时，按钮不带悬停 watcher。"""
    _collection()
    button = QPushButton()
    set_icon(button, "intg:sq", size=16, color="#ff0000")
    assert not button.children() or all(
        type(child).__name__ != "_ButtonHoverWatcher"
        for child in button.children()
    )


def test_set_icon_button_with_hover_installs_watcher(qtbot: object) -> None:
    """set_icon 写 hover_color 时，按钮安装悬停 watcher 且双图标状态正确。"""
    _collection()
    button = QPushButton()
    set_icon(button, "intg:sq", size=16, color="#ff0000", hover_color="#0000ff")
    watchers = [
        child for child in button.children()
        if type(child).__name__ == "_ButtonHoverWatcher"
    ]
    assert watchers, "hover_color 参数应安装悬停 watcher"
    active = button.icon().pixmap(QSize(16, 16), QIcon.Mode.Active).toImage()
    # normal 引擎无视 Active 请求，永远是常态色
    assert active.pixelColor(8, 8).name() == "#ff0000"


def test_hover_mode_explicit_color(qtbot: object) -> None:
    """hover 引擎（state_mode=hover）无视请求 mode，永远用悬停色。"""
    from pyside_iconify.core.types import IconName
    from pyside_iconify.rendering.engine import IconEngine
    from pyside_iconify.rendering.options import make_options

    _collection()
    options = make_options(size=24, color="#ff0000", hover_color="#0000ff")
    engine = IconEngine(IconName("intg", "sq"), options, state_mode="hover")
    active = engine.pixmap(QSize(24, 24), QIcon.Mode.Active, QIcon.State.Off).toImage()
    assert active.pixelColor(12, 12).name() == "#0000ff"
    normal_request = engine.pixmap(
        QSize(24, 24), QIcon.Mode.Normal, QIcon.State.Off
    ).toImage()
    assert normal_request.pixelColor(12, 12).name() == "#0000ff"


def test_hover_modes_cache_separated(qtbot: object) -> None:
    """QIcon 按 (key, mode) 缓存，Normal/Active 必须各归各位不串色。"""
    from pyside_iconify.core.types import IconName
    from pyside_iconify.rendering.engine import IconEngine
    from pyside_iconify.rendering.options import make_options

    _collection()
    options = make_options(size=24, color="#808080", hover_color="#0000ff")
    normal_icon = QIcon(IconEngine(IconName("intg", "sq"), options, state_mode="normal"))
    hovered_icon = QIcon(IconEngine(IconName("intg", "sq"), options, state_mode="hover"))
    for _ in range(2):
        normal = normal_icon.pixmap(QSize(24, 24), QIcon.Mode.Active).toImage()
        hovered = hovered_icon.pixmap(QSize(24, 24), QIcon.Mode.Normal).toImage()
        assert normal.pixelColor(12, 12).name() == "#808080"
        assert hovered.pixelColor(12, 12).name() == "#0000ff"


def test_engine_key_contains_state_colors(qtbot: object) -> None:
    """hover 配置不同的两个 icon，引擎 key 必须不同（QIcon 缓存隔离）。"""
    from pyside_iconify.core.types import IconName
    from pyside_iconify.rendering.engine import IconEngine
    from pyside_iconify.rendering.options import make_options

    _collection()
    plain = make_options(size=24, color="#808080")
    hovered = make_options(size=24, color="#808080", hover_color="#0000ff")
    key_plain = IconEngine(IconName("intg", "sq"), plain).key()
    key_hovered = IconEngine(IconName("intg", "sq"), hovered).key()
    assert key_plain != key_hovered


def test_selected_mode_color(qtbot: object) -> None:
    _collection()
    icon = get_icon("intg:sq", size=24, selected_color="#00ff00")
    selected = icon.pixmap(QSize(24, 24), QIcon.Mode.Selected).toImage()
    assert selected.pixelColor(12, 12).name() == "#00ff00"


def test_hover_does_not_affect_disabled(qtbot: object) -> None:
    """带悬停参数的按钮，禁用后图标变淡且不显示悬停色。"""
    from PySide6.QtWidgets import QApplication

    _collection()
    set_icon(button := QPushButton(), "intg:sq", size=24, color="#ff0000", hover_color="#0000ff")
    qtbot.addWidget(button)
    button.setEnabled(False)
    button.resize(60, 40)
    button.show()
    QApplication.processEvents()
    disabled = button.icon().pixmap(QSize(24, 24), QIcon.Mode.Disabled).toImage()
    color = disabled.pixelColor(12, 12)
    # 禁用态：红色 + 透明度变淡，不是 hover 蓝色
    assert color.name() == "#ff0000"
    assert color.alpha() < 255


def test_widget_hover_changes_color(qtbot: object) -> None:
    _collection()
    widget = show_widget(
        qtbot,
        IconWidget("intg:sq", size=24, color="#808080", hover_color="#0000ff"),
        24,
        24,
    )
    QApplication.processEvents()
    # show_widget 已把窗口移出鼠标位置，处于非悬停态。
    normal = widget.grab().toImage().pixelColor(12, 12)
    assert normal.name() == "#808080", normal.name()
    widget._hovering = True
    widget.update()
    QApplication.processEvents()
    hovered = widget.grab().toImage().pixelColor(12, 12)
    assert hovered.name() == "#0000ff", hovered.name()


def test_item_view_paints_engine_paint_path(qtbot: object) -> None:
    """QListWidget 走 QIcon.paint()（引擎 paint 虚函数）绘制不崩溃。"""
    _collection()
    list_widget = QListWidget()
    for row in range(5):
        item = QListWidgetItem(f"行 {row}")
        item.setIcon(get_icon("intg:sq", size=16, color="#d1242f"))
        list_widget.addItem(item)
    show_widget(qtbot, list_widget, 200, 160)
    image = list_widget.grab().toImage()
    points = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 60 and image.pixelColor(x, y) != BG
    ]
    assert points, "icons not painted in item view"
