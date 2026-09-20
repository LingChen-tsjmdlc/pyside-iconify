# 0. 开始这里

只看这一页就够。01—04 是参考资料，需要细节时再查。

## 这个库是什么

**不用准备图标文件，写名字就有图标。**

```python
IconWidget("mdi:home", color="red")
```

一行就是一个图标。大小、颜色都是参数，不用准备多套文件。

底层产出的是标准 `QIcon`，所以你现有的代码、别人的控件、**你自己写的组件库**都不用改。可以理解成：**给 `QIcon` 换了个数据来源。**

|            | 原来                    | 用这个库           |
| ---------- | ----------------------- | ------------------ |
| 图标从哪来 | 自己准备 SVG / PNG 文件 | 一个名字           |
| 换颜色     | 准备多套文件            | `color="red"`      |
| 换大小     | 准备多种尺寸            | `size=24`          |
| 亮暗主题   | 准备两套图标            | **自动跟随**       |
| 高分屏     | 准备 @2x、@3x 多套图    | **自动按屏幕渲染** |
| 结果类型   | `QIcon`                 | **还是 `QIcon`**   |

## 五个重点能力

### 一、自动适配亮暗主题

```python
IconWidget("mdi:home")   # 不填颜色
```

亮色主题下是深色图标，暗色主题下是浅色图标，**用户切换主题时自动变**，不用你写代码。原理是跟随所在控件的文字颜色，和旁边的文字始终一致。

按钮禁用时，图标透明度自动降到 0.4 变淡（不是换成灰色，这样多色图标也能正确变淡）。

想分别指定亮暗颜色：

```python
IconWidget("mdi:home", light_color="#333333", dark_color="#eeeeee")
```

只写一个也行，另一种主题下仍然自动跟随。

优先级：**`light_color` / `dark_color` → `color` → 自动跟随**。

### 二、多色图标也能换色、也能跟主题

颜色参数可以传一张映射表，把原色换成新色：

```python
IconWidget("devicon:google", color={"#4285f4": "#00a0ff"})
```

只替换表里列出的颜色，其余保持原样。配合亮暗参数，可以解决「图标里的白色在暗色主题下太刺眼」：

```python
IconWidget("devicon:google",
           light_color={"#ffffff": "#f5f5f5"},
           dark_color={"#ffffff": "#2b2b2b"})
```

**多色图标传单个颜色不会生效**，因为把 Google 图标染成一片红没有意义。想改就用映射表明确说明改哪个。

不知道图标里有哪些颜色时：`get_icon_colors("devicon:google")`。

### 三、高分屏不用管

`size=24` 是**逻辑像素**。在 150% 缩放的屏幕上，我们会按 36 个物理像素渲染，但看起来还是 24 像素那么大。

**不要自己乘缩放比**，那会导致图标过大。因为是矢量数据按需渲染，任何缩放比下都清晰，不需要准备 @2x、@3x 多套图。

### 四、透明度和加载动画

```python
IconWidget("mdi:home", opacity=0.5)      # 整体变淡
IconWidget("mdi:loading", spin=True)     # 持续旋转，加载中
```

透明度来自三处时**相乘**：颜色自带的 alpha × `opacity` × 禁用系数。例如 `opacity=0.5` 的图标放在禁用按钮上，最终是 `0.5 × 0.4 = 0.2`。

这样每层意图都保留：本来就半透明的图标，禁用后会比正常状态更淡。

`spin` 在控件不可见时自动暂停，多个图标同转共用一个定时器。

### 五、20 万个图标随便用

不用下载文件、不用管资源路径，也可以完全离线打包。

## 怎么用

只有两个入口。

### 一、摆一个图标：IconWidget

```python
from pyside_iconify import IconWidget

IconWidget("mdi:home", color="red")
IconWidget("mdi:home", size=32)

layout.addWidget(IconWidget("mdi:home"))
```

**这是最常用的写法。** `IconWidget` 就是普通 `QWidget`，能进布局、能当子控件、能设样式表，和网页里的 `<div>` 一样自由。

### 二、给已有控件设图标：get_icon

```python
from pyside_iconify import get_icon

button.setIcon(get_icon("mdi:home", color="red"))
action.setIcon(get_icon("mdi:save"))
my_custom_widget.setIcon(get_icon("mdi:home"))
```

