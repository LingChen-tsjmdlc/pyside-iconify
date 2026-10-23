"""Shared English/Chinese text switching for the examples.

Every visible string is written as an (English, Chinese) pair. ``bind`` applies
it now and re-applies it whenever the language changes; ``t`` returns the text
for the current language, for strings built at runtime.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QLocale

_language = "zh" if QLocale.system().language() == QLocale.Language.Chinese else "en"
_listeners: list[Callable[[], None]] = []


def language() -> str:
    """返回当前语言代码："en" 或 "zh"。"""
    return _language


def t(en: str, zh: str, **fields: object) -> str:
    """返回当前语言的文本，并用 fields 填充其中的 {占位符}。

    Args:
        en: 英文文本。
        zh: 中文文本。
        **fields: 格式化字段。
    """
    text = zh if _language == "zh" else en
    return text.format(**fields) if fields else text


def on_change(callback: Callable[[], None], *, call_now: bool = True) -> None:
    """登记语言变化回调，用于刷新由状态拼出来的文本。

    Args:
        callback: 无参回调，在其中重新设置文本。
        call_now: 是否登记后立即调用一次。
    """
    _listeners.append(callback)
    if call_now:
        callback()


def bind(setter: Callable[[str], object], en: str, zh: str, **fields: object) -> None:
    """把一对文本绑定到设置函数，语言切换时自动更新。

    Args:
        setter: 接收字符串的设置函数，如 label.setText。
        en: 英文文本。
        zh: 中文文本。
        **fields: 格式化字段。
    """
    on_change(lambda: setter(t(en, zh, **fields)))


def set_language(code: str) -> None:
    """切换语言并通知所有已登记的回调。

    Args:
        code: "en" 或 "zh"。
    """
    global _language
    if code not in {"en", "zh"}:
        raise ValueError(f"unsupported language: {code!r}")
    _language = code
    for callback in list(_listeners):
        callback()


def toggle_language() -> None:
    """在英文和中文之间切换。"""
    set_language("en" if _language == "zh" else "zh")
