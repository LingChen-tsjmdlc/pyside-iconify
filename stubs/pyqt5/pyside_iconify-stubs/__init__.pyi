from collections.abc import Callable, Mapping, Sequence
from typing import TypeAlias

from pyside_iconify._qt import (
    QColor as QColor,
    QIcon as QIcon,
    QObject as QObject,
    QPixmap as QPixmap,
    QSize as QSize,
    Qt as Qt,
    QWidget as QWidget,
    Signal as Signal,
)

from pyside_iconify._config import DefaultConfig
from pyside_iconify.core.registry import IconRegistry
from pyside_iconify.core.types import IconData, IconName, RGBA
from pyside_iconify.network.disk_cache import DiskCache
from pyside_iconify.network.downloader import IconDownloader

ColorScalar: TypeAlias = str | Sequence[int | float] | RGBA | QColor | Qt.GlobalColor
ColorMapping: TypeAlias = Mapping[ColorScalar, ColorScalar]
ColorValue: TypeAlias = ColorScalar | ColorMapping

class IconifyError(Exception):
    """库异常基类。"""
    ...
class InvalidIconNameError(IconifyError):
    """图标名无效。"""
    ...
class InvalidIconDataError(IconifyError):
    """Iconify 数据无效。"""
    ...
class IconNotFoundError(IconifyError):
    """图标数据不存在。"""
    ...
class InvalidColorError(IconifyError):
    """颜色值无效。"""
    ...
class InvalidSizeError(IconifyError):
    """尺寸值无效。"""
    ...
class InvalidRotationError(IconifyError):
    """旋转值无效。"""
    ...
class InvalidAnimationError(IconifyError):
    """动画名称无效或参数互相冲突。"""
    ...
class InvalidOpacityError(IconifyError):
    """透明度无效。"""
    ...
class DuplicateIconError(IconifyError):
    """图标重复注册。"""
    ...
class UnsupportedSvgError(IconifyError):
    """SVG 数据不受支持。"""
    ...
class UnsafeIconDataError(IconifyError):
    """图标数据不安全。"""
    ...
class WrongThreadError(IconifyError):
    """Qt 调用不在主线程。"""
    ...
class NoApplicationError(IconifyError):
    """缺少 QApplication 实例。"""
    ...
class IconNotLoadedError(IconifyError):
    """图标数据尚未就绪。"""
    ...
class UnsupportedTargetError(IconifyError):
    """目标类型不受支持。"""
    ...
class NetworkError(IconifyError):
    """网络请求失败。"""
    ...
class OfflineError(IconifyError):
    """离线模式下数据不可用。"""
    ...
class RateLimitError(IconifyError):
    """请求过于频繁被限流。"""
    ...
class ServerError(IconifyError):
    """服务器返回错误。"""
    ...
class InvalidResponseError(IconifyError):
    """响应内容不是合法图标数据。"""
    ...
class ResponseTooLargeError(IconifyError):
    """响应内容超出大小上限。"""
    ...
class RequestCancelledError(IconifyError):
    """请求被主动取消。"""
    ...
