"""渲染缓存键的失效正确性：任何影响画面的参数变化都必须换键并重渲染。"""

from __future__ import annotations

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QWidget

from pyside_iconify import add_collection, IconWidget


def _setup_collection() -> None:
    add_collection(
        {
            "prefix": "cache",
            "width": 24,
            "height": 24,
            "icons": {
                "sq": {"body": '<rect width="24" height="24" fill="currentColor"/>'},
                "ci": {"body": '<circle cx="12" cy="12" r="10" fill="currentColor"/>'},
            },
        },
        replace=True,
    )


def _center_color(widget: IconWidget) -> str:
    return widget.grab().toImage().pixelColor(16, 16).name()


def test_cache_key_invalidates_on_every_visual_change(qtbot: object) -> None:
    """穷举影响画面的参数变化：键必须变、渲染必须跟着变。"""
    _setup_collection()
    host = QWidget()
    host.resize(140, 60)
    qtbot.addWidget(host)
    host.move(400, 400)
    host.show()
    app = QApplication.instance()

    # 跟随主题的图标：主题切换必须换键并换渲染
    widget = IconWidget("cache:sq", size=32)
    widget.setParent(host)
    widget.move(0, 0)
    widget.show()
    app.processEvents()
    widget.grab()  # 强制同步渲染

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1d2128"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
    app.setPalette(palette)
    app.processEvents()
    key_dark = widget._key_cache
    color_dark = _center_color(widget)
    assert color_dark == "#e6edf3", color_dark

    palette.setColor(QPalette.ColorRole.Window, QColor("#f6f8fa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#20242b"))
    app.setPalette(palette)
    app.processEvents()
    assert widget._key_cache != key_dark, "主题切换未换键"
    assert _center_color(widget) == "#20242b"

    # 显式颜色变化：换键且渲染正确（取中心像素避开抗锯齿边缘）
    widget.setColor("#ff0000")
    app.processEvents()
    widget.grab()
    assert widget._key_cache, "键未生成"
    assert _center_color(widget) == "#ff0000", "显式颜色变化渲染错误"

    # 数据源变化：换键且渲染形状改变
    key_before = widget._key_cache
    widget.setIcon("cache:ci")
    app.processEvents()
    widget.grab()
    assert widget._key_cache != key_before, "数据源变化未换键"

    # 尺寸 / 旋转 / 禁用：逐一换键
    key_before = widget._key_cache
    widget.setSize(40)
    app.processEvents()
    widget.grab()
    assert widget._key_cache != key_before, "尺寸变化未换键"

    key_before = widget._key_cache
    widget.setRotation(45)
    app.processEvents()
    widget.grab()
    assert widget._key_cache != key_before, "旋转变化未换键"

    key_before = widget._key_cache
    widget.setEnabled(False)
    app.processEvents()
    widget.grab()
    assert widget._key_cache != key_before, "禁用变化未换键"


def test_cache_key_ignores_theme_for_explicit_color(qtbot: object) -> None:
    """显式颜色不受主题切换影响：键与渲染都保持不变。"""
    _setup_collection()
    host = QWidget()
    host.resize(80, 60)
    qtbot.addWidget(host)
    host.move(400, 400)
    host.show()
    app = QApplication.instance()

    widget = IconWidget("cache:sq", size=32, color="#00ff00")
    widget.setParent(host)
    widget.move(0, 0)
    widget.show()
    app.processEvents()
    widget.grab()
    key_before = widget._key_cache

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1d2128"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
    app.setPalette(palette)
    app.processEvents()
    assert widget._key_cache == key_before, "显式颜色不应因主题切换换键"
    assert _center_color(widget) == "#00ff00"
