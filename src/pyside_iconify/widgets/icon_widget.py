"""图标控件 IconWidget。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from hashlib import sha256

from pyside_iconify._qt import (
    QEvent,
    QObject,
    QPainter,
    QPaintEvent,
    QPalette,
    QRectF,
    QSize,
    QSizePolicy,
    QStyle,
    QStyleOption,
    Qt,
    QTimer,
    QWidget,
    Signal,
)

from pyside_iconify._config import get_default_config
from pyside_iconify._errors import (
    IconNotFoundError,
    InvalidAnimationError,
    InvalidIconNameError,
    UnsupportedSvgError,
)
from pyside_iconify._logging import logger
from pyside_iconify.core.names import parse_icon_name
from pyside_iconify.core.smil import UnsupportedSmilError
from pyside_iconify.core.registry import registry
from pyside_iconify.core.types import IconData, RGBA
from pyside_iconify.network import client as _network
from pyside_iconify.rendering.engine import IconOptions
from pyside_iconify.rendering.motion import frame_at
from pyside_iconify.rendering.options import make_options
from pyside_iconify.rendering.placeholder import create_blank, create_placeholder
from pyside_iconify.rendering.qt_adapter import (
    ColorValue,
    normalize_color,
    require_application,
    require_main_thread,
)
from pyside_iconify.rendering.renderer import render_pixmap
from pyside_iconify.rendering import smil_player
from pyside_iconify.widgets.animation import Playhead, get_spin_clock

_UNSET = object()

# ThemeChange 只在部分绑定里存在（PyQt5、PyQt6 没有），缺了就少监听一种事件
_THEME_CHANGE = getattr(QEvent.Type, "ThemeChange", None)
_REPOLISH_EVENTS = frozenset(
    kind
    for kind in (
        QEvent.Type.PaletteChange,
        QEvent.Type.ApplicationPaletteChange,
        QEvent.Type.StyleChange,
        _THEME_CHANGE,
    )
    if kind is not None
)
_REFRESH_EVENTS = _REPOLISH_EVENTS | {QEvent.Type.FontChange, QEvent.Type.EnabledChange}


def _valid_speed(value: float) -> float:
    """校验播放速度倍率。

    Args:
        value: 倍率；须为大于 0 的有限数字，不接受 bool

    Returns:
        转为 float 的倍率。

    Raises:
        InvalidAnimationError: 值不是数字、是 bool、非有限数或不大于 0。
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise InvalidAnimationError("speed must be a finite number greater than 0")
    return float(value)


