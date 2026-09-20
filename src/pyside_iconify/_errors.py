"""错误类型。"""


class IconifyError(Exception):
    """库异常基类。"""


class InvalidIconNameError(IconifyError):
    """图标名无效。"""


class InvalidIconDataError(IconifyError):
    """Iconify 数据无效。"""


class IconNotFoundError(IconifyError):
    """图标数据不存在。"""


class InvalidColorError(IconifyError):
    """颜色值无效。"""


class InvalidSizeError(IconifyError):
    """尺寸值无效。"""


class InvalidRotationError(IconifyError):
    """旋转值无效。"""


class InvalidOpacityError(IconifyError):
    """透明度无效。"""


class DuplicateIconError(IconifyError):
    """图标重复注册。"""


class UnsupportedSvgError(IconifyError):
    """SVG 数据不受支持。"""


class UnsafeIconDataError(IconifyError):
    """图标数据不安全。"""


class WrongThreadError(IconifyError):
    """Qt 调用不在主线程。"""


class NoApplicationError(IconifyError):
    """缺少 QApplication 实例。"""


class IconNotLoadedError(IconifyError):
    """图标数据尚未就绪。"""


class UnsupportedTargetError(IconifyError):
    """目标类型不受支持。"""
