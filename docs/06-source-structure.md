# 6. 源码结构

## 6.1 先说结论

```text
src/pyside_iconify/
├── __init__.py
├── py.typed
├── _api.py
├── _config.py
├── _errors.py
├── _logging.py
├── core/
├── rendering/
└── widgets/
```

## 6.2 依赖方向

```text
widgets/  →  rendering/  →  core/
```

只能从右向左依赖：

- `widgets/` 可以用 `rendering/`
- `rendering/` 可以用 `core/`
- `core/` 不依赖 Qt，也不反向依赖其它层

这样图标数据处理可在没有 Qt 的环境运行；绘制细节也不会污染公开接口。

## 6.3 根目录：公开入口与全局规则

| 文件          | 放什么                                                 | 为什么在这里                        |
| ------------- | ------------------------------------------------------ | ----------------------------------- |
| `__init__.py` | 对外导出 `IconWidget`、`get_icon`、`add_collection` 等 | 用户只从一个地方导入                |
| `_api.py`     | 公开函数的实现和参数归一化                             | 内部拆文件不影响用户导入路径        |
| `_config.py`  | `set_default_config()`、缓存限制、禁用透明度           | 全局配置集中管理                    |
| `_errors.py`  | 所有公开异常                                           | 错误类型不散落各层                  |
| `_logging.py` | `pyside_iconify` logger                                | 默认静默，统一日志规则              |
| `py.typed`    | 类型包标记                                             | IDE、类型检查、未来工具链能识别类型 |

根目录不放 SVG 渲染、JSON 解析或 QWidget 逻辑。

## 6.4 core：纯数据层

```text
core/
├── types.py
├── names.py
├── icon_data.py
├── registry.py
├── colors.py
├── sizes.py
└── svg.py
```

| 文件           | 负责什么                                                 |
| -------------- | -------------------------------------------------------- |
| `types.py`     | 图标名、图标数据、RGBA、尺寸描述等不可变类型             |
| `names.py`     | 解析 `mdi:home` 这类图标名                               |
| `icon_data.py` | 解析 Iconify JSON、默认宽高、别名                        |
| `registry.py`  | `add_icon`、`add_collection`、数据版本、锁               |
| `colors.py`    | 颜色名、HEX、RGB/HSL、映射表、`hex_argb()`、`hex_rgba()` |
| `sizes.py`     | 数字、`px`、`em` 等尺寸写法的解析                        |
| `svg.py`       | 合成 SVG、别名变换、90 度倍数旋转                        |

### 为什么 core 不导入 PySide

- 后台线程可解析、注册大量图标数据
- 将来 VSCode 插件、MCP 或命令行工具可以复用
- 测数据规则时不需要创建 `QApplication`

公开接口接到 `QColor`、`QSize` 后，在 Qt 边界先转成内部类型；`core/` 内部只认识自己的 RGBA 和尺寸描述，不保存 Qt 对象。

## 6.5 rendering：把数据变成 QIcon

```text
rendering/
├── engine.py
├── renderer.py
├── cache.py
├── placeholder.py
└── qt_adapter.py
```

| 文件             | 负责什么                                               |
| ---------------- | ------------------------------------------------------ |
| `engine.py`      | 自定义 `QIconEngine`，使 `get_icon()` 返回标准 `QIcon` |
| `renderer.py`    | SVG 转 QImage/QPixmap，处理颜色、透明度、旋转和高分屏  |
| `cache.py`       | 图标数据、SVG 文本、位图三层缓存                       |
| `placeholder.py` | 不存在或出错时的内置占位图                             |
| `qt_adapter.py`  | Qt 类型转换、主线程检查、设备缩放比获取                |

这是唯一负责 Qt 绘制的边界层。

它负责：

- 高分屏按 DPR 重新渲染
- `loading` 画空白，`missing` / `error` 画占位图
- 位图缓存和缓存键
- `WrongThreadError`
- `get_icon()` 产出标准 `QIcon`

## 6.6 widgets：摆在界面里的控件

```text
widgets/
├── icon_widget.py
└── animation.py
```

| 文件             | 负责什么                                        |
| ---------------- | ----------------------------------------------- |
| `icon_widget.py` | `IconWidget`、主题跟随、QSS、palette 监听、信号 |
| `animation.py`   | `spin=True` 的共享时钟、隐藏暂停、角度量化      |

`widgets/` 不解析 JSON，不直接管理图标集合，也不重复实现缓存。

它只负责把渲染层能力变成一个普通 QWidget：

```python
IconWidget("mdi:home", qss="toolbar")
```

QSS 仍使用 PySide 原生写法：

```python
self.setStyleSheet("""
IconWidget[qss~="toolbar"] {
    color: #cbd2dd;
    background: #111111;
}
""")
```

`qss` 只是选择器分组标签；具体样式永远由 `setStyleSheet()` 写入。

## 6.7 以后才建的目录

### Step 2：network

```text
network/
├── client.py
├── request.py
└── disk_cache.py
```

负责下载、请求合并、磁盘缓存、严格离线模式。它使用 `core/` 的图标数据类型，不让网络逻辑侵入控件。

### Step 3：integrations

```text
integrations/
└── set_icon.py
```

这里放可选的 `set_icon()` 便利函数。它不是核心路径：核心仍是 `get_icon()` 返回标准 `QIcon`，让任何接收 QIcon 的组件自行使用。

## 6.8 不要出现的目录

| 不建什么    | 原因                                     |
| ----------- | ---------------------------------------- |
| `utils/`    | 职责不清，最后会变成杂物间               |
| `managers/` | 名称太泛，不说明管理什么                 |
| `assets/`   | 图标数据由注册表管理，内置占位图用代码画 |
| `compat/`   | 当前只承诺 PySide6，暂时不需要兼容层     |

## 6.9 判断一个文件该放哪里

| 问题                                             | 应放的位置        |
| ------------------------------------------------ | ----------------- |
| 不装 PySide6 也能运行吗？                        | `core/`           |
| 要用 QIcon、QPixmap、QPainter、QSvgRenderer 吗？ | `rendering/`      |
| 是 QWidget、QSS、信号、动画交互吗？              | `widgets/`        |
| 是用户 import 的公开接口或全局规则吗？           | 根目录            |
| 是下载或磁盘缓存吗？                             | 以后放 `network/` |

这个判断比文件名更重要：**一件事只放一层。**