class IconWidget(QWidget):
    """可放入任意 Qt 布局的图标控件。

    控件为固定尺寸策略，按位图原尺寸居中绘制；图标尚未加载完成时显示空白，
    加载失败时按 fallback 设置显示备用图标、空白或占位图。必须在 Qt 主线程创建。

    信号：
        loaded(str)：图标数据就绪时发出，参数为图标名。
        failed(str, object)：加载或渲染失败时发出（每个图标名只发一次），
            参数为图标名和异常对象。
        statusChanged(str)：状态变化时发出，参数为新状态，
            取值 "empty"、"loading"、"ready"、"missing"、"error"。
    """

    loaded = Signal(str)
    failed = Signal(str, object)
    statusChanged = Signal(str)

    def __init__(
        self,
        icon: str | IconData,
        *,
        size: object | None = None,
        color: ColorValue | None = None,
        color_light_theme: ColorValue | None = None,
        color_dark_theme: ColorValue | None = None,
        hover_color: ColorValue | None = None,
        hover_color_light_theme: ColorValue | None = None,
        hover_color_dark_theme: ColorValue | None = None,
        opacity: float | None = None,
        width: object | None = None,
        height: object | None = None,
        rotate: float = 0,
        rotate_overflow: bool = False,
        spin: bool = False,
        spin_period: float | None = None,
        animation: str | None = None,
        animation_period: float | None = None,
        animation_depth: float | None = None,
        autoplay: bool = True,
        speed: float = 1.0,
        h_flip: bool = False,
        v_flip: bool = False,
        qss: str | None = None,
        fallback: str | None | object = _UNSET,
        parent: QWidget | None = None,
    ) -> None:
        """创建图标控件，并立即触发图标加载。

        需要已存在 QApplication 且在主线程调用。参数为 None 时使用全局默认配置。

        Args:
            icon: 图标；可传 "前缀:名称" 格式的图标名字符串，或内联的 IconData。
            size: 图标尺寸；可传数字（正方形像素）、(宽, 高) 元组/列表、QSize、
                "24px"、"1.5em" 等字符串（em 按控件字体高度换算）；None 用默认配置。
            color: 默认颜色；可传单个颜色（CSS 颜色字符串、元组、RGBA、QColor、
                Qt.GlobalColor），或 {原色: 新色} 映射表（原色可为 "currentColor"）；
                None 用默认配置，仍为 None 时取控件前景色。
            color_light_theme: 亮色主题（窗口背景较亮）下使用的颜色，写法同 color；
                未设置时回退到 color。
            color_dark_theme: 暗色主题（窗口背景较暗）下使用的颜色，写法同 color；
                未设置时回退到 color。
            hover_color: 鼠标悬停时的颜色，写法同 color；None 表示不覆盖。
            hover_color_light_theme: 亮色主题下悬停的颜色，写法同 color；
                未设置时回退到 hover_color。
            hover_color_dark_theme: 暗色主题下悬停的颜色，写法同 color；
                未设置时回退到 hover_color。
            opacity: 整体透明度；0 到 1 的数字，None 用默认配置。
            width: 单独覆盖宽度；写法同 size（取其宽度），None 表示沿用 size。
            height: 单独覆盖高度；写法同 size（取其高度），None 表示沿用 size。
            rotate: 静态旋转角度（度）；有限数字，会对 360 取模。
            rotate_overflow: 旋转时是否保持原大小；False 按角度自动缩小以免被裁切，
                True 不缩小，铺满控件的图标旋转时四角可能被裁掉。
            spin: 是否持续旋转；等价于 animation="spin"，不能与其他动画同时给出。
            spin_period: 旋转一圈的秒数；有限正数，None 用默认配置。
            animation: 内置动画；"spin"、"pulse"、"breathe"、"ping"、"bounce" 之一，
                None 表示不动画。
                动画由共享时钟驱动。
            animation_period: 动画一个周期的秒数；有限正数，None 时 spin 用
                spin_period，pulse、ping、bounce 为 1 秒，breathe 为 2 秒。
            animation_depth: 动画变化幅度；0 到 1，None 用默认值。pulse 默认 0.25（缩到 75%），
                breathe 默认 0.7（淡到 30%），ping 默认 1（水波扩散到 2 倍），
                bounce 默认 0.25（跳起图标高度的 25%）。ping、bounce 会把图标缩小到
                1 / (1 + 幅度)，给水波和弹跳留出空间。spin 不能给出。
            autoplay: 图标自带 SMIL 动画（如 line-md、meteocons、svg-spinners 的动画图标）
                是否自动播放；False 时停在播完后的完成态，调用 play() 才开始。
                对没有自带动画的图标无影响。
            speed: 图标自带动画的播放速度倍率；须大于 0，不影响 animation= 内置效果。
            h_flip: 是否水平翻转；True 或 False。
            v_flip: 是否垂直翻转；True 或 False。
            qss: 样式表属性；传入非空字符串时写入控件的 "qss" 动态属性，
                并启用 QSS 背景绘制，None 或空字符串表示不设置。
            fallback: 加载失败时的备用图标；可传图标名字符串（显示该图标）、
                None（显示空白）；不传则用默认配置的 fallback，仍为 None 时显示问号占位图。
            parent: 父控件；QWidget 或 None。
        """
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
            color_light_theme=color_light_theme,
            color_dark_theme=color_dark_theme,
            hover_color=hover_color,
            hover_color_light_theme=hover_color_light_theme,
            hover_color_dark_theme=hover_color_dark_theme,
            opacity=opacity,
            width=width,
            height=height,
            spin=spin,
            spin_period=spin_period,
            animation=animation,
            animation_period=animation_period,
            animation_depth=animation_depth,
            rotate=rotate,
            rotate_overflow=rotate_overflow,
            h_flip=h_flip,
            v_flip=v_flip,
        )
        self.setMouseTracking(True)
        self._width_override = width
        self._height_override = height
        self._fallback = (
            get_default_config().fallback if fallback is _UNSET else fallback
        )
        self._blank_on_failure = fallback is None
        self._status = "empty"
        self._hovering = False
        self._key_state: tuple | None = None
        self._key_cache: str | None = None
        self._fast_state: tuple | None = None
        self._fast_pixmap = None
        self._reported_failure = False
        self._repolishing = False
        self._loading_timer: QTimer | None = None
        self._playhead = Playhead(_valid_speed(speed))
        self._autoplay = bool(autoplay)
        self._smil_shown: float | None = None
        if qss:
            self.setProperty("qss", qss)
            # QSS 背景需要控件自己参与样式绘制
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if self._options.animation is not None:
            get_spin_clock().add(self)
        # 构造即预触发加载，不等首次绘制。
        if not registry.contains(self._name) and not registry.is_pending(self._name):
            _network.default_client().ensure_loaded(self._name)
        self._update_status()

    def iconName(self) -> str:
        """返回当前图标名。"""
        return str(self._name)

    def setIcon(self, icon: str) -> None:
        """更换图标名，并重新检查加载状态。

        Args:
            icon: 新的图标名；"前缀:名称" 格式的字符串。
        """
        require_main_thread()
        self._name = parse_icon_name(icon)
        self._reported_failure = False
        # 新图标有自己的动画，要从头开始：autoplay 时立刻计时，否则回到"未开始"（显示完成态）
        self._smil_shown = None
        if self._autoplay:
            self._playhead.restart(get_spin_clock().elapsed())
            get_spin_clock().add(self)
        else:
            self._playhead = Playhead(self._playhead.speed)
        self._update_status()
        self.update()

    def setSize(self, value: object) -> None:
        """设置图标尺寸。

        Args:
            value: 新尺寸；可传数字、(宽, 高) 元组/列表、QSize、"24px"、"1.5em" 等字符串。
        """
        self._replace_options(size=value)

    def setColor(self, value: ColorValue | None) -> None:
        """设置默认颜色。

        Args:
            value: 颜色；单个颜色或 {原色: 新色} 映射表，None 恢复默认配置。
        """
        self._replace_options(color=value)

    def setColorLightTheme(self, value: ColorValue | None) -> None:
        """设置亮色主题颜色。

        Args:
            value: 颜色；单个颜色或 {原色: 新色} 映射表，None 恢复默认配置。
        """
        self._replace_options(color_light_theme=value)

    def setColorDarkTheme(self, value: ColorValue | None) -> None:
        """设置暗色主题颜色。

        Args:
            value: 颜色；单个颜色或 {原色: 新色} 映射表，None 恢复默认配置。
        """
        self._replace_options(color_dark_theme=value)

    def setOpacity(self, value: float) -> None:
        """设置整体透明度。

        Args:
            value: 透明度；0 到 1 的数字。
        """
        self._replace_options(opacity=value)

    def setRotation(self, value: float) -> None:
        """设置静态旋转角度。

        Args:
            value: 旋转角度（度）；有限数字，会对 360 取模。
        """
        self._replace_options(rotate=value)

    def setRotateOverflow(self, enabled: bool) -> None:
        """设置旋转时是否保持原大小。

        Args:
            enabled: True 不随角度缩小，四角旋转时可能被裁掉；False 自动缩小以免被裁切。
        """
        self._replace_options(rotate_overflow=enabled)

    def setAnimation(
        self,
        animation: str | None,
        period: float | None = None,
        depth: float | None = None,
    ) -> None:
        """设置或停止内置动画。

        Args:
            animation: "spin"、"pulse"、"breathe"、"ping"、"bounce" 之一；None 停止动画。
            period: 一个周期的秒数；有限正数，None 用该动画的默认周期。
            depth: 变化幅度；0 到 1，None 用默认值，不能用于 spin。
        """
        self._replace_options(
            animation=animation, animation_period=period, animation_depth=depth
        )
        clock = get_spin_clock()
        if self._options.animation is not None:
            clock.add(self)
        else:
            clock.remove(self)
        self.update()

    def setSpin(self, enabled: bool) -> None:
        """启用或停止旋转动画；其他动画运行时 enabled=False 不会打断它。

        Args:
            enabled: 是否旋转；True 等价于 setAnimation("spin")。
        """
        if enabled:
            self.setAnimation("spin")
        elif self._options.animation == "spin":
            self.setAnimation(None)

    def isAnimated(self) -> bool:
        """当前图标是否带有可播放的 SMIL 动画。

        Returns:
            图标数据已加载且含受支持的 SMIL 动画时为 True。
        """
        plan = self._current_plan()
        return plan is not None

    def isPlaying(self) -> bool:
        """图标自带的动画是否正在播放。

        Returns:
            动画已开始、没有暂停、且还没有播到完成态时为 True；循环图标只要没暂停就一直为 True。
        """
        plan = self._current_plan()
        if plan is None or not self._playhead.started or self._playhead.paused:
            return False
        if plan.loops:
            return True
        return self._playhead.elapsed(get_spin_clock().elapsed()) < plan.duration

    def play(self) -> None:
        """开始或继续播放图标自带的 SMIL 动画；已暂停则从暂停处继续。"""
        require_main_thread()
        clock = get_spin_clock()
        now = clock.elapsed()
        if self._playhead.paused:
            self._playhead.resume(now)
        elif not self._playhead.started:
            self._playhead.start(now)
        clock.add(self)
        self.update()

    def pause(self) -> None:
        """暂停图标自带的动画，画面停在当前帧。"""
        require_main_thread()
        self._playhead.pause(get_spin_clock().elapsed())
        self.update()

    def replay(self) -> None:
        """从头重新播放图标自带的动画。"""
        require_main_thread()
        clock = get_spin_clock()
        self._playhead.restart(clock.elapsed())
        clock.add(self)
        self.update()

    def setSpeed(self, speed: float) -> None:
        """设置图标自带动画的播放速度倍率，已播放的部分保持不变。

        Args:
            speed: 倍率；须大于 0，如 0.5 为半速、2 为两倍速。

        Raises:
            InvalidAnimationError: 倍率不是大于 0 的有限数字。
        """
        require_main_thread()
        self._playhead.set_speed(_valid_speed(speed), get_spin_clock().elapsed())
        self.update()

    def setFlips(self, horizontal: bool, vertical: bool) -> None:
        """设置水平和垂直翻转。

        Args:
            horizontal: 是否水平翻转；True 或 False。
            vertical: 是否垂直翻转；True 或 False。
        """
        self._replace_options(h_flip=horizontal, v_flip=vertical)

    def sizeHint(self) -> QSize:
        """返回图标的逻辑尺寸建议。"""
        width, height = self._logical_size()
        return QSize(round(width), round(height))

    def minimumSizeHint(self) -> QSize:
        """返回与 sizeHint 相同的最小尺寸建议。"""
        return self.sizeHint()

    def showEvent(self, event: QEvent) -> None:
        """控件显示时同步旋转时钟。

        Args:
            event: Qt 显示事件。
        """
        super().showEvent(event)
        if self._options.animation is not None:
            get_spin_clock().sync()

    def hideEvent(self, event: QEvent) -> None:
        """控件隐藏时同步旋转时钟。

        Args:
            event: Qt 隐藏事件。
        """
        super().hideEvent(event)
        if self._options.animation is not None:
            get_spin_clock().sync()

    def changeEvent(self, event: QEvent) -> None:
        """调色板、样式、字体或启用状态变化时重新抛光并重绘。

        Args:
            event: Qt 状态变化事件。
        """
        super().changeEvent(event)
        kind = event.type()
        if kind in _REPOLISH_EVENTS:
            self._repolish()
        if kind in _REFRESH_EVENTS:
            self.updateGeometry()
            self.update()

    def _has_own_palette(self) -> bool:
        """控件自己是否显式设置过调色板项。

        PySide6 能直接读调色板的 resolveMask；其他绑定没有这个方法，改看
        WA_SetPalette。Qt 的 setPalette 在传入非空调色板时才打开该属性，
        含义相同。

        Returns:
            设置过调色板项返回 True，完全跟随样式和应用调色板返回 False。
        """
        palette = self.palette()
        if hasattr(palette, "resolveMask"):
            return bool(palette.resolveMask())
        return self.testAttribute(Qt.WidgetAttribute.WA_SetPalette)

    def _repolish(self) -> None:
        """重新应用控件样式，带重入保护。"""
        if self._repolishing:
            return
        self._repolishing = True
        try:
            if not self._has_own_palette():
                self.setPalette(QPalette())
            style = self.style()
            style.unpolish(self)
            style.polish(self)
        finally:
            self._repolishing = False

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制 QSS 背景（如启用）和居中的图标位图。

        Args:
            event: Qt 绘制事件。
        """
        painter = QPainter(self)
        if self.testAttribute(Qt.WidgetAttribute.WA_StyledBackground):
            # QSS 背景需要控件自己参与样式绘制
            option = QStyleOption()
            option.initFrom(self)
            self.style().drawPrimitive(
                QStyle.PrimitiveElement.PE_Widget, option, painter, self
            )
        pixmap = self._pixmap()
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

    def _pixmap(self):
        """生成当前状态应显示的位图。

        加载中返回空白；加载失败按 fallback 设置返回备用图标、空白或占位图；
        渲染不支持的 SVG 时返回占位图。状态不变时复用上一次的位图。

        Returns:
            QPixmap：带设备像素比的位图。
        """
        logical_width, logical_height = self._logical_size()
        width = max(1.0, logical_width)
        height = max(1.0, logical_height)
        dpr = self.devicePixelRatioF()
        # 快路径：数据版本、尺寸、缩放比、颜色来源、悬停/禁用状态都没变
        # 时，画面必然与上次一致，直接复用位图，跳过全部解析与哈希。
        # 调色板变化会换 palette cacheKey，主题切换、QSS 改色都能命中失效。
        try:
            fast_state = (
                str(self._name),
                registry.version(self._name),
                width,
                height,
                dpr,
                id(self._options),
                self.isEnabled(),
                self._hovering,
                self.palette().cacheKey(),
                require_application().palette().cacheKey(),
            )
        except IconNotFoundError:
            fast_state = None
        if (
            fast_state is not None
            and self._options.animation is None
            and not self._smil_running()
            and not self._smil_stale()
            and fast_state == self._fast_state
            and self._fast_pixmap is not None
            and not registry.is_pending(self._name)
        ):
            return self._fast_pixmap
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
        data, smil_moment = self._smil_frame(data, str(render_name))
        color, colors = self._resolve_colors()
        disabled = self._options.disabled_opacity if not self.isEnabled() else 1.0
        frame = frame_at(
            self._options.animation,
            get_spin_clock().elapsed(),
            self._options.animation_period,
            self._options.animation_depth,
        )
        rotate = (self._options.rotate + frame.rotate) % 360.0
        opacity = self._options.opacity * disabled * frame.opacity
        # 静态场景下参数不变，直接复用上次的缓存键，省掉每帧的哈希计算
        key_state = (
            str(render_name),
            version,
            width,
            height,
            dpr,
            color,
            tuple(sorted((colors or {}).items(), key=repr)) if colors else None,
            opacity,
            rotate,
            frame.shape,
            smil_moment,
            self._options.rotate_overflow,
            self._options.h_flip,
            self._options.v_flip,
        )
        if key_state != self._key_state:
            self._key_state = key_state
            self._key_cache = sha256(repr(key_state).encode("utf-8")).hexdigest()
        key = self._key_cache
        try:
            pixmap = render_pixmap(
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
                stable_scale=self._options.spin,
                rotate_overflow=self._options.rotate_overflow,
                frame=frame,
            )
        except UnsupportedSvgError as error:
            self._set_status("error")
            if not self._reported_failure:
                self._reported_failure = True
                self.failed.emit(str(self._name), error)
            return create_placeholder(width, height, dpr)
        # 只有成功渲染才更新快路径状态，保证键与位图始终配对
        self._fast_state = fast_state
        self._fast_pixmap = pixmap
        return pixmap

    def _current_plan(self) -> smil_player.Plan | None:
        """当前图标的 SMIL 播放计划。

        Returns:
            Plan；图标尚未加载、没有自带动画或写法不受支持时为 None。
        """
        try:
            data = registry.get(self._name)
        except IconNotFoundError:
            return None
        return smil_player.get_plan(data, str(self._name))

    def _needs_frames(self) -> bool:
        """此刻是否还需要共享时钟继续驱动重绘。

        内置效果（animation=）一直需要；图标自带的 SMIL 动画只在播放中需要，
        播完或暂停后让出定时器，避免空转。

        Returns:
            需要继续刷新时为 True。
        """
        if self._options.animation is not None:
            return True
        return self._smil_running() or (self._autoplay and not self._playhead.started)

    def _smil_stale(self) -> bool:
        """上次渲染的 SMIL 画面是否已经落后于现在应有的画面。

        动画刚好播完（或被暂停）的那一刻，``_smil_running`` 已经是 False，
        但上一次画出来的还是倒数第二帧；这时必须再画一次，才能停在真正的最终画面。

        Returns:
            需要重画时为 True。
        """
        plan = self._current_plan()
        if plan is None:
            return False
        shown = self._smil_shown
        if not self._playhead.started:
            wanted = plan.finish
        else:
            wanted = smil_player.quantize(
                plan, self._playhead.elapsed(get_spin_clock().elapsed())
            )
        return shown != wanted

    def _smil_running(self) -> bool:
        """图标自带的动画此刻是否还在变化（用来绕过静态快路径）。

        Returns:
            有动画、已开始、没暂停、且没有播到不再变化的完成态时为 True。
        """
        if not self._playhead.started or self._playhead.paused:
            return False
        plan = self._current_plan()
        if plan is None:
            return False
        if plan.loops:
            return True
        return self._playhead.elapsed(get_spin_clock().elapsed()) < plan.duration

    def _smil_frame(self, data: IconData, label: str) -> tuple[IconData, float | None]:
        """把图标数据换成当前应显示的 SMIL 帧。

        autoplay=False 且尚未调用 play() 时显示完成态；否则按播放头算出时刻。
        没有自带动画的图标原样返回。

        Args:
            data: 图标数据
            label: 用于日志的图标名

        Returns:
            (该帧对应的静态图标数据, 用于缓存键的时刻)；没有自带动画时时刻为 None。
        """
        plan = smil_player.get_plan(data, label)
        if plan is None:
            return data, None
        clock = get_spin_clock()
        if not self._playhead.started and self._autoplay:
            self._playhead.start(clock.elapsed())
            clock.add(self)
        if not self._playhead.started:
            moment = plan.finish
        else:
            moment = smil_player.quantize(plan, self._playhead.elapsed(clock.elapsed()))
        try:
            frame = smil_player.render_data(data, plan, moment)
            self._smil_shown = moment
            return frame, moment
        except UnsupportedSmilError as error:
            logger.warning("icon %s cannot be evaluated (%s); showing it as written", label, error)
            return data, None

    def _start_loading_timer(self) -> None:
        """启动 50 毫秒间隔的加载轮询定时器。"""
        if self._loading_timer is None:
            self._loading_timer = QTimer(self)
            self._loading_timer.setInterval(50)
            self._loading_timer.timeout.connect(self._poll_loading)
        if not self._loading_timer.isActive():
            self._loading_timer.start()

    def _stop_loading_timer(self) -> None:
        """停止加载轮询定时器。"""
        if self._loading_timer is not None:
            self._loading_timer.stop()

    def _poll_loading(self) -> None:
        """轮询图标是否加载结束，结束后更新状态并重绘。"""
        if registry.is_pending(self._name):
            return
        self._stop_loading_timer()
        self._reported_failure = False
        self._update_status()
        self.update()

    def enterEvent(self, event: QEvent) -> None:
        """鼠标进入时标记悬停并重绘。

        Args:
            event: Qt 鼠标进入事件。
        """
        self._hovering = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """鼠标离开时取消悬停标记并重绘。

        Args:
            event: Qt 鼠标离开事件。
        """
        self._hovering = False
        self.update()
        super().leaveEvent(event)

    def _resolve_colors(self) -> tuple[RGBA | None, Mapping[RGBA, RGBA] | None]:
        """按主题明暗和悬停状态选出当前使用的颜色。

        优先级：悬停覆盖色、主题专用色、默认色、控件前景色。

        Returns:
            (单色, 映射表) 二元组；选中的是单色时映射表为 None，选中映射表时单色为 None。
        """
        window = self.palette().color(QPalette.ColorRole.Window)
        selected: ColorValue | None
        dark = window.lightness() < 128
        if dark and self._options.color_dark_theme is not None:
            selected = self._options.color_dark_theme
        elif not dark and self._options.color_light_theme is not None:
            selected = self._options.color_light_theme
        else:
            selected = self._options.color
        if selected is None:
            selected = normalize_color(self.palette().color(self.foregroundRole()))
        if self._hovering:
            from pyside_iconify.rendering.engine import _select_hover_color

            override = _select_hover_color(self._options, dark)
            if override is not None:
                selected = override
        if isinstance(selected, Mapping):
            return None, selected
        return selected, None

    def _logical_size(self) -> tuple[float, float]:
        """计算图标的逻辑像素宽高，em 单位按字体高度换算。

        Returns:
            (宽, 高) 二元组，单位为逻辑像素。
        """
        spec = self._options.size
        if spec.is_em:
            font_pixels = self.fontMetrics().height()
            width = spec.width * font_pixels
            height = spec.height * font_pixels
        else:
            width, height = spec.width, spec.height
        return width, height

    def _replace_options(self, **changes: object) -> None:
        """用给定字段覆盖当前渲染选项并刷新几何与绘制。

        Args:
            **changes: 要覆盖的 make_options 关键字参数，如 color、opacity、rotate。
        """
        require_main_thread()
        values = {
            "size": self._options.size,
            "color": self._options.color,
            "color_light_theme": self._options.color_light_theme,
            "color_dark_theme": self._options.color_dark_theme,
            "hover_color": self._options.hover_color,
            "hover_color_light_theme": self._options.hover_color_light_theme,
            "hover_color_dark_theme": self._options.hover_color_dark_theme,
            "selected_color": self._options.selected_color,
            "selected_color_light_theme": self._options.selected_color_light_theme,
            "selected_color_dark_theme": self._options.selected_color_dark_theme,
            "opacity": self._options.opacity,
            "disabled_opacity": self._options.disabled_opacity,
            "rotate": self._options.rotate,
            "rotate_overflow": self._options.rotate_overflow,
            "animation": self._options.animation,
            "animation_period": self._options.animation_period,
            "animation_depth": self._options.animation_depth,
            "spin_period": self._options.spin_period,
            "h_flip": self._options.h_flip,
            "v_flip": self._options.v_flip,
        }
        values.update(changes)
        self._options = make_options(**values)
        self.updateGeometry()
        self.update()

    def _update_status(self) -> None:
        """按注册表状态更新为 ready、loading 或 missing。"""
        if registry.contains(self._name):
            self._set_status("ready")
        elif registry.is_pending(self._name):
            self._set_status("loading")
        else:
            self._set_status("missing")

    def _set_status(self, value: str) -> None:
        """设置状态，变化时发出 statusChanged，变为 ready 时再发出 loaded。

        Args:
            value: 新状态；"empty"、"loading"、"ready"、"missing"、"error" 之一。
        """
        if self._status != value:
            self._status = value
            self.statusChanged.emit(value)
            if value == "ready":
                self.loaded.emit(str(self._name))
