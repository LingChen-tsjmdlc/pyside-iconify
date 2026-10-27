"""Qt 绑定选择层：全库唯一允许导入具体 Qt 绑定的地方。

其余模块一律写 ``from pyside_iconify._qt import QWidget, ...``，不关心背后是
PySide6、PyQt6、PyQt5 还是 PySide2。本模块在第一次被导入时选定绑定，并抹平各绑定
之间的小差别（信号名、QAction 所在模块），之后整个进程里不再改变。

选择顺序，哪一步有答案就停：

1. 环境变量 ``PYSIDE_ICONIFY_QT_API``（pyside6 / pyqt6 / pyqt5 / pyside2）。
2. 进程里已经导入过的绑定：库是用户程序的一个零件，应当跟着主程序走。
3. 都没有时，依次尝试 PySide6、PyQt6、PyQt5、PySide2，取第一个装了的。

同一个进程里混用两个绑定会让 Qt 崩溃，所以发现这种情况直接报错，不替用户猜。
"""

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType

ENV_VAR = "PYSIDE_ICONIFY_QT_API"

# 按优先级排列；名字就是绑定的顶层包名
_BINDINGS = ("PySide6", "PyQt6", "PyQt5", "PySide2")
_BY_LOWER = {name.lower(): name for name in _BINDINGS}

_INSTALL_HINT = (
    "install one, e.g. pip install \"pyside-iconify[pyside6]\" "
    "(or [pyqt6], [pyqt5], [pyside2])"
)


def _imported_bindings() -> list[str]:
    """返回进程里已经导入了 QtCore 的绑定。

    只认 ``<绑定>.QtCore`` 而不是顶层包：顶层包可能只是被某个工具探测性地导入过，
    QtCore 被导入才说明程序真的在用它。

    Returns:
        已导入的绑定名，顺序同 _BINDINGS。
    """
    return [name for name in _BINDINGS if f"{name}.QtCore" in sys.modules]


def _select() -> str:
    """按文档里的三步规则选定要使用的绑定。

    Returns:
        绑定的顶层包名，如 "PyQt6"。

    Raises:
        ImportError: 环境变量写错、与已导入的绑定冲突、同时导入了多个绑定，
            或者一个绑定都没装。
    """
    requested = os.environ.get(ENV_VAR, "").strip()
    loaded = _imported_bindings()
    if requested:
        name = _BY_LOWER.get(requested.lower())
        if name is None:
            raise ImportError(
                f"{ENV_VAR}={requested!r} is not supported; "
                f"use one of: {', '.join(_BY_LOWER)}"
            )
        others = [other for other in loaded if other != name]
        if others:
            raise ImportError(
                f"{ENV_VAR}={requested!r} conflicts with {others[0]}, which this "
                "process has already imported; Qt bindings cannot be mixed"
            )
        return name
    if len(loaded) > 1:
        raise ImportError(
            f"more than one Qt binding is imported ({', '.join(loaded)}); "
            f"mixing them crashes Qt. Use one, or set {ENV_VAR} to choose"
        )
    if loaded:
        return loaded[0]
    failures: list[str] = []
    for name in _BINDINGS:
        try:
            importlib.import_module(f"{name}.QtCore")
        except ImportError as error:
            failures.append(f"{name}: {error}")
            continue
        return name
    raise ImportError(
        "no Qt binding found; " + _INSTALL_HINT + ". Tried: " + "; ".join(failures)
    )


BINDING: str = _select()
"""选定的绑定名，如 "PySide6"。"""

IS_QT5: bool = BINDING in ("PyQt5", "PySide2")
"""是否 Qt5 系（PyQt5、PySide2）；Qt5 与 Qt6 在高分屏图标路径上不同。"""


def _load(module: str) -> ModuleType:
    """导入选定绑定下的一个子模块。

    Args:
        module: 子模块名，如 "QtGui"

    Returns:
        导入后的模块对象。
    """
    return importlib.import_module(f"{BINDING}.{module}")