class ClientClosedError(IconifyError):
    """客户端已关闭。"""
    ...

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
    loaded: Signal
    failed: Signal
    statusChanged: Signal
    def __init__(
        self,
        icon: str | IconData,
        *,
        size: int | float | str | tuple[int | float, int | float] | QSize | None = None,
        color: ColorValue | None = None,
        color_light_theme: ColorValue | None = None,
        color_dark_theme: ColorValue | None = None,
        hover_color: ColorValue | None = None,
        hover_color_light_theme: ColorValue | None = None,
        hover_color_dark_theme: ColorValue | None = None,
        opacity: float | None = None,
        width: int | float | str | None = None,
        height: int | float | str | None = None,
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
        fallback: str | None = ...,
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
        ...
    def iconName(self) -> str:
        """返回当前图标名。"""
        ...
    def setIcon(self, icon: str) -> None:
        """更换图标名，并重新检查加载状态。

        Args:
            icon: 新的图标名；"前缀:名称" 格式的字符串。
        """
        ...
    def setSize(
        self, value: int | float | str | tuple[int | float, int | float] | QSize
    ) -> None:
        """设置图标尺寸。

        Args:
            value: 新尺寸；可传数字、(宽, 高) 元组/列表、QSize、"24px"、"1.5em" 等字符串。
        """
        ...
    def setColor(self, value: ColorValue | None) -> None:
        """设置默认颜色。

        Args:
            value: 颜色；单个颜色或 {原色: 新色} 映射表，None 恢复默认配置。
        """
        ...
    def setColorLightTheme(self, value: ColorValue | None) -> None:
        """设置亮色主题颜色。

        Args:
            value: 颜色；单个颜色或 {原色: 新色} 映射表，None 恢复默认配置。
        """
        ...
    def setColorDarkTheme(self, value: ColorValue | None) -> None:
        """设置暗色主题颜色。

        Args:
            value: 颜色；单个颜色或 {原色: 新色} 映射表，None 恢复默认配置。
        """
        ...
    def setOpacity(self, value: float) -> None:
        """设置整体透明度。

        Args:
            value: 透明度；0 到 1 的数字。
        """
        ...
    def setRotation(self, value: float) -> None:
        """设置静态旋转角度。

        Args:
            value: 旋转角度（度）；有限数字，会对 360 取模。
        """
        ...
    def setRotateOverflow(self, enabled: bool) -> None:
        """设置旋转时是否保持原大小。

        Args:
            enabled: True 不随角度缩小，四角旋转时可能被裁掉；False 自动缩小以免被裁切。
        """
        ...
    def isAnimated(self) -> bool:
        """当前图标是否带有可播放的 SMIL 动画。

        Returns:
            图标数据已加载且含受支持的 SMIL 动画时为 True。
        """
        ...
    def isPlaying(self) -> bool:
        """图标自带的动画是否正在播放。

        Returns:
            动画已开始、没有暂停、且还没有播到完成态时为 True；循环图标只要没暂停就一直为 True。
        """
        ...
    def play(self) -> None:
        """开始或继续播放图标自带的 SMIL 动画；已暂停则从暂停处继续。"""
        ...
    def pause(self) -> None:
        """暂停图标自带的动画，画面停在当前帧。"""
        ...
    def replay(self) -> None:
        """从头重新播放图标自带的动画。"""
        ...
    def setSpeed(self, speed: float) -> None:
        """设置图标自带动画的播放速度倍率，已播放的部分保持不变。

        Args:
            speed: 倍率；须大于 0，如 0.5 为半速、2 为两倍速。

        Raises:
            InvalidAnimationError: 倍率不是大于 0 的有限数字。
        """
        ...
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
        ...
    def setSpin(self, enabled: bool) -> None:
        """启用或停止旋转动画；其他动画运行时 enabled=False 不会打断它。

        Args:
            enabled: 是否旋转；True 等价于 setAnimation("spin")。
        """
        ...
    def setFlips(self, horizontal: bool, vertical: bool) -> None:
        """设置水平和垂直翻转。

        Args:
            horizontal: 是否水平翻转；True 或 False。
            vertical: 是否垂直翻转；True 或 False。
        """
        ...

def add_icon(name: str, data: IconData | str, *, replace: bool = False) -> None:
    """注册一个本地图标。

    Args:
        name: 图标名；格式为 ``prefix:name``。
        data: 图标数据；可传 IconData 或 SVG body 字符串。
        replace: 同名图标已存在时是否覆盖；False 时抛出重复注册异常。
    """
    ...
def add_collection(
    collection: Mapping[str, object], *, replace: bool = False
) -> None:
    """注册一份 Iconify JSON 图标集合。

    Args:
        collection: Iconify JSON 集合（已解析为映射）。
        replace: 集合内存在已注册的同名图标时是否覆盖；False 时抛出重复注册异常。
    """
    ...
def get_icon(
    icon: str | IconData,
    *,
    size: int | float | str | tuple[int | float, int | float] | QSize | None = None,
    color: ColorValue | None = None,
    color_light_theme: ColorValue | None = None,
    color_dark_theme: ColorValue | None = None,
    selected_color: ColorValue | None = None,
    selected_color_light_theme: ColorValue | None = None,
    selected_color_dark_theme: ColorValue | None = None,
    opacity: float | None = None,
    width: int | float | str | None = None,
    height: int | float | str | None = None,
    rotate: float = 0,
    rotate_overflow: bool = False,
    spin: bool = False,
    h_flip: bool = False,
    v_flip: bool = False,
) -> QIcon:
    """返回可用于任意 Qt 控件的标准 QIcon。

    悬停变色不在这里：裸 QIcon 表达不了悬停（样式对图标
    的 mode 请求不可靠）。按钮悬停用 set_icon(hover_color=...)，
    控件悬停用 IconWidget(hover_color=...)。

    Args:
        icon: 图标名（``prefix:name``）或 IconData；IconData 会按内容注册为内联图标。
        size: 图标尺寸；None 使用默认配置，可传数字、``"16px"``/``"1.5em"`` 字符串或 (宽, 高) 序列。
        color: 通用颜色；None 使用默认配置。
        color_light_theme: 浅色主题下的颜色；None 使用默认配置。
        color_dark_theme: 深色主题下的颜色；None 使用默认配置。
        selected_color: 选中状态的颜色；None 表示不单独指定。
        selected_color_light_theme: 浅色主题下选中状态的颜色；None 表示不单独指定。
        selected_color_dark_theme: 深色主题下选中状态的颜色；None 表示不单独指定。
        opacity: 不透明度；0 到 1，None 使用默认配置。
        width: 单独覆盖宽度；None 沿用 size 的宽度。
        height: 单独覆盖高度；None 沿用 size 的高度。
        rotate: 旋转角度；单位为度，会对 360 取模。
        rotate_overflow: 旋转时是否保持原大小；False 按角度自动缩小以免被裁切，
            True 不缩小，铺满的图标旋转时四角可能被裁掉。
        spin: 是否持续旋转。
        h_flip: 是否水平翻转。
        v_flip: 是否垂直翻转。

    Returns:
        可直接用于 Qt 控件的 QIcon。
    """
    ...
def get_pixmap(
    icon: str | IconData, *, size: object | None = None, **options: object
) -> QPixmap:
    """返回静态 QPixmap。

    Args:
        icon: 图标名（``prefix:name``）或 IconData。
        size: 图标尺寸；None 使用默认配置，em 单位按应用默认字体高度换算。
        **options: 其余渲染选项；取值同 get_icon 的同名参数（如 color、opacity、rotate、h_flip）。

    Returns:
        按解析后的尺寸渲染出的 QPixmap。
    """
    ...
def get_icon_data(icon: str) -> IconData:
    """返回已注册的图标数据。

    Args:
        icon: 图标名；格式为 ``prefix:name``。

    Returns:
        该图标对应的 IconData。
    """
    ...
def mark_pending(icon: str) -> None:
    """标记图标数据正在加载。

    Args:
        icon: 图标名；格式为 ``prefix:name``。
    """
    ...
def get_icon_colors(icon: str) -> tuple[str, ...]:
    """列出图标固定颜色。

    Args:
        icon: 已注册的图标名。

    Returns:
        ``#rrggbb`` 形式的颜色字符串元组；不含 alpha。
    """
    ...
def is_animated(icon: str) -> bool:
    """判断图标是否带有可播放的 SMIL 动画。

    只认 SMIL（SVG 内置的 animate、set、animateTransform、animateMotion）。
    CSS 动画、脚本动画等其他形式不属于播放范围，这类图标和普通静态图一样显示。

    Args:
        icon: 已注册的图标名。

    Returns:
        图标含有本库能播放的 SMIL 动画时为 True。
    """
    ...
def is_monotone(icon: str) -> bool:
    """判断图标是否只使用 currentColor。

    Args:
        icon: 已注册的图标名。

    Returns:
        图标没有固定颜色时为 True。
    """
    ...
def hex_argb(value: str) -> RGBA:
    """按 Qt 的 #AARRGGBB 顺序解析十六进制颜色。

    Args:
        value: 十六进制颜色文本；可传 `#RGB`、`#ARGB`、`#RRGGBB`、`#AARRGGBB`，`#` 可省略。

    Returns:
        解析后的 RGBA 颜色；无透明度部分时不透明度取 RGBA 默认值。

    Raises:
        InvalidColorError: 文本不是合法的十六进制颜色。
    """
    ...
def hex_rgba(value: str) -> RGBA:
    """按 CSS 的 #RRGGBBAA 顺序解析十六进制颜色。

    Args:
        value: 十六进制颜色文本；可传 `#RGB`、`#RGBA`、`#RRGGBB`、`#RRGGBBAA`，`#` 可省略。

    Returns:
        解析后的 RGBA 颜色；无透明度部分时不透明度取 RGBA 默认值。

    Raises:
        InvalidColorError: 文本不是合法的十六进制颜色。
    """
    ...
def get_default_config() -> DefaultConfig:
    """返回当前默认配置。

    Returns:
        当前生效的 DefaultConfig。
    """
    ...
def set_default_config(
    *,
    size: int | float | str | tuple[int | float, int | float] | QSize | None = ...,
    color: ColorValue | None = ...,
    color_light_theme: ColorValue | None = ...,
    color_dark_theme: ColorValue | None = ...,
    opacity: float | None = ...,
    fallback: str | None = ...,
    disabled_opacity: float | None = ...,
    spin_period: float | None = ...,
) -> DefaultConfig:
    """更新新图标的默认配置。

    未传入的参数保持当前值；传入 None 则恢复为内置默认值。

    Args:
        size: 默认尺寸；可传数字、``"16px"``/``"1.5em"`` 字符串或 (宽, 高) 序列。
        color: 默认颜色。
        color_light_theme: 浅色主题下的默认颜色。
        color_dark_theme: 深色主题下的默认颜色。
        opacity: 默认不透明度；0 到 1。
        fallback: 后备图标名；格式为 ``prefix:name``。
        disabled_opacity: 禁用状态的不透明度；0 到 1。
        spin_period: 旋转一圈所需的秒数；须为有限正数。

    Returns:
        更新后的 DefaultConfig。
    """
    ...
def set_disabled_opacity(value: float) -> None:
    """设置禁用状态的默认不透明度。

    Args:
        value: 不透明度；0 到 1。
    """
    ...
def set_cache_limits(
    *, pixmap_mib: int | None = None, data_entries: int | None = None
) -> None:
    """调整缓存上限。

    Args:
        pixmap_mib: 像素图缓存上限；单位 MiB，须大于 0，None 表示不修改。
        data_entries: 图标数据缓存的最大条目数，须大于 0，None 表示不修改。
    """
    ...
def set_offline(value: bool) -> None:
    """切换默认客户端的离线模式。

    Args:
        value: True 进入离线模式，False 回到在线模式。
    """
    ...
def is_offline() -> bool:
    """返回默认客户端是否处于离线模式。"""
    ...
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
    ...
def register_icon_target(target_type: type, applier: object) -> None:
    """注册自定义目标类型的图标适配器。

    同一类型重复注册会覆盖旧适配器。

    Args:
        target_type: 目标类型；必须是类
        applier: 适配器；签名为 (target, icon, *args)，args 来自 set_icon 的透传参数
    """
    ...
def pack_icons(
    icons: Sequence[str], out_path: str, *, api_root: str = ...
) -> object:
    """按显式清单联网收集图标，写成一个 bundle 文件。

    bundle 可在运行时用 load_bundle() 加载，断网也能显示。

    Args:
        icons: 图标名清单；每项形如 "prefix:name"
        out_path: 输出 bundle 文件路径
        api_root: Iconify API 根地址；默认 DEFAULT_API_ROOT

    Returns:
        bundle 文件路径。
    """
    ...
def pack_project(
    paths: str, out_path: str, *, api_root: str = ...
) -> tuple[object, list[str]]:
    """自动扫描 + 打包一步完成。

    扫描到的名字不存在的自动跳过（源码里 'a:b' 形状的普通字符串很常见），
    跳过的名字会输出到 stderr。

    Args:
        paths: 要扫描的目录或 .py 文件；可传单个路径或路径可迭代对象
        out_path: 输出 bundle 文件路径
        api_root: Iconify API 根地址；默认 DEFAULT_API_ROOT

    Returns:
        (bundle 路径, 实际打包的图标名列表)。
    """
    ...
def load_bundle(path: str) -> None:
    """加载 bundle 文件并注册全部图标集合。

    相对路径找不到时自动查 PyInstaller 的解包目录（sys._MEIPASS），
    所以同一句 load_bundle("icons.json") 开发态和打包后都能用。

    Args:
        path: bundle 文件路径；可传绝对路径或相对路径

    Raises:
        InvalidResponseError: 文件内容不是 pyside-iconify bundle。
    """
    ...
def load_icons(
    icons: Sequence[str],
    *,
    on_finished: Callable[[dict[str, Exception | None]], None] | None = None,
) -> LoadRequest:
    """用默认客户端预加载一批图标。

    Args:
        icons: 图标名可迭代对象；每项为 "prefix:name" 字符串。
        on_finished: 整批完成时的回调，参数为结果映射；None 表示不回调。

    Returns:
        本批请求的 LoadRequest 句柄。
    """
    ...
def default_client() -> IconifyClient:
    """返回进程级共享客户端，首次调用时创建。

    Returns:
        共享的 IconifyClient。
    """
    ...

class IconifyClient(QObject):
    """按需下载图标数据并注册进内存注册表。

    加载顺序为：内存注册表、磁盘缓存、网络下载。

    信号 loaded(str)：参数为图标名；本类当前不会发射该信号。
    信号 failed(str, object)：某个图标加载失败时发射，参数为图标名和异常对象。
    """
    loaded: Signal
    failed: Signal
    def __init__(
        self,
        parent: QObject | None = None,
        *,
        offline: bool = False,
        downloader: IconDownloader | None = None,
        cache: DiskCache | None = None,
        target_registry: IconRegistry | None = None,
    ) -> None:
        """初始化客户端。

        Args:
            parent: 父 QObject；可传 None。
            offline: 是否启动即处于严格离线模式；默认 False。
            downloader: 下载器；None 时新建默认 IconDownloader。
            cache: 磁盘缓存；None 时使用默认目录的 DiskCache。
            target_registry: 接收图标数据的注册表；None 时使用共享注册表。
        """
        ...
    def set_offline(self, value: bool) -> None:
        """切换严格离线模式。

        切到离线时，未完成的加载记为 OfflineError；切回在线时，清除此前由离线造成的失败记录。

        Args:
            value: True 进入离线模式，False 回到在线模式。
        """
        ...
    def is_offline(self) -> bool:
        """是否处于严格离线模式。"""
        ...
    def get_failure(self, name: str | IconName) -> Exception | None:
        """返回已记录的加载失败原因。

        Args:
            name: 图标名；可传 "prefix:name" 字符串或 IconName。

        Returns:
            失败异常；没有失败记录时为 None。
        """
        ...
    def reset_failures(self) -> None:
        """清除失败记录，允许重新加载。"""
        ...
    def ensure_loaded(self, name: str | IconName) -> None:
        """数据缺失时轻量触发一次加载，可在绘制路径调用。

        客户端已关闭、处于离线、已有失败记录、数据已在注册表或正在加载时直接返回。

        Args:
            name: 图标名；可传 "prefix:name" 字符串或 IconName。
        """
        ...
    def load(
        self,
        icons: Sequence[str],
        *,
        on_finished: Callable[[dict[str, Exception | None]], None] | None = None,
    ) -> LoadRequest:
        """显式预加载一批图标。

        已在注册表的图标直接记为成功；已有失败记录的沿用该失败；离线时记为 OfflineError。

        Args:
            icons: 图标名可迭代对象；每项为 "prefix:name" 字符串。
            on_finished: 整批完成时的回调，参数为结果映射；None 表示不回调。

        Returns:
            本批请求的 LoadRequest 句柄。

        Raises:
            ClientClosedError: 客户端已关闭。
        """
        ...
    def close(self) -> None:
        """关闭客户端并关闭下载器，未完成的图标记为 ClientClosedError。"""
        ...

class LoadRequest(QObject):
    """一批预加载请求的完成通知句柄。

    信号 finished(object)：整批图标都有结果时发射，参数为 ``{图标名: 异常或 None}`` 字典。
    """
    finished: Signal
    def names(self) -> tuple[str, ...]:
        """返回已有结果的图标名。"""
        ...
    def wait(self, timeout_ms: int | None = None) -> dict[str, Exception | None]:
        """阻塞事件循环等待本批完成，必须在主线程调用。

        Args:
            timeout_ms: 最长等待毫秒数；None 表示一直等到全部完成。

        Returns:
            图标名到结果的映射，成功为 None，失败为对应异常；超时时只含已完成的图标。
        """
        ...
    def cancel(self) -> None:
        """取消尚未完成的图标，剩余项记为 RequestCancelledError。"""
        ...