按钮、菜单这些控件已经有自己的图标属性，不需要再塞一个控件进去，所以给它们一个 `QIcon`。

**参数和 `IconWidget` 完全一样。** 区别只在于：一个是新控件，一个是给已有控件的图标。

### 为什么 get_icon 能适配任何控件

它返回的就是标准 `QIcon`，**凡是接受 `QIcon` 的地方都能用**——包括你自己写的组件库、将来 Qt 新增的控件。

库不需要知道目标是什么，也不需要为每种控件写适配代码。判断标准只有一条：**它收不收 `QIcon`。**

## 数据从哪来：两种

写法完全一样，区别只是数据来源。

### 用法 A：离线（Step 1 先做这个）

图标数据由你提供，程序不联网。

```python
from pyside_iconify import add_collection, IconWidget

# 注册一份图标数据，格式和 Iconify 官方 JSON 一样
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

IconWidget("app:square", size=24, color="red")
```

数据可以来自：

- 你自己画的图标
- 从 Iconify 官方仓库挑出来的 JSON，放进你的项目
- 将来提供的打包工具生成的子集

**适合**：内网程序、要求可复现构建、不希望运行时依赖外部服务。

### 用法 B：联网按需下载（Step 2 再做）

只写名字，数据由库自动获取。

```python
IconWidget("mdi:home", size=24, color="red")
```

第一次用到时后台下载，之后走缓存。**Step 1 阶段这种写法还不能用。**

**适合**：开发阶段随意试图标，不想提前准备素材。

## 支持范围

| 项目          | 支持情况                                            |
| ------------- | --------------------------------------------------- |
| Python        | 3.10 — 3.14                                         |
| Qt 绑定       | PySide6（主要目标）                                 |
| PySide6 版本  | Python 3.10—3.13 用 6.8.3 以上；3.14 用 6.11.2 以上 |
| 操作系统      | 先验证 Windows x64，之后补 macOS 与 Linux           |
| PySide2       | 暂不支持，后续再评估                                |
| PyQt5 / PyQt6 | 暂不支持，有需求再考虑 PyQt6                        |
| QML           | 不支持，只做 Widgets                                |

**这是目标范围，不是已测结果。** 功能还没实现，Step 1 完成后逐项验证再更新这张表。

### 为什么不支持 PySide2

官方 PySide2 停在 2022 年的 5.15.2.1，要求 Python 3.10 及更低版本。为了兼容它，整个项目得一直用旧语法，还要处理 Qt5 与 Qt6 的渲染差异。**代价太大，先把 PySide6 做好。**

### 安装方式（实现后才可用）

```powershell
uv add pyside-iconify
```

你的程序已经装了 PySide6 的话，本库不会再装一份 Qt。

## 开发原则

1. **一行能用**：`IconWidget("mdi:home", color="red")` 就是标准写法，不需要先创建任何管理对象。
2. **产出标准 QIcon**：不要求使用者改已有代码，也不需要我们适配各种控件类型。
3. **分层清晰**：数据处理不依赖 Qt，Qt 层只负责显示。
4. **不卡界面**：下载在后台进行。
5. **离线可用**：本地图标数据必须能直接显示。

## 现在的状态

已完成：MIT 许可证、uv 与打包配置、目录骨架、参考文档。

未实现：**全部功能。** `get_icon` 和 `IconWidget` 都还不存在。

## 下一步（Step 1，不涉及网络）

目标：**把上面的用法 A 跑通。**

1. 解析图标名（`app:square` → 集合 + 名字）
2. 解析 Iconify 格式的 JSON，实现 `add_collection`
3. 生成 SVG 并用 Qt 画出来
4. 实现 `get_icon`（返回 `QIcon`）和 `IconWidget`
5. 颜色三参数（`color` / `light_color` / `dark_color`）与映射表换色
6. `opacity` 与透明度相乘规则、禁用变淡
7. 亮暗主题自动跟随、高分屏按缩放比渲染
8. `spin` 旋转动画
9. QSS 支持、类型标注、线程检查、日志

**完成标准：断网状态下，`IconWidget("app:square", size=24, color="red")` 能显示出红色方块，改 `size`、`color`、`rotate`、`opacity` 都生效；`get_icon` 的结果交给普通按钮也能正常显示。**

