"""Qt names for the examples: they run on whichever binding is installed.

Every example imports Qt from here (``from _qt import QPushButton``) instead of
naming a binding, so the same file runs on PySide6, PyQt6, PyQt5 and PySide2.
In your own application just import your binding directly, as in the README.

Pick a binding when several are installed with the PYSIDE_ICONIFY_QT_API
environment variable (pyside6, pyqt6, pyqt5, pyside2).
"""

from __future__ import annotations

from collections.abc import Sequence

from pyside_iconify import _qt

_SEARCH = (_qt.QtCore, _qt.QtGui, _qt.QtWidgets, _qt.QtNetwork, _qt.QtSvg)


def __getattr__(name: str) -> object:
    """按名字在垫片和各 Qt 子模块里找 Qt 类，供 ``from _qt import X`` 使用。

    Args:
        name: Qt 类或函数的名字，如 "QPushButton"

    Returns:
        对应的对象。

    Raises:
        AttributeError: 当前绑定里没有这个名字。
    """
    if not name.startswith("_") and hasattr(_qt, name):
        return getattr(_qt, name)
    for module in _SEARCH:
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"{_qt.BINDING} has no Qt name {name!r}")


def make_app(argv: Sequence[str]) -> object:
    """创建 QApplication。Qt5 下先打开高分屏位图属性，图标才不会糊。

    Args:
        argv: 命令行参数，通常是 sys.argv

    Returns:
        QApplication 实例。
    """
    core = _qt.QtCore
    if _qt.IS_QT5:
        core.QCoreApplication.setAttribute(core.Qt.AA_EnableHighDpiScaling, True)
        core.QCoreApplication.setAttribute(core.Qt.AA_UseHighDpiPixmaps, True)
    return _qt.QtWidgets.QApplication(list(argv))


def run(app: object) -> int:
    """进入事件循环。PySide2 里叫 exec_，其余叫 exec。

    Args:
        app: make_app() 返回的应用对象

    Returns:
        进程退出码。
    """
    runner = getattr(app, "exec", None) or getattr(app, "exec_")
    return int(runner())
