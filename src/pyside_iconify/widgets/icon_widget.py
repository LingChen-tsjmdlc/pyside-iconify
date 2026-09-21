"""图标控件。"""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPalette, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QStyle, QStyleOption, QWidget

from pyside_iconify._config import get_default_config
from pyside_iconify._errors import (
    IconNotFoundError,
    InvalidIconNameError,
    UnsupportedSvgError,
)
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.registry import registry
from pyside_iconify.core.types import IconData, RGBA
from pyside_iconify.network import client as _network
from pyside_iconify.rendering.engine import IconOptions
from pyside_iconify.rendering.options import make_options
from pyside_iconify.rendering.placeholder import create_blank, create_placeholder
from pyside_iconify.rendering.qt_adapter import (
    ColorValue,
    normalize_color,
    require_application,
    require_main_thread,
)
from pyside_iconify.rendering.renderer import render_pixmap
from pyside_iconify.widgets.animation import get_spin_clock

_UNSET = object()


class IconWidget(QWidget):
    """可放入任意 Qt 布局的图标控件。"""

    loaded = Signal(str)
    failed = Signal(str, object)
    statusChanged = Signal(str)

    def __init__(
        self,
        icon: str | IconData,
        *,
        size: object | None = None,
        color: ColorValue | None = None,
        light_color: ColorValue | None = None,
        dark_color: ColorValue | None = None,
        opacity: float | None = None,
        width: object | None = None,
        height: object | None = None,
        rotate: float = 0,
        spin: bool = False,
        spin_period: float | None = None,
        h_flip: bool = False,
        v_flip: bool = False,
        qss: str | None = None,
        fallback: str | None | object = _UNSET,
        parent: QWidget | None = None,
    ) -> None:
        require_application()
        require_main_thread()
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._name = (
            registry.register_inline(icon)
            if isinstance(icon, IconData)
            else parse_icon_name(icon)
        )
        self._options = make_options(
            size=size,
            color=color,
            light_color=light_color,
            dark_color=dark_color,
            opacity=opacity,
            width=width,
            height=height,
            spin=spin,
            spin_period=spin_period,
            rotate=rotate,
            h_flip=h_flip,
            v_flip=v_flip,
        )
        self._width_override = width
        self._height_override = height
        self._spin = spin
        self._spin_period = self._options.spin_period
        self._fallback = (
            get_default_config().fallback if fallback is _UNSET else fallback
        )
        self._blank_on_failure = fallback is None
        self._status = "empty"
        self._reported_failure = False
        self._repolishing = False
        self._loading_timer: QTimer | None = None
        if qss:
            self.setProperty("qss", qss)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        require_application().installEventFilter(self)
        if spin:
            get_spin_clock().add(self)
        # 构造即预触发加载，不等首次绘制。
        if not registry.contains(self._name) and not registry.is_pending(self._name):
            _network.default_client().ensure_loaded(self._name)
        self._update_status()

    def iconName(self) -> str:
        """返回当前图标名。"""
        return str(self._name)

    def setIcon(self, icon: str) -> None:
        """更换图标名。"""
        require_main_thread()
        self._name = parse_icon_name(icon)
        self._reported_failure = False
        self._update_status()
        self.update()

    def setSize(self, value: object) -> None:
        """设置图标尺寸。"""
        require_main_thread()
        self._options = make_options(
            size=value,
            color=self._options.color,
            light_color=self._options.light_color,
            dark_color=self._options.dark_color,
            opacity=self._options.opacity,
            disabled_opacity=self._options.disabled_opacity,
            spin=self._options.spin,
            spin_period=self._options.spin_period,
            rotate=self._options.rotate,
            h_flip=self._options.h_flip,
            v_flip=self._options.v_flip,
        )
        self.updateGeometry()
        self.update()

    def setColor(self, value: ColorValue | None) -> None:
        """设置默认颜色。"""
        self._replace_options(color=value)

    def setLightColor(self, value: ColorValue | None) -> None:
        """设置亮色主题颜色。"""
        self._replace_options(light_color=value)

    def setDarkColor(self, value: ColorValue | None) -> None:
        """设置暗色主题颜色。"""
        self._replace_options(dark_color=value)

    def setOpacity(self, value: float) -> None:
        """设置整体透明度。"""
        self._replace_options(opacity=value)

    def setRotation(self, value: float) -> None:
        """设置旋转角度。"""
        self._replace_options(rotate=value)

    def setSpin(self, enabled: bool) -> None:
        """启用或停止旋转动画。"""
        require_main_thread()
        self._spin = enabled
        clock = get_spin_clock()
        if enabled:
            clock.add(self)
        else:
            clock.remove(self)
        self.update()

    def setFlips(self, horizontal: bool, vertical: bool) -> None:
        """设置水平和垂直翻转。"""
        self._replace_options(h_flip=horizontal, v_flip=vertical)

    def sizeHint(self) -> QSize:
        """返回图标的逻辑尺寸建议。"""
        width, height = self._logical_size()
        return QSize(round(width), round(height))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event)
        if self._spin:
            get_spin_clock().sync()

    def hideEvent(self, event: QEvent) -> None:
        super().hideEvent(event)
        if self._spin:
            get_spin_clock().sync()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.ThemeChange,
        }:
            self._repolish()
            self.updateGeometry()
            self.update()
        return super().eventFilter(watched, event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.StyleChange,
        }:
            self._repolish()
        if event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.FontChange,
            QEvent.Type.EnabledChange,
            QEvent.Type.StyleChange,
        }:
            self.updateGeometry()
            self.update()

    def _repolish(self) -> None:
        if self._repolishing:
            return
        self._repolishing = True
        try:
            if not self.palette().resolveMask():
                self.setPalette(QPalette())
            style = self.style()
            style.unpolish(self)
            style.polish(self)
        finally:
            self._repolishing = False

    def paintEvent(self, event: QPaintEvent) -> None:
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, option, painter, self
        )
        pixmap = self._pixmap(option)
        # 居中按位图原尺寸绘制，控件被布局挤压时也不拉伸变形。
        rect = self.contentsRect()
        source = QRectF(pixmap.rect())
        ratio = pixmap.devicePixelRatio() or 1.0
        target = QRectF(
            rect.x() + (rect.width() - source.width() / ratio) / 2.0,
            rect.y() + (rect.height() - source.height() / ratio) / 2.0,
            source.width() / ratio,
            source.height() / ratio,
        )
        painter.drawPixmap(target, pixmap, source)
        painter.end()

    def _pixmap(self, option: QStyleOption):
        logical_width, logical_height = self._logical_size()
        width = max(1.0, logical_width)
        height = max(1.0, logical_height)
        dpr = self.devicePixelRatioF()
        render_name = self._name
        if registry.is_pending(render_name):
            self._set_status("loading")
            self._start_loading_timer()
            return create_blank(width, height, dpr)
        self._stop_loading_timer()
        try:
            data = registry.get(render_name)
            version = registry.version(render_name)
        except IconNotFoundError as error:
            client = _network.default_client()
            client.ensure_loaded(render_name)
            if registry.is_pending(render_name):
                self._set_status("loading")
                self._start_loading_timer()
                return create_blank(width, height, dpr)
            failure = client.get_failure(render_name) or error
            self._set_status("missing")
            if not self._reported_failure:
                self._reported_failure = True
                self.failed.emit(str(self._name), failure)
            if self._blank_on_failure:
                return create_blank(width, height, dpr)
            if isinstance(self._fallback, str):
                try:
                    render_name = parse_icon_name(self._fallback)
                    data = registry.get(render_name)
                    version = registry.version(render_name)
                except (IconNotFoundError, InvalidIconNameError):
                    return create_placeholder(width, height, dpr)
            else:
                return create_placeholder(width, height, dpr)
        if render_name == self._name:
            self._set_status("ready")
        color, colors = self._resolve_colors(option)
        disabled = self._options.disabled_opacity if not self.isEnabled() else 1.0
        rotate = self._options.rotate
        if self._spin:
            rotate = (rotate + get_spin_clock().angle(self._spin_period)) % 360.0
        opacity = self._options.opacity * disabled
        key = sha256(
            repr(
                (
                    str(render_name),
                    version,
                    width,
                    height,
                    dpr,
                    color,
                    tuple(sorted((colors or {}).items(), key=repr)),
                    opacity,
                    rotate,
                    self._options.h_flip,
                    self._options.v_flip,
                )
            ).encode("utf-8")
        ).hexdigest()
        try:
            return render_pixmap(
                cache_key=key,
                data=data,
                width=width,
                height=height,
                device_pixel_ratio=dpr,
                color=color,
                colors=colors,
                opacity=opacity,
                rotate=rotate,
                h_flip=self._options.h_flip,
                v_flip=self._options.v_flip,
                stable_scale=self._spin,
            )
        except UnsupportedSvgError as error:
            self._set_status("error")
            if not self._reported_failure:
                self._reported_failure = True
                self.failed.emit(str(self._name), error)
            return create_placeholder(width, height, dpr)

    def _start_loading_timer(self) -> None:
        if self._loading_timer is None:
            self._loading_timer = QTimer(self)
            self._loading_timer.setInterval(50)
            self._loading_timer.timeout.connect(self._poll_loading)
        if not self._loading_timer.isActive():
            self._loading_timer.start()

    def _stop_loading_timer(self) -> None:
        if self._loading_timer is not None:
            self._loading_timer.stop()

    def _poll_loading(self) -> None:
        if registry.is_pending(self._name):
            return
        self._stop_loading_timer()
        self._reported_failure = False
        self._update_status()
        self.update()

    def _resolve_colors(
        self, option: QStyleOption
    ) -> tuple[RGBA | None, Mapping[RGBA, RGBA] | None]:
        window = option.palette.color(QPalette.ColorRole.Window)
        selected: ColorValue | None
        if window.lightness() < 128 and self._options.dark_color is not None:
            selected = self._options.dark_color
        elif window.lightness() >= 128 and self._options.light_color is not None:
            selected = self._options.light_color
        else:
            selected = self._options.color
        if selected is None:
            selected = normalize_color(option.palette.color(self.foregroundRole()))
        if isinstance(selected, Mapping):
            return None, selected
        return selected, None

    def _logical_size(self) -> tuple[float, float]:
        spec = self._options.size
        if spec.is_em:
            font_pixels = self.fontMetrics().height()
            width = spec.width * font_pixels
            height = spec.height * font_pixels
        else:
            width, height = spec.width, spec.height
        return width, height

    def _replace_options(self, **changes: object) -> None:
        require_main_thread()
        values = {
            "size": self._options.size,
            "color": self._options.color,
            "light_color": self._options.light_color,
            "dark_color": self._options.dark_color,
            "opacity": self._options.opacity,
            "disabled_opacity": self._options.disabled_opacity,
            "rotate": self._options.rotate,
            "h_flip": self._options.h_flip,
            "v_flip": self._options.v_flip,
        }
        values.update(changes)
        self._options = make_options(**values)
        self.updateGeometry()
        self.update()

    def _update_status(self) -> None:
        if registry.contains(self._name):
            self._set_status("ready")
        elif registry.is_pending(self._name):
            self._set_status("loading")
        else:
            self._set_status("missing")

    def _set_status(self, value: str) -> None:
        if self._status != value:
            self._status = value
            self.statusChanged.emit(value)
            if value == "ready":
                self.loaded.emit(str(self._name))