这一步不会有任何网络代码。

### 六件事需要真机验证

1. **数据到了自动刷新**：要确认 Qt 不会因为内部缓存继续显示旧图。这决定了 `get_icon` 能不能真的零适配。
2. **主题切换**：系统主题、QSS 换肤、`setPalette` 三种方式都要能触发更新，不能只在重启后才对。
3. **高分屏**：100% / 125% / 150% / 200%，以及窗口拖到另一块不同缩放比的屏幕。
4. **动画开销**：几十个图标同时转时的 CPU 占用，窗口最小化后是否真的停下来。
5. **大量图标**：上千行的列表滚动是否掉帧。
6. **QSS 生效**：`color` 和 `background` 是否真能作用到自定义控件上。

**这六条必须实测，不靠推断。** 有做不到的我会如实说明并给替代方案。

## 已确认

- **主要写法是 `IconWidget("mdi:home", color="red")`**，一行可用。
- `get_icon()` 用于给已有控件设图标，参数与 `IconWidget` 一致。
- **定位：`QIcon` 的数据来源升级。** 底层产出标准 `QIcon`，能接 `QIcon` 的地方都能用，包括自写组件库。
- **不填 `color` 时自动跟随亮暗主题**；也可以用 `light_color` / `dark_color` 分别指定，优先级高于 `color`。
- **颜色参数可以传一张 `{原色: 新色}` 映射表**，用于多色图标换色；多色图标传单个颜色不生效，保持原配色。
- **禁用状态用透明度变淡**（默认 0.4），不换成灰色，多色图标也适用。
- **有 `opacity` 参数**；多个透明度相乘：颜色 alpha × `opacity` × 状态系数。
- **有 `spin=True` 旋转动画**，不可见时自动暂停，多图标共用定时器。
- **`size` 可传数字、元组、`QSize`、`"24px"`、`"1.5em"`**；是逻辑像素，高分屏自动按缩放比渲染。
- **加载中显示空白，确认不存在才显示占位图标**；可用 `fallback` 指定替代图标。
- **有 `set_default_config()` 统一设默认值**，参数写法与 `IconWidget` 一致。
- **支持 QSS**：`IconWidget { color: #333; }` 直接生效；构造时可写 `qss="toolbar primary"` 给 QSS 分组，具体样式仍用原生 `setStyleSheet()` 写。优先级：参数 → QSS → 主题跟随。
- **全库带类型标注 + `py.typed`**，为后续 VSCode 插件、MCP 工具打基础，CI 跑类型检查。
- **Qt 调用必须在主线程**，否则报 `WrongThreadError`；数据层（解析、注册）允许后台线程。
- **用标准 `logging`**，logger 名 `pyside_iconify`，默认不输出。
- **性能是硬指标**，单独见[性能文档](05-performance.md)。
- 旋转只有 `rotate` 一个参数，接受任意角度（`90`、`45` 都行），斜放时自动缩小以避免裁剪。
- `color` 支持颜色名、HEX 3/4/6/8 位、`rgb()`、`rgba()`、`hsl()`、`hsla()`、元组、`QColor`。**带透明度的 HEX 默认按 `#RRGGBBAA`**（取色器都是这个顺序）；需要 Qt 的 `#AARRGGBB` 时用 `hex_argb()` 显式声明。
- 悬停 / 选中状态的图标变化**延后到 Step 3** 再做。
- 阶段命名用 Step 0—4。
- 已删除 `assets/`、`outputs/`。
- 保留 `src/` 布局。
- 代码等你审阅后再开始写。

## 需要你回答

1. 用法 A（离线）的写法认可吗？Step 1 就按它实现。
2. 支持范围认可吗？
3. Step 1 的任务顺序要调整吗？

说「开始」我再动手写代码。

## 文档导航

| 文件                            | 何时看             |
| ------------------------------- | ------------------ |
| 00-start.md                     | 本页，日常看这个   |
| 01-design.md                    | 想知道内部怎么运作 |
| 02-api-contract.md              | 定接口细节时       |
| 03-compatibility-and-release.md | 发布到 PyPI 前     |
| 04-roadmap.md                   | 查阶段任务时       |
| 05-performance.md               | 关心性能时         |
| 06-source-structure.md          | 看源码怎么分层时   |
