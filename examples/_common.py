"""Controls shared by every example: theme toggle and language toggle."""

from __future__ import annotations

from _qt import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from _i18n import bind, toggle_language
from _theme import is_dark, set_theme


def add_controls(window: QWidget, layout: QVBoxLayout, *, dark: bool = False) -> None:
    """在布局末尾加一行“切换主题 / 切换语言”按钮，并应用初始主题。

    Args:
        window: 示例窗口，主题样式表应用在它身上。
        layout: 要追加按钮行的布局。
        dark: 初始是否为暗色主题。
    """
    row = QHBoxLayout()
    theme_button = QPushButton()
    language_button = QPushButton()
    bind(theme_button.setText, "Toggle light/dark theme", "切换亮暗主题")
    bind(language_button.setText, "中文 / English", "中文 / English")
    theme_button.clicked.connect(lambda: set_theme(window, not is_dark()))
    language_button.clicked.connect(toggle_language)
    row.addWidget(theme_button)
    row.addWidget(language_button)
    layout.addLayout(row)
    set_theme(window, dark)
