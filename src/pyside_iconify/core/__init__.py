"""不依赖 Qt 的图标数据能力。"""

from pyside_iconify.core.registry import IconRegistry, registry
from pyside_iconify.core.types import IconData, IconName, RGBA, SizeSpec

__all__ = ["IconData", "IconName", "IconRegistry", "RGBA", "SizeSpec", "registry"]
