# pyside-iconify

**给 `QIcon` 换一个数据来源。**

[English](../../README.md) | **中文** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

一行一个图标。不用管理 SVG / PNG 文件——图标按名称从
[Iconify](https://iconify.design) 生态按需获取并自动缓存。产出仍是标准
`QIcon`，任何接收图标的控件都能直接用。

> 本项目**不是** Iconify 官方项目。

## 为什么用它

| 原来                            | 用 pyside-iconify                  |
| ------------------------------- | ---------------------------------- |
| `QIcon("assets/home.svg")`      | `get_icon("mdi:home")`             |
| 自己管理 SVG/PNG 文件和资源路径 | 按名称从 Iconify 生态取图标        |
| 多套资产文件处理颜色和尺寸      | `color`、`size`、`rotate` 都是参数 |
| 每个控件自己接图标              | 标准 `QIcon`，到处可用             |
| 手工维护亮暗两套图标            | 自动跟随控件调色板                 |

## 快速开始

选择你的应用使用的 Qt 绑定，并安装对应的 extra：

```bash
# 你用哪个 Qt 绑定，就装哪一行。
pip install "pyside-iconify[pyside6]"   # 使用 PySide6（类型提示也默认按它）
pip install "pyside-iconify[pyqt6]"     # 使用 PyQt6
pip install "pyside-iconify[pyqt5]"     # 使用 PyQt5
pip install "pyside-iconify[pyside2]"   # 使用 PySide2（仅 Python 3.10）
```

extra 会同时安装该绑定和对应的类型存根。如果绑定已经装好，直接 `pip install pyside-iconify` 运行时也能用（库会跟随你的程序导入的绑定），只是非 PySide6 用户得不到精确的类型提示。详见下文“选择 Qt 绑定”。

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# 独立图标控件
icon = IconWidget("mdi:home", size=24, color="red")

# 或者把标准 QIcon 交给任意控件
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

常见场景的全部 API 就这些。图标首次使用时下载、落盘缓存，之后本地渲染。

## 特性

- **主题自适应**——不填颜色时跟随控件文字色，亮暗主题自动切换；禁用图标
  变淡而不是变灰（多色图标也能正确变淡）
- **完整的颜色控制**——单色、多色图标的 `{原色: 新色}` 映射表、按主题覆盖
  （`color_light_theme` / `color_dark_theme`）
- **直觉的尺寸**——数字、`(宽, 高)`、`QSize`、`"24px"`、`"1.5em"`（跟随控件字号）
- **高分屏原生**——size 是逻辑像素，按屏幕缩放比渲染物理像素，不需要 @2x/@3x
- **加载与缺失分离**——加载中显示空白，确认缺失才显示内置占位图并发出
  `failed` 信号；可用 `fallback` 指定替代图标
- **QSS 友好**——`qss="toolbar primary"` 分组标记，样式用原生
  `setStyleSheet()`；优先级：参数 → QSS → 主题
- **内置动画**——`spin`、`pulse`、`breathe`、`ping`、`bounce`，以及 `line-md`、
  `meteocons`、`svg-spinners` 中自带动画的图标，在 `IconWidget` 里开箱即播
  （仅 SMIL，见下文）
- **类型与日志**——全量类型提示 + `py.typed`；标准 `logging`（默认静默）

## 参数

`IconWidget` 与 `get_icon` 共用：

```python
get_icon(名称, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(名称, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| 参数                                     | 说明                                                                                                                                       |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 名称                                     | `"mdi:home"` 这样的图标名，或内联图标数据                                                                                                  |
| `size`                                   | 数字、`(宽, 高)`、`QSize`、`"24px"`、`"1.5em"`                                                                                             |
| `color`                                  | 单个颜色，或 `{原色: 新色}` 映射表                                                                                                         |
| `color_light_theme` / `color_dark_theme` | 按主题覆盖，优先于 `color`                                                                                                                 |
| `selected_color`                         | 列表/树中选中时的颜色（item view）                                                                                                         |
| `hover_color`                            | IconWidget / `set_icon` 的悬停色——显式启用才生效                                                                                           |
| `opacity`                                | 整体透明度 0–1，与颜色 alpha 相乘                                                                                                          |
| `width` / `height`                       | 非正方形图标，优先于 `size`                                                                                                                |
| `rotate`                                 | 任意角度（度），自动缩小避免裁剪                                                                                                           |
| `rotate_overflow`                        | 旋转时保持原尺寸；边角可能被裁切                                                                                                           |
| `spin`                                   | 持续旋转，用于加载指示                                                                                                                     |
| `animation` / `animation_period`         | 仅 IconWidget：`"spin"`、`"pulse"`、`"breathe"`、`"ping"` 或 `"bounce"`；每圈秒数                                                          |
| `autoplay` / `speed`                     | 仅 IconWidget：自动播放图标自带的 SMIL 动画；播放速度倍数                                                                                  |
| `animation_depth`                        | 动画强度 0–1（默认：pulse 0.25、breathe 0.7、ping 1、bounce 0.25）。ping 和 bounce 把图标画在控件的 1/(1+depth) 大小，给波纹和跳起留出空间 |
| `h_flip` / `v_flip`                      | 水平 / 垂直翻转                                                                                                                            |
| `qss`                                    | QSS 分组标记，选择器 `IconWidget[qss~="tag"]`（仅 IconWidget）                                                                             |

颜色接受 CSS/SVG 颜色名、HEX 3/4/6/8 位（`#RRGGBBAA` 顺序）、
`rgb()/rgba()/hsl()/hsla()`、元组、`QColor`、`Qt.GlobalColor`。
无法解析的颜色直接报错，不会静默变黑。

## 动画图标（SMIL）

部分 Iconify 图标集（`line-md`、`meteocons`、`svg-spinners`、`eos-icons` 等）
的图标自带动画。`IconWidget` 无需额外代码即可播放：

```python
IconWidget("line-md:loading-loop", size=48)       # 循环播放
IconWidget("line-md:account")                     # 自己画一遍，然后停住
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` 和 `set_icon()` 返回标准 `QIcon`，它自己不会动，所以显示的是动画的
**完成态**。要看动画请用 `IconWidget`。`is_animated("line-md:account")` 可以判断
某个图标是否带动画（不需要 Qt）。

范围：**只支持 SMIL**（SVG 内的 `<animate>`、`<set>`、`<animateTransform>`、
`<animateMotion>`）。其他类型的动画，如 CSS 动画、脚本、Lottie、GIF，不会播放。
如果图标用了本库未实现的 SMIL 特性，会显示为动画完成态的静态图，并只记录一次
警告日志。

动画帧以位图缓存（用内存换速度）。大尺寸的长循环图标可能占用默认 32 MiB 缓存的
几 MiB；如果同时显示很多个，请用 `set_cache_limits()` 调大。

## 离线打包

内网、断网或零外部依赖的发布场景，发布前把图标打包：

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # 程序启动时加载；PyInstaller 打包后同样可用
```

完整 CLI 与函数用法见 `src/pyside_iconify/pack.py` 与
`tests/test_pack_integration.py`。本地数据始终优先于网络。

## 性能

三层缓存（图标数据 → SVG 文本 → 渲染位图）+ 内存预算，每帧只做缓存查找和
一次 `drawPixmap`。1000 行 `QListWidget` 构建约 270 ms，滚动原生流畅。
大规模网格请用 item view + `get_icon`；`IconWidget` 适合独立图标位。

## 选择 Qt 绑定

同一份代码可在四种绑定上运行。照常导入你自己的绑定即可，库会跟随它。

| 绑定    | 状态                 | Extra                     |
| ------- | -------------------- | ------------------------- |
| PySide6 | 支持，主力           | `pyside-iconify[pyside6]` |
| PyQt6   | 支持                 | `pyside-iconify[pyqt6]`   |
| PyQt5   | 兼容                 | `pyside-iconify[pyqt5]`   |
| PySide2 | 兼容，仅 Python 3.10 | `pyside-iconify[pyside2]` |

绑定的选择顺序：

1. 环境变量 `PYSIDE_ICONIFY_QT_API`（`pyside6`、`pyqt6`、`pyqt5` 或 `pyside2`），如果设置了。
2. 你的程序在导入 `pyside_iconify` 之前已经导入的绑定。
3. 已安装的第一个，顺序为 PySide6、PyQt6、PyQt5、PySide2。

注意：

- **同一进程里不要混用绑定。** 如果程序已导入一种绑定而环境变量指向另一种，库会报错，而不是猜测。
- **类型提示。** `pyqt6`、`pyqt5`、`pyside2` 这几个 extra 还会安装一个很小的存根包（`pyside-iconify-stubs-<绑定>`），让编辑器和类型检查器看到你所用绑定的类（`QIcon`、`QSize` 等），而不是 `Any`。之后再装也同样生效。
- **Qt5 与高分屏。** Qt5 要在创建 `QApplication` 之前设置 `Qt.AA_UseHighDpiPixmaps`，图标在高分屏上才不会发糊。Qt6 默认已开启。
- **PyQt 许可。** PyQt5 和 PyQt6 由 Riverbank Computing 以 GPL v3 或商业许可发布。pyside-iconify 本身是 MIT，且不打包 Qt 或 PyQt；但如果你选择 PyQt，你的应用要遵守 PyQt 的许可。PySide6 和 PySide2 为 LGPL。

## 支持范围

| 项目     | 范围                                                          |
| -------- | ------------------------------------------------------------- |
| Python   | 3.10 – 3.14（PySide2：仅 3.10，这是它最后支持的版本）         |
| Qt       | PySide6、PyQt6（6.4+）；PyQt5（5.15.9+）；PySide2（5.15.2.1） |
| 操作系统 | Windows、macOS、Linux（CI 在 macOS 上运行）                   |

## 开发

```bash
uv sync --extra pyside6 --group test   # 只做一次：安装 PySide6 和测试工具
uv run pytest -v                       # 跑测试（先设置 QT_QPA_PLATFORM=offscreen）
uv run examples/smil_showcase.py       # 运行 examples/ 里的示例
```

各 extra 互斥。想试别的 Qt 绑定，请用一次性的临时环境，你的 `.venv` 会保持 PySide6：

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5，或：--python 3.10 --extra pyside2
```

`examples/` 里的文件通过一个小工具（`examples/_qt.py`）导入 Qt，这样它们能在所有绑定上运行。你自己的应用请直接导入所用绑定，写法见快速开始。

- 贡献指南与发布清单：[CONTRIBUTING.md](../../CONTRIBUTING.md)
- 架构与设计决策：[docs/architecture.md](../architecture.md)
- 路线图：[docs/roadmap.md](../roadmap.md)
- 性能演示：`uv run benchmarks/list_scroll.py`

## 许可证

[MIT](../../LICENSE)。图标集合遵循其各自许可；Qt 由其权利人单独授权。
