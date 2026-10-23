"""set_icon 统一入口与自定义目标注册。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction, QIcon, QStandardItem
from PySide6.QtWidgets import (
    QAbstractButton,
    QListWidgetItem,
    QTabWidget,
    QTreeWidgetItem,
    QWidget,
)

from pyside_iconify._errors import UnsupportedTargetError
from pyside_iconify._api import get_icon
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.rendering.engine import IconEngine
from pyside_iconify.rendering.options import make_options

IconApplier: TypeAlias = Callable[..., None]


class _ButtonHoverWatcher(QObject):
    """事件驱动的按钮悬停换图。

    按钮样式对图标永远请求 QIcon.Active（与悬停无关），
    所以按钮的 hover 效果只能靠 Enter/Leave 时主动切换图标实现。
    watcher 以按钮为父对象，按钮销毁时随之销毁。
    """

    def __init__(
        self, button: QAbstractButton, normal: QIcon, hovered: QIcon
    ) -> None:
        """创建悬停监听器并安装到按钮上。

        Args:
            button: 被监听的按钮，同时作为监听器的父对象
            normal: 鼠标离开时显示的图标
            hovered: 鼠标进入时显示的图标
        """
        super().__init__(button)
        self._normal = normal
        self._hovered = hovered
        button.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """在 Enter/Leave 事件时切换按钮图标。

        Args:
            watched: 被监听的对象，即按钮
            event: 收到的事件；Enter 切换为悬停图标，Leave 切换为常态图标

        Returns:
            始终为 False，不拦截事件。
        """
        if event.type() == QEvent.Type.Enter:
            watched.setIcon(self._hovered)  # type: ignore[attr-defined]
        elif event.type() == QEvent.Type.Leave:
            watched.setIcon(self._normal)  # type: ignore[attr-defined]
        return False


def _apply_button(target: QAbstractButton, icon: QIcon, hovered: QIcon) -> None:
    """给按钮设置图标并安装悬停换图监听。

    Args:
        target: 目标按钮
        icon: 常态图标
        hovered: 悬停时显示的图标
    """
    target.setIcon(icon)
    _ButtonHoverWatcher(target, icon, hovered)


def _apply_action(target: QAction, icon: QIcon) -> None:
    """给 QAction 设置图标。

    Args:
        target: 目标动作
        icon: 要设置的图标
    """
    target.setIcon(icon)


def _apply_tab(target: QTabWidget, icon: QIcon, index: int) -> None:
    """给 QTabWidget 的指定页设置图标。

    Args:
        target: 目标标签页控件
        icon: 要设置的图标
        index: 页索引
    """
    target.setTabIcon(index, icon)


def _apply_list_item(target: QListWidgetItem, icon: QIcon) -> None:
    """给列表项设置图标。

    Args:
        target: 目标列表项
        icon: 要设置的图标
    """
    target.setIcon(icon)


def _apply_tree_item(target: QTreeWidgetItem, icon: QIcon, column: int = 0) -> None:
    """给树节点的指定列设置图标。

    Args:
        target: 目标树节点
        icon: 要设置的图标
        column: 列号，默认 0
    """
    target.setIcon(column, icon)


def _apply_standard_item(target: QStandardItem, icon: QIcon) -> None:
    """给 QStandardItem 设置图标。

    Args:
        target: 目标标准项
        icon: 要设置的图标
    """
    target.setIcon(icon)


def _apply_window(target: QWidget, icon: QIcon) -> None:
    """给窗口设置窗口图标。

    Args:
        target: 目标窗口控件
        icon: 要设置的图标
    """
    target.setWindowIcon(icon)


_ADAPTERS: dict[type, IconApplier] = {
    QAbstractButton: _apply_button,
    QAction: _apply_action,
    QTabWidget: _apply_tab,
    QListWidgetItem: _apply_list_item,
    QTreeWidgetItem: _apply_tree_item,
    QStandardItem: _apply_standard_item,
    QWidget: _apply_window,
}


def register_icon_target(target_type: type, applier: IconApplier) -> None:
    """注册自定义目标类型的图标适配器。

    同一类型重复注册会覆盖旧适配器。

    Args:
        target_type: 目标类型；必须是类
        applier: 适配器；签名为 (target, icon, *args)，args 来自 set_icon 的透传参数
    """
    if not isinstance(target_type, type):
        raise TypeError("target_type must be a type")
    if not callable(applier):
        raise TypeError("applier must be callable")
    _ADAPTERS[target_type] = applier


def set_icon(target: object, icon: str, *args: object, **options: object) -> QIcon:
    """给任意受支持的 Qt 目标设置图标。

    悬停效果是显式启用的：只有传了 hover_color /
    hover_color_light_theme / hover_color_dark_theme 之一，
    按钮才有悬停变色；不写就没有任何 hover 效果。

    Args:
        target: 目标对象；按类型的 MRO 查找已注册的适配器
        icon: 图标名称
        *args: 透传给适配器的额外参数，例如 QTabWidget 的页索引、item 的列号
        **options: 渲染选项，与 get_icon 的关键字参数一致

    Returns:
        设置到目标上的 QIcon；按钮启用悬停时返回常规图标，实际安装的是常态/悬停两个图标。

    Raises:
        UnsupportedTargetError: 目标类型没有已注册的适配器。
    """
    hover_only = {
        key: options.pop(key)
        for key in ("hover_color", "hover_color_light_theme", "hover_color_dark_theme")
        if key in options
    }
    qicon = get_icon(icon, **options)
    applier = _find_applier(type(target))
    if applier is None:
        raise UnsupportedTargetError(f"unsupported icon target: {type(target).__name__}")
    if isinstance(target, QAbstractButton):
        if any(hover_only.values()):
            name = parse_icon_name(icon)
            render_options = make_options(**options, **hover_only)
            normal = QIcon(IconEngine(name, render_options, state_mode="normal"))
            hovered = QIcon(IconEngine(name, render_options, state_mode="hover"))
            applier(target, normal, hovered)
        else:
            target.setIcon(qicon)
        return qicon
    applier(target, qicon, *args)
    return qicon


def _find_applier(target_type: type) -> IconApplier | None:
    """沿 MRO 查找目标类型对应的适配器。

    Args:
        target_type: 目标对象的类型

    Returns:
        第一个已注册的适配器，找不到时为 None。
    """
    for klass in target_type.__mro__:
        if klass in _ADAPTERS:
            return _ADAPTERS[klass]
    return None
