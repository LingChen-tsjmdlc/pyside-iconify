# pyside-iconify

**给 `QIcon` 换一个数据来源。**

```python
IconWidget("mdi:home", color="red")
```

不用准备 SVG 或 PNG 文件，直接用图标名。需要交给已有控件时，仍然得到标准 `QIcon`。

> 状态：开发中，尚未发布到 PyPI。离线能力已实现，可运行 `examples/step1_demo.py` 查看；联网按需下载尚未实现，公开接口在首次发布前可能调整。
>
> 本项目**不是 Iconify 官方项目**。

## 为什么用它

| 原来                              | pyside-iconify                                |
| --------------------------------- | --------------------------------------------- |
| `QIcon("assets/home.svg")`        | `get_icon("mdi:home")`                        |
| 自己管理 SVG / PNG 文件和资源路径 | 通过图标名或本地 Iconify JSON 获取数据        |
| 多套图标文件处理颜色和尺寸        | `color`、`size` 等参数                        |
| 不同控件要自己处理图标来源        | 返回标准 `QIcon`，任何接收 QIcon 的控件都能用 |

## 目标用法

### 独立摆放图标

```python
from pyside_iconify import IconWidget

icon = IconWidget("mdi:home", size=24, color="red")
layout.addWidget(icon)
```

### 给已有控件设置图标

```python
from pyside_iconify import get_icon

button.setIcon(get_icon("mdi:home", size=24, color="red"))
```

### 完全离线使用

图标数据由你提供，运行时不联网：

```python
from pyside_iconify import IconWidget, add_collection

add_collection({
    "prefix": "app",
    "width": 16,
    "height": 16,
    "icons": {
        "square": {
            "body": '<rect x="2" y="2" width="12" height="12" fill="currentColor"/>'
        }
    },
})

icon = IconWidget("app:square", size=24, color="red")
```

### 运行示例

```powershell
python examples/step1_demo.py
```

## 设计目标

- `IconWidget("mdi:home", color="red")` 一行可用
- `get_icon()` 返回标准 `QIcon`
- 不填颜色时跟随 Qt 亮暗主题和控件文字颜色
- 多色图标支持 `{原色: 新色}` 映射表
- 高分屏按设备缩放比渲染
- 加载中显示空白，确认缺失或错误才显示占位图
- 支持 Qt 原生 QSS：`qss` 用于分组，具体样式用 `setStyleSheet()`
- 离线优先，联网下载和磁盘缓存留到 Step 2

## 支持范围

| 项目                 | 计划范围           |
| -------------------- | ------------------ |
| Python               | 3.10 — 3.14        |
| Qt 绑定              | PySide6            |
| 操作系统             | 先验证 Windows x64 |
| PySide2 / PyQt / QML | 暂不支持           |

这些是目标范围，不代表已经完成验证。

## 安装

首次发布到 PyPI 后：

```powershell
pip install "pyside-iconify[pyside6]"
```

当前从源码开发时，参考[版本支持与发布](docs/03-compatibility-and-release.md)。

## 测试

测试使用 `pytest` 与 `pytest-qt`。从源码开发时先由你安装测试组：

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

测试覆盖离线数据、颜色、QIcon、IconWidget、QSS、loading、fallback、线程和缓存等 Step 1 回归项。GitHub Actions 会在 Python 3.10 与 3.13 上运行同一套离屏测试。

## 文档

| 文档                                                   | 内容                        |
| ------------------------------------------------------ | --------------------------- |
| [开始这里](docs/00-start.md)                           | 日常使用和当前状态          |
| [它是怎么工作的](docs/01-design.md)                    | Iconify 数据与 Qt 渲染原理  |
| [接口设计](docs/02-api-contract.md)                    | 参数、颜色、QSS、异常、线程 |
| [版本支持与发布](docs/03-compatibility-and-release.md) | 依赖与发布计划              |
| [开发计划](docs/04-roadmap.md)                         | Step 0—4 与验收项           |
| [性能](docs/05-performance.md)                         | 缓存、性能目标和基准测试    |
| [源码结构](docs/06-source-structure.md)                | 分层和依赖方向              |

## 许可证

本库代码采用 [MIT](LICENSE)。

图标素材遵循各自图标集合的许可；Qt / PySide 也有独立许可要求。若将来引入 Iconify 上游代码，会保留上游版权声明。