QtCore = _load("QtCore")
QtGui = _load("QtGui")
QtWidgets = _load("QtWidgets")
QtNetwork = _load("QtNetwork")
QtSvg = _load("QtSvg")

# 各子模块里本库用到的名字；写在这里一次，_qt.pyi 与垫片共用同一份清单
_CORE = (
    "QByteArray",
    "QCoreApplication",
    "QEvent",
    "QEventLoop",
    "QObject",
    "QRectF",
    "QSize",
    "QStandardPaths",
    "QThread",
    "QTimer",
    "QUrl",
    "Qt",
)
_GUI = (
    "QColor",
    "QFontMetrics",
    "QIcon",
    "QIconEngine",
    "QImage",
    "QPainter",
    "QPaintEvent",
    "QPalette",
    "QPen",
    "QPixmap",
    "QStandardItem",
)
_WIDGETS = (
    "QAbstractButton",
    "QApplication",
    "QListWidgetItem",
    "QSizePolicy",
    "QStyle",
    "QStyleOption",
    "QTabWidget",
    "QTreeWidgetItem",
    "QWidget",
)
_NETWORK = ("QNetworkAccessManager", "QNetworkReply", "QNetworkRequest")
_SVG = ("QSvgRenderer",)

for _module, _names in (
    (QtCore, _CORE),
    (QtGui, _GUI),
    (QtWidgets, _WIDGETS),
    (QtNetwork, _NETWORK),
    (QtSvg, _SVG),
):
    for _name in _names:
        globals()[_name] = getattr(_module, _name)

# PyQt 把信号叫 pyqtSignal，PySide 叫 Signal；统一成 Signal
Signal = getattr(QtCore, "Signal", None) or getattr(QtCore, "pyqtSignal")

# QAction 在 Qt6 属于 QtGui，在 Qt5 属于 QtWidgets
QAction = getattr(QtGui, "QAction", None) or getattr(QtWidgets, "QAction")


def _qt_version() -> tuple[int, int]:
    """返回运行时 Qt 的 (主版本, 次版本)。

    Returns:
        形如 (6, 8) 的元组；读不到时按 (0, 0) 处理。
    """
    try:
        major, minor = QtCore.qVersion().split(".")[:2]
        return int(major), int(minor)
    except (ValueError, AttributeError):
        return (0, 0)


QT_VERSION: tuple[int, int] = _qt_version()
"""运行时 Qt 的 (主版本, 次版本)。"""

SCALED_PIXMAP_GETS_PHYSICAL_SIZE: bool = QT_VERSION < (6, 8)
"""``QIconEngine.scaledPixmap`` 收到的 size 是否已经乘过缩放比。

Qt 官方文档（QIcon::pixmap 的说明）写明：6.8 之前这个调用错误地把设备相关的
像素尺寸传给 scaledPixmap，6.8 起才传设备无关的逻辑尺寸。Qt5 不走 scaledPixmap，
这个值对它没有意义。
"""


def run_event_loop(loop: QEventLoop) -> None:
    """运行一个事件循环直到它被退出。

    Qt6 与 PyQt5 里叫 ``exec()``；PySide2 只有 ``exec_()``（Python 2 时代 exec 是关键字，
    老绑定用了带下划线的名字）。

    Args:
        loop: 要运行的 QEventLoop
    """
    runner = getattr(loop, "exec", None) or getattr(loop, "exec_")
    runner()


__all__ = [
    "BINDING",
    "ENV_VAR",
    "IS_QT5",
    "QT_VERSION",
    "SCALED_PIXMAP_GETS_PHYSICAL_SIZE",
    "QAction",
    "Signal",
    "run_event_loop",
    "QtCore",
    "QtGui",
    "QtNetwork",
    "QtSvg",
    "QtWidgets",
    *_CORE,
    *_GUI,
    *_WIDGETS,
    *_NETWORK,
    *_SVG,
]
