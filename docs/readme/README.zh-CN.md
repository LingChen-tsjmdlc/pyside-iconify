# pyside-iconify

**给 `QIcon` 换一个数据来源。**

[English](../../README.md) | **中文** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

一行一个图标。不用管理 SVG / PNG 文件——图标按名称从
[Iconify](https://iconify.design) 生态按需获取并自动缓存。产出仍是标准
`QIcon`，任何接收图标的控件都能直接用。

> **状态**：开发中，尚未发布到 PyPI。首次发布前公开接口可能调整。
>
> 本项目**不是** Iconify 官方项目。

[English](../../README.md)

## 为什么用它

| 原来                            | 用 pyside-iconify                  |
| ------------------------------- | ---------------------------------- |
| `QIcon("assets/home.svg")`      | `get_icon("mdi:home")`             |
| 自己管理 SVG/PNG 文件和资源路径 | 按名称从 Iconify 生态取图标        |
| 多套资产文件处理颜色和尺寸      | `color`、`size`、`rotate` 都是参数 |
| 每个控件自己接图标              | 标准 `QIcon`，到处可用             |
| 手工维护亮暗两套图标            | 自动跟随控件调色板                 |

## 快速开始

```powershell
pip install "pyside-iconify[pyside6]"
```

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
- **类型与日志**——全量类型提示 + `py.typed`；标准 `logging`（默认静默）

## 参数

`IconWidget` 与 `get_icon` 共用：

```python
get_icon(名称, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(名称, *, ..., hover_color=None, qss=None, parent=None)
```

| 参数                                     | 说明                                                           |
| ---------------------------------------- | -------------------------------------------------------------- |
| 名称                                     | `"mdi:home"` 这样的图标名，或内联图标数据                      |
| `size`                                   | 数字、`(宽, 高)`、`QSize`、`"24px"`、`"1.5em"`                 |
| `color`                                  | 单个颜色，或 `{原色: 新色}` 映射表                             |
| `color_light_theme` / `color_dark_theme` | 按主题覆盖，优先于 `color`                                     |
| `selected_color`                         | 列表/树中选中时的颜色（item view）                             |
| `hover_color`                            | IconWidget / `set_icon` 的悬停色——显式启用才生效               |
| `opacity`                                | 整体透明度 0–1，与颜色 alpha 相乘                              |
| `width` / `height`                       | 非正方形图标，优先于 `size`                                    |
| `rotate`                                 | 任意角度（度），自动缩小避免裁剪                               |
| `spin`                                   | 持续旋转，用于加载指示                                         |
| `h_flip` / `v_flip`                      | 水平 / 垂直翻转                                                |
| `qss`                                    | QSS 分组标记，选择器 `IconWidget[qss~="tag"]`（仅 IconWidget） |

颜色接受 CSS/SVG 颜色名、HEX 3/4/6/8 位（`#RRGGBBAA` 顺序）、
`rgb()/rgba()/hsl()/hsla()`、元组、`QColor`、`Qt.GlobalColor`。
无法解析的颜色直接报错，不会静默变黑。

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

## 支持范围

| 项目         | 范围                           |
| ------------ | ------------------------------ |
| Python       | 3.10 – 3.14                    |
| Qt 绑定      | PySide6                        |
| 操作系统     | Windows、macOS、Linux（CI 在 macOS 上运行） |
| PySide2/PyQt | 暂不支持（未来可能评估 PyQt6） |

## 开发

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- 架构与设计决策：[docs/architecture.md](../architecture.md)
- 路线图：[docs/roadmap.md](../roadmap.md)
- 性能演示：`uv run benchmarks/list_scroll.py`

## 许可证

[MIT](../../LICENSE)。图标集合遵循其各自许可；Qt 由其权利人单独授权。
