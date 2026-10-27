"""测试用的 Qt 名字入口：跟随被测库选中的绑定。

测试里写 ``from tests.qt import QPushButton``，不直接写 ``from PySide6...``，
这样同一份测试可以在 PySide6、PyQt6、PyQt5、PySide2 下原样运行。

只服务测试，所以放在 tests/ 而不是库里：库自己的垫片只列库用到的那几十个名字。
"""

from __future__ import annotations

from types import ModuleType

from pyside_iconify import _qt

BINDING: str = _qt.BINDING
IS_QT5: bool = _qt.IS_QT5

_SEARCH: tuple[ModuleType, ...] = (
    _qt.QtCore,
    _qt.QtGui,
    _qt.QtWidgets,
    _qt.QtNetwork,
    _qt.QtSvg,
)


def __getattr__(name: str) -> object:
    """按名字在库垫片和各 Qt 子模块里找，找不到就像普通模块一样报错。

    Args:
        name: Qt 类或函数的名字，如 "QPushButton"

    Returns:
        对应的对象。

    Raises:
        AttributeError: 垫片和所有子模块里都没有这个名字。
    """
    # 先看库垫片：Signal、QAction 在各绑定里的位置不同，只有垫片处理过
    if hasattr(_qt, name) and not name.startswith("_"):
        return getattr(_qt, name)
    for module in _SEARCH:
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"{BINDING} has no Qt name {name!r}")
